from __future__ import annotations

import json
import re
from typing import Any

import httpx

from backend.config import settings
from backend.models import AnalysisResult, ParsedFormulaCandidate, ParsedPdf


class LlmAnalysisService:
    @property
    def available(self) -> bool:
        return bool(settings.openai_api_key)

    async def analyze(self, parsed_pdf: ParsedPdf) -> AnalysisResult:
        if self.available:
            try:
                return await self._analyze_with_openai(parsed_pdf)
            except Exception as exc:
                fallback = self._heuristic_analysis(parsed_pdf)
                fallback.status = "fallback"
                fallback.warnings.append(f"LLM request failed and semantic fallback was used: {exc}")
                return fallback

        fallback = self._heuristic_analysis(parsed_pdf)
        fallback.status = "fallback"
        fallback.warnings.append("OPENAI_API_KEY is not configured, so semantic fallback analysis was used.")
        return fallback

    async def _analyze_with_openai(self, parsed_pdf: ParsedPdf) -> AnalysisResult:
        prioritized_candidates = rank_formula_candidates(parsed_pdf.formula_candidates)
        prompt = build_prompt(parsed_pdf)
        schema = build_response_schema()

        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{settings.openai_base_url.rstrip('/')}/responses",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.openai_model,
                    "input": [
                        {
                            "role": "system",
                            "content": [
                                {
                                    "type": "input_text",
                                    "text": (
                                        "You convert parsed academic paper content into a structured formula graph. "
                                        "Always preserve page-level grounding and return strict JSON only."
                                    ),
                                }
                            ],
                        },
                        {
                            "role": "user",
                            "content": [{"type": "input_text", "text": prompt}],
                        },
                    ],
                    "text": {
                        "format": {
                            "type": "json_schema",
                            "name": "paper_nexus_analysis",
                            "schema": schema,
                            "strict": True,
                        }
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

        content = extract_response_text(data)
        payload = json.loads(content)
        payload.setdefault("status", "ok")
        payload.setdefault("warnings", parsed_pdf.warnings)
        payload.setdefault("sourceFilename", parsed_pdf.source_filename)
        payload.setdefault("pageCount", parsed_pdf.page_count)
        payload.setdefault("documentTitle", parsed_pdf.title)
        payload.setdefault("pdfUrl", None)
        payload.setdefault("extractedText", parsed_pdf.full_text[:12000])
        payload.setdefault("formulaCandidates", [candidate.expression for candidate in prioritized_candidates[:20]])

        enrich_formulas(payload.setdefault("formulas", []), parsed_pdf)
        enrich_variables(payload.setdefault("variables", []), parsed_pdf)
        return AnalysisResult.model_validate(payload)

    def _heuristic_analysis(self, parsed_pdf: ParsedPdf) -> AnalysisResult:
        prioritized_candidates = rank_formula_candidates(parsed_pdf.formula_candidates)
        symbol_to_id: dict[str, str] = {}
        variables: list[dict[str, Any]] = []
        formulas: list[dict[str, Any]] = []

        for index, candidate in enumerate(prioritized_candidates[:16], start=1):
            formula_id = f"f{index}"
            expression = candidate.expression
            semantic = analyze_expression(expression)
            symbols = unique(semantic["lhsSymbols"] + semantic["rhsSymbols"])
            input_ids: list[str] = []

            for symbol in symbols:
                variable_id = slugify_symbol(symbol)
                if symbol not in symbol_to_id:
                    symbol_to_id[symbol] = variable_id
                    variables.append(
                        {
                            "id": variable_id,
                            "symbol": symbol,
                            "name": infer_variable_name(symbol),
                            "type": infer_variable_type(symbol),
                            "unit": "-",
                            "role": infer_variable_role(symbol),
                            "meaning": f"Symbol extracted from formula `{expression}`.",
                            "memory": f"Track `{symbol}` as one of the core entities in this paper.",
                            "source": f"Detected from page {candidate.page}",
                            "formulas": [formula_id],
                            "anchors": find_symbol_anchors(parsed_pdf, symbol),
                        }
                    )
                else:
                    variable_id = symbol_to_id[symbol]
                    for variable in variables:
                        if variable["id"] == variable_id and formula_id not in variable["formulas"]:
                            variable["formulas"].append(formula_id)
                            break

                input_ids.append(variable_id)

            output_symbol = semantic["lhsSymbols"][0] if semantic["lhsSymbols"] else None
            output_id = symbol_to_id.get(output_symbol) if output_symbol else None

            formulas.append(
                {
                    "id": formula_id,
                    "title": summarize_formula_title(expression, index),
                    "expression": expression,
                    "physicalMeaning": candidate.context or "Formula extracted from PDF content.",
                    "memory": f"Formula candidate from page {candidate.page}.",
                    "output": output_id,
                    "page": candidate.page,
                    "bbox": candidate.bbox.model_dump() if candidate.bbox else None,
                    "sourceCandidateId": candidate.id,
                    "semantic": semantic,
                    "inputs": unique(input_ids),
                    "dependsOn": [],
                    "paperNote": f"Page {candidate.page} · source {candidate.source} · conf {candidate.confidence:.2f}",
                    "chunks": build_chunks(expression, semantic, unique(input_ids)),
                    "anchors": find_formula_anchors(parsed_pdf, expression, semantic),
                }
            )

        if not formulas:
            fallback_expression = infer_fallback_formula(parsed_pdf.full_text)
            semantic = analyze_expression(fallback_expression)
            formulas.append(
                {
                    "id": "f1",
                    "title": "Recovered formula candidate",
                    "expression": fallback_expression,
                    "physicalMeaning": "No explicit formula-like line was detected, so this placeholder summarizes the extracted text.",
                    "memory": "Connect richer OCR and parsing to improve this result.",
                    "output": None,
                    "page": 1,
                    "bbox": None,
                    "sourceCandidateId": None,
                    "semantic": semantic,
                    "inputs": [],
                    "dependsOn": [],
                    "paperNote": "Generated fallback",
                    "chunks": [{"label": "Fallback", "text": parsed_pdf.full_text[:500] or "No text extracted.", "variableIds": []}],
                    "anchors": [],
                }
            )

        enrich_dependencies(formulas)

        overview = (
            f"Paper parsed from {parsed_pdf.page_count} page(s). {len(formulas)} formula candidates and "
            f"{len(variables)} variable candidates were reconstructed with page-anchored semantics."
        )

        return AnalysisResult.model_validate(
            {
                "documentTitle": parsed_pdf.title,
                "sourceFilename": parsed_pdf.source_filename,
                "pdfUrl": None,
                "pageCount": parsed_pdf.page_count,
                "status": "ok",
                "variables": variables,
                "formulas": formulas,
                "documentInsight": {
                    "overview": overview,
                    "pipeline": [
                        "PDF parsing: line-level formula region detection with normalized bounding boxes.",
                        "OCR: Mathpix region-aware extraction when credentials are configured.",
                        "Semantic parsing: operator/symbol analysis and dependency reconstruction.",
                    ],
                },
                "extractedText": parsed_pdf.full_text[:20000],
                "formulaCandidates": [candidate.expression for candidate in parsed_pdf.formula_candidates[:24]],
                "warnings": parsed_pdf.warnings,
            }
        )


def build_prompt(parsed_pdf: ParsedPdf) -> str:
    prioritized_candidates = rank_formula_candidates(parsed_pdf.formula_candidates)
    formula_lines = "\n".join(
        (
            f"- {candidate.id} | page {candidate.page} | {candidate.source} | conf={candidate.confidence:.2f}"
            f" | bbox={candidate.bbox.model_dump() if candidate.bbox else None}: {candidate.expression}\n"
            f"  context: {candidate.context}"
        )
        for candidate in prioritized_candidates[:30]
    )
    return f"""
Analyze this parsed paper and reconstruct it into an interactive formula graph.

Document title: {parsed_pdf.title}
Source filename: {parsed_pdf.source_filename}
Page count: {parsed_pdf.page_count}

Extracted text (possibly truncated):
{parsed_pdf.full_text[:18000]}

Formula candidates with page grounding and bounding boxes:
{formula_lines or '- none detected'}

Requirements:
- Produce variables with stable ids and attach each variable to related formulas.
- Produce formulas with concise titles, physical meaning, memory hooks, dependencies, chunks, and semantic metadata.
- Every formula must include page, sourceCandidateId (or null), bbox (or null), and semantic object.
- Keep dependencies sparse and precise.
- Do not hallucinate symbols not present in text/candidates unless absolutely required.
""".strip()


def build_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "documentTitle",
            "sourceFilename",
            "pdfUrl",
            "pageCount",
            "status",
            "variables",
            "formulas",
            "documentInsight",
            "extractedText",
            "formulaCandidates",
            "warnings",
        ],
        "properties": {
            "documentTitle": {"type": "string"},
            "sourceFilename": {"type": "string"},
            "pdfUrl": {"type": ["string", "null"]},
            "pageCount": {"type": "integer"},
            "status": {"type": "string", "enum": ["ok", "fallback"]},
            "variables": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "symbol", "name", "type", "unit", "role", "meaning", "memory", "source", "formulas"],
                    "properties": {
                        "id": {"type": "string"},
                        "symbol": {"type": "string"},
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                        "unit": {"type": "string"},
                        "role": {"type": "string"},
                        "meaning": {"type": "string"},
                        "memory": {"type": "string"},
                        "source": {"type": "string"},
                        "formulas": {"type": "array", "items": {"type": "string"}},
                        "anchors": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "formulas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "id",
                        "title",
                        "expression",
                        "physicalMeaning",
                        "memory",
                        "output",
                        "page",
                        "bbox",
                        "sourceCandidateId",
                        "semantic",
                        "inputs",
                        "dependsOn",
                        "paperNote",
                        "chunks",
                    ],
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "expression": {"type": "string"},
                        "physicalMeaning": {"type": "string"},
                        "memory": {"type": "string"},
                        "output": {"type": ["string", "null"]},
                        "page": {"type": ["integer", "null"]},
                        "bbox": {
                            "type": ["object", "null"],
                            "additionalProperties": False,
                            "required": ["x0", "y0", "x1", "y1"],
                            "properties": {
                                "x0": {"type": "number"},
                                "y0": {"type": "number"},
                                "x1": {"type": "number"},
                                "y1": {"type": "number"},
                            },
                        },
                        "sourceCandidateId": {"type": ["string", "null"]},
                        "semantic": {
                            "type": ["object", "null"],
                            "additionalProperties": False,
                            "required": ["lhsSymbols", "rhsSymbols", "operators", "complexity"],
                            "properties": {
                                "lhsSymbols": {"type": "array", "items": {"type": "string"}},
                                "rhsSymbols": {"type": "array", "items": {"type": "string"}},
                                "operators": {"type": "array", "items": {"type": "string"}},
                                "complexity": {"type": "integer"},
                            },
                        },
                        "inputs": {"type": "array", "items": {"type": "string"}},
                        "dependsOn": {"type": "array", "items": {"type": "string"}},
                        "paperNote": {"type": "string"},
                        "anchors": {"type": "array", "items": {"type": "string"}},
                        "chunks": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["label", "text", "variableIds"],
                                "properties": {
                                    "label": {"type": "string"},
                                    "text": {"type": "string"},
                                    "variableIds": {"type": "array", "items": {"type": "string"}},
                                },
                            },
                        },
                    },
                },
            },
            "documentInsight": {
                "type": "object",
                "additionalProperties": False,
                "required": ["overview", "pipeline"],
                "properties": {
                    "overview": {"type": "string"},
                    "pipeline": {"type": "array", "items": {"type": "string"}},
                },
            },
            "extractedText": {"type": "string"},
            "formulaCandidates": {"type": "array", "items": {"type": "string"}},
            "warnings": {"type": "array", "items": {"type": "string"}},
        },
    }


def enrich_formulas(formulas: list[dict[str, Any]], parsed_pdf: ParsedPdf) -> None:
    candidate_map = {candidate.id: candidate for candidate in parsed_pdf.formula_candidates}
    unused_candidates = rank_formula_candidates(parsed_pdf.formula_candidates)

    for idx, formula in enumerate(formulas, start=1):
        formula.setdefault("id", f"f{idx}")
        formula.setdefault("title", summarize_formula_title(str(formula.get("expression") or ""), idx))
        formula.setdefault("expression", "")
        formula.setdefault("physicalMeaning", "Formula extracted from paper context.")
        formula.setdefault("memory", "")
        formula.setdefault("output", None)
        formula.setdefault("sourceCandidateId", None)
        formula.setdefault("bbox", None)
        formula.setdefault("page", None)
        formula.setdefault("inputs", [])
        formula.setdefault("dependsOn", [])
        formula.setdefault("paperNote", "")
        formula.setdefault("chunks", [])
        formula.setdefault("anchors", [])

        semantic = formula.get("semantic")
        if not isinstance(semantic, dict):
            semantic = analyze_expression(str(formula.get("expression") or ""))
        else:
            semantic.setdefault("lhsSymbols", [])
            semantic.setdefault("rhsSymbols", [])
            semantic.setdefault("operators", [])
            semantic.setdefault("complexity", len(semantic.get("operators", [])) + len(semantic.get("rhsSymbols", [])))
        formula["semantic"] = semantic

        if not formula.get("inputs"):
            formula["inputs"] = unique(slugify_symbol(sym) for sym in semantic["lhsSymbols"] + semantic["rhsSymbols"])

        candidate = resolve_candidate(formula, unused_candidates, candidate_map)
        if candidate:
            formula["sourceCandidateId"] = candidate.id
            formula["page"] = formula.get("page") or candidate.page
            if not formula.get("bbox") and candidate.bbox:
                formula["bbox"] = candidate.bbox.model_dump()
            if candidate in unused_candidates:
                unused_candidates.remove(candidate)

        if not formula.get("page"):
            formula["page"] = min(parsed_pdf.page_count, idx)
        if not formula.get("anchors"):
            formula["anchors"] = find_formula_anchors(parsed_pdf, str(formula.get("expression") or ""), semantic)

    enrich_dependencies(formulas)


def enrich_variables(variables: list[dict[str, Any]], parsed_pdf: ParsedPdf) -> None:
    for variable in variables:
        variable.setdefault("anchors", [])
        symbol = str(variable.get("symbol") or "").strip()
        if symbol and not variable["anchors"]:
            variable["anchors"] = find_symbol_anchors(parsed_pdf, symbol)


def resolve_candidate(
    formula: dict[str, Any],
    unused_candidates: list[ParsedFormulaCandidate],
    candidate_map: dict[str, ParsedFormulaCandidate],
) -> ParsedFormulaCandidate | None:
    source_candidate_id = formula.get("sourceCandidateId")
    if isinstance(source_candidate_id, str) and source_candidate_id in candidate_map:
        return candidate_map[source_candidate_id]

    expression = normalize_expression(str(formula.get("expression") or ""))
    if not expression:
        return None

    best: tuple[float, ParsedFormulaCandidate] | None = None
    for candidate in unused_candidates:
        candidate_expr = normalize_expression(candidate.expression)
        if not candidate_expr:
            continue
        score = expression_similarity(expression, candidate_expr)
        if best is None or score > best[0]:
            best = (score, candidate)

    if best and best[0] >= 0.45:
        return best[1]
    return None


def enrich_dependencies(formulas: list[dict[str, Any]]) -> None:
    symbol_producer: dict[str, str] = {}

    for formula in formulas:
        semantic = formula.get("semantic") or {}
        lhs_symbols = semantic.get("lhsSymbols") or []
        if lhs_symbols:
            symbol_producer[lhs_symbols[0]] = formula["id"]

    for formula in formulas:
        semantic = formula.get("semantic") or {}
        rhs_symbols = semantic.get("rhsSymbols") or []
        computed_deps: list[str] = []
        for symbol in rhs_symbols:
            producer = symbol_producer.get(symbol)
            if producer and producer != formula["id"]:
                computed_deps.append(producer)

        merged = unique((formula.get("dependsOn") or []) + computed_deps)
        formula["dependsOn"] = merged[:6]


def build_chunks(expression: str, semantic: dict[str, Any], variable_ids: list[str]) -> list[dict[str, Any]]:
    operators = semantic.get("operators") or []
    lhs = ", ".join(semantic.get("lhsSymbols") or []) or "(none)"
    rhs = ", ".join(semantic.get("rhsSymbols") or []) or "(none)"

    chunks = [
        {
            "label": "Symbol mapping",
            "text": f"LHS symbols: {lhs}. RHS symbols: {rhs}.",
            "variableIds": variable_ids[:6],
        },
        {
            "label": "Operator structure",
            "text": f"Detected operators: {', '.join(operators) if operators else 'none'} in `{expression}`.",
            "variableIds": variable_ids[:6],
        },
    ]
    for idx, term in enumerate(split_expression_terms(expression), start=1):
        chunks.append(
            {
                "label": f"Term {idx}",
                "text": f"Local component: `{term}`.",
                "variableIds": [vid for vid in variable_ids if vid in {slugify_symbol(sym) for sym in extract_symbols(term)}][:6],
            }
        )
    return chunks


def analyze_expression(expression: str) -> dict[str, Any]:
    compact = expression.strip()
    left, right = split_expression(compact)
    lhs_symbols = extract_symbols(left)
    rhs_symbols = extract_symbols(right)
    operators = list(dict.fromkeys(re.findall(r"[=+\-*/^<>≤≥]", compact)))

    return {
        "lhsSymbols": lhs_symbols,
        "rhsSymbols": [sym for sym in rhs_symbols if sym not in lhs_symbols],
        "operators": operators,
        "complexity": len(operators) + len(rhs_symbols),
    }


def split_expression(expression: str) -> tuple[str, str]:
    if "=" in expression:
        left, right = expression.split("=", 1)
        return left.strip(), right.strip()
    return "", expression


def expression_similarity(a: str, b: str) -> float:
    if a == b:
        return 1.0

    a_symbols = set(extract_symbols(a))
    b_symbols = set(extract_symbols(b))
    if not a_symbols or not b_symbols:
        return 0.0

    overlap = len(a_symbols & b_symbols)
    union = len(a_symbols | b_symbols)
    return overlap / max(union, 1)


def normalize_expression(expression: str) -> str:
    return re.sub(r"\s+", "", expression).lower()


def extract_response_text(payload: dict[str, Any]) -> str:
    if payload.get("output_text"):
        return payload["output_text"]

    parts: list[str] = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if text:
                parts.append(text)
    return "\n".join(parts)


def extract_symbols(expression: str) -> list[str]:
    seen: list[str] = []
    for token in re.findall(r"[A-Za-zΑ-Ωα-ω]+(?:_[A-Za-z0-9()+-]+)?", expression):
        token_norm = token.strip()
        if token_norm.lower() in {"min", "max", "arg", "sin", "cos", "exp", "log"}:
            continue
        if token_norm not in seen:
            seen.append(token_norm)
    return seen[:14]


def slugify_symbol(symbol: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", symbol.lower())
    return slug.strip("-") or "var"


def infer_variable_name(symbol: str) -> str:
    mapping = {
        "E": "Energy",
        "J": "Objective",
        "P": "Power",
        "Q": "Flow quantity",
        "C": "Cost",
    }
    return mapping.get(symbol[:1].upper(), f"Variable {symbol}")


def infer_variable_type(symbol: str) -> str:
    return "Vector element" if "_" in symbol else "Scalar"


def infer_variable_role(symbol: str) -> str:
    if symbol[:1].isupper():
        return "Objective term"
    return "Process variable"


def summarize_formula_title(expression: str, index: int) -> str:
    lhs = expression.split("=")[0].strip() if "=" in expression else expression[:24]
    return f"Formula {index}: {lhs or 'expression'}"


def infer_fallback_formula(text: str) -> str:
    sentence = next((line.strip() for line in text.splitlines() if len(line.strip()) > 20), "No recoverable formula")
    return sentence[:120]


def unique(items) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def rank_formula_candidates(candidates: list[ParsedFormulaCandidate]) -> list[ParsedFormulaCandidate]:
    deduped: list[ParsedFormulaCandidate] = []
    seen: set[str] = set()
    for candidate in sorted(candidates, key=candidate_rank_key):
        key = normalize_expression(candidate.expression)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def candidate_rank_key(candidate: ParsedFormulaCandidate) -> tuple[int, float, int]:
    source_priority = {"nougat": 0, "ocr": 1, "text": 2}.get(candidate.source, 3)
    complexity = len(extract_symbols(candidate.expression)) + len(re.findall(r"[=+\-*/^<>≤≥]", candidate.expression))
    return (source_priority, -candidate.confidence, -complexity)


def find_symbol_anchors(parsed_pdf: ParsedPdf, symbol: str, limit: int = 3) -> list[str]:
    variants = symbol_search_variants(symbol)
    anchors: list[str] = []
    for page_index, block in enumerate(parsed_pdf.text_blocks, start=1):
        for sentence in split_sentences(block):
            normalized = normalize_sentence(sentence)
            if any(variant in normalized for variant in variants):
                anchors.append(f"p.{page_index}: {sentence}")
                if len(anchors) >= limit:
                    return anchors
    return anchors


def find_formula_anchors(parsed_pdf: ParsedPdf, expression: str, semantic: dict[str, Any] | None, limit: int = 3) -> list[str]:
    symbols = extract_symbols(expression)
    if semantic:
        symbols = unique(symbols + semantic.get("lhsSymbols", []) + semantic.get("rhsSymbols", []))
    anchors: list[str] = []
    for page_index, block in enumerate(parsed_pdf.text_blocks, start=1):
        for sentence in split_sentences(block):
            normalized = normalize_sentence(sentence)
            hits = sum(1 for variant in {v for symbol in symbols[:6] for v in symbol_search_variants(symbol)} if variant in normalized)
            if hits >= 2 or (hits >= 1 and len(symbols) <= 2):
                anchors.append(f"p.{page_index}: {sentence}")
                if len(anchors) >= limit:
                    return anchors
    return anchors


def split_sentences(text: str) -> list[str]:
    raw = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [segment.strip() for segment in raw if len(segment.strip()) >= 24]


def normalize_sentence(text: str) -> str:
    return re.sub(r"\s+", " ", text).lower()


def symbol_search_variants(symbol: str) -> set[str]:
    raw = symbol.strip()
    variants = {raw.lower()}
    variants.add(re.sub(r"[_{}\\]", "", raw).lower())
    variants.add(re.sub(r"[^a-z0-9]+", " ", raw.lower()).strip())
    return {variant for variant in variants if variant}


def split_expression_terms(expression: str) -> list[str]:
    if not expression:
        return []
    rhs = expression.split("=", 1)[1] if "=" in expression else expression
    pieces = [piece.strip() for piece in re.split(r"(?<!\^)\s*[+-]\s*", rhs) if piece.strip()]
    return pieces[:4]
