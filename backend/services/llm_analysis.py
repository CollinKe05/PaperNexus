from __future__ import annotations

import json
import re
from typing import Any

import httpx

from backend.config import settings
from backend.models import AnalysisResult, ParsedFormulaCandidate, ParsedPdf


LANGUAGE_TEXT = {
    "en": {
        "llm_failed": "LLM request failed and semantic fallback was used: {error}",
        "no_openai_key": "OPENAI_API_KEY is not configured, so semantic fallback analysis was used.",
        "symbol_meaning": "This symbol was extracted from formula `{expression}`.",
        "symbol_memory": "Track `{symbol}` as one of the core symbols in this paper.",
        "detected_from_page": "Detected from page {page}",
        "formula_from_pdf": "Formula extracted from PDF content.",
        "formula_memory": "Formula candidate from page {page}.",
        "paper_note": "Page {page} | source {source} | confidence {confidence:.2f}",
        "recovered_formula_title": "Recovered formula candidate",
        "fallback_physical_meaning": "No explicit formula-like line was detected, so this placeholder summarizes the extracted text.",
        "fallback_memory": "Connect richer OCR and parsing to improve this result.",
        "generated_fallback": "Generated fallback",
        "fallback_label": "Fallback",
        "no_text_extracted": "No text extracted.",
        "overview": "Paper parsed from {page_count} page(s). {formula_count} formula candidates and {variable_count} variable candidates were reconstructed with page-anchored semantics.",
        "pipeline_pdf": "PDF parsing: line-level formula region detection with normalized bounding boxes.",
        "pipeline_ocr": "OCR: Mathpix region-aware extraction when credentials are configured.",
        "pipeline_semantic": "Semantic parsing: operator and symbol analysis with dependency reconstruction.",
        "title_formula": "Formula {index}: {lhs}",
        "title_expression": "Formula {index}: expression",
        "name_variable": "Variable {symbol}",
        "type_matrix": "Matrix",
        "type_vector": "Vector",
        "type_scalar": "Scalar",
        "role_objective": "Objective term",
        "role_process": "Process variable",
        "role_parameter": "Parameter",
        "chunk_symbol_mapping": "Symbol mapping",
        "chunk_symbol_text": "LHS symbols: {lhs}. RHS symbols: {rhs}.",
        "chunk_operator_structure": "Operator structure",
        "chunk_operator_text": "Detected operators: {operators} in `{expression}`.",
        "chunk_term": "Term {index}",
        "chunk_term_text": "Local component: `{term}`.",
        "language_instruction": "English",
        "warning_passthrough": "{warning}",
        "formula_context_default": "Formula extracted from paper context.",
        "fallback_formula": "No recoverable formula",
    },
    "zh": {
        "llm_failed": "LLM 请求失败，已改用启发式语义分析：{error}",
        "no_openai_key": "未配置 OPENAI_API_KEY，因此当前结果使用启发式语义分析生成。",
        "symbol_meaning": "该符号从公式 `{expression}` 中提取。",
        "symbol_memory": "可将 `{symbol}` 视为本文中的核心符号之一。",
        "detected_from_page": "识别自第 {page} 页",
        "formula_from_pdf": "该公式从 PDF 内容中提取。",
        "formula_memory": "这是来自第 {page} 页的公式候选。",
        "paper_note": "第 {page} 页 | 来源 {source} | 置信度 {confidence:.2f}",
        "recovered_formula_title": "恢复出的公式候选",
        "fallback_physical_meaning": "没有检测到明确的公式行，因此这里用占位结果概括提取到的文本。",
        "fallback_memory": "如果接入更强的 OCR 与解析流程，这部分结果会更准确。",
        "generated_fallback": "自动生成的占位结果",
        "fallback_label": "占位解释",
        "no_text_extracted": "未提取到文本。",
        "overview": "论文共 {page_count} 页，重建出 {formula_count} 条公式候选与 {variable_count} 个变量候选，并尽量保留页码锚点。",
        "pipeline_pdf": "PDF 解析：基于行与位置框的公式区域检测。",
        "pipeline_ocr": "OCR：若配置凭据，则使用 Mathpix 做区域增强识别。",
        "pipeline_semantic": "语义解析：基于运算符与符号关系重建依赖图。",
        "title_formula": "公式 {index}：{lhs}",
        "title_expression": "公式 {index}：表达式",
        "name_variable": "变量 {symbol}",
        "type_matrix": "矩阵",
        "type_vector": "向量",
        "type_scalar": "标量",
        "role_objective": "目标项",
        "role_process": "过程变量",
        "role_parameter": "参数",
        "chunk_symbol_mapping": "符号映射",
        "chunk_symbol_text": "左侧符号：{lhs}。右侧符号：{rhs}。",
        "chunk_operator_structure": "运算结构",
        "chunk_operator_text": "在 `{expression}` 中检测到的运算符：{operators}。",
        "chunk_term": "局部项 {index}",
        "chunk_term_text": "局部组成部分：`{term}`。",
        "language_instruction": "Simplified Chinese",
        "warning_passthrough": "{warning}",
        "formula_context_default": "该公式从论文上下文中提取。",
        "fallback_formula": "未恢复出可用公式",
    },
}

FUNCTION_WORDS = {"min", "max", "arg", "sin", "cos", "tan", "exp", "log", "ln", "softmax", "concat", "relu"}
SYMBOL_RE = re.compile(r"[A-Za-z]+(?:_[A-Za-z0-9]+|_\\{[A-Za-z0-9]+\\})?")
OPERATOR_RE = re.compile(r"(<=|>=|!=|=|\\+|-|\\*|/|\\^|<|>)")


class LlmAnalysisService:
    @property
    def available(self) -> bool:
        return bool(settings.openai_api_key)

    async def analyze(self, parsed_pdf: ParsedPdf, language: str = "en") -> AnalysisResult:
        language = normalize_language(language)
        if self.available:
            try:
                return await self._analyze_with_openai(parsed_pdf, language)
            except Exception as exc:
                fallback = self._heuristic_analysis(parsed_pdf, language)
                fallback.status = "fallback"
                fallback.warnings.append(localize_text(language, "llm_failed").format(error=exc))
                return fallback

        fallback = self._heuristic_analysis(parsed_pdf, language)
        fallback.status = "fallback"
        fallback.warnings.append(localize_text(language, "no_openai_key"))
        return fallback

    async def _analyze_with_openai(self, parsed_pdf: ParsedPdf, language: str) -> AnalysisResult:
        prioritized_candidates = rank_formula_candidates(parsed_pdf.formula_candidates)
        prompt = build_prompt(parsed_pdf, language)
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
                        {"role": "user", "content": [{"type": "input_text", "text": prompt}]},
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
        payload.setdefault("warnings", [localize_warning(language, warning) for warning in parsed_pdf.warnings])
        payload.setdefault("sourceFilename", parsed_pdf.source_filename)
        payload.setdefault("pageCount", parsed_pdf.page_count)
        payload.setdefault("documentTitle", parsed_pdf.title)
        payload.setdefault("pdfUrl", None)
        payload.setdefault("language", language)
        payload.setdefault("extractedText", parsed_pdf.full_text[:12000])
        payload.setdefault("formulaCandidates", [candidate.expression for candidate in prioritized_candidates[:20]])

        enrich_formulas(payload.setdefault("formulas", []), parsed_pdf, language)
        enrich_variables(payload.setdefault("variables", []), parsed_pdf)
        return AnalysisResult.model_validate(payload)

    def _heuristic_analysis(self, parsed_pdf: ParsedPdf, language: str) -> AnalysisResult:
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
                            "name": infer_variable_name(symbol, language),
                            "type": infer_variable_type(symbol, language),
                            "unit": "-",
                            "role": infer_variable_role(symbol, language),
                            "meaning": localize_text(language, "symbol_meaning").format(expression=expression),
                            "memory": localize_text(language, "symbol_memory").format(symbol=symbol),
                            "source": localize_text(language, "detected_from_page").format(page=candidate.page),
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
                    "title": summarize_formula_title(expression, index, language),
                    "expression": expression,
                    "physicalMeaning": candidate.context or localize_text(language, "formula_from_pdf"),
                    "memory": localize_text(language, "formula_memory").format(page=candidate.page),
                    "output": output_id,
                    "page": candidate.page,
                    "bbox": candidate.bbox.model_dump() if candidate.bbox else None,
                    "sourceCandidateId": candidate.id,
                    "semantic": semantic,
                    "inputs": unique(input_ids),
                    "dependsOn": [],
                    "paperNote": localize_text(language, "paper_note").format(
                        page=candidate.page, source=candidate.source, confidence=candidate.confidence
                    ),
                    "chunks": build_chunks(expression, semantic, unique(input_ids), language),
                    "anchors": find_formula_anchors(parsed_pdf, expression, semantic),
                }
            )

        if not formulas:
            fallback_expression = infer_fallback_formula(parsed_pdf.full_text, language)
            formulas.append(
                {
                    "id": "f1",
                    "title": localize_text(language, "recovered_formula_title"),
                    "expression": fallback_expression,
                    "physicalMeaning": localize_text(language, "fallback_physical_meaning"),
                    "memory": localize_text(language, "fallback_memory"),
                    "output": None,
                    "page": 1,
                    "bbox": None,
                    "sourceCandidateId": None,
                    "semantic": analyze_expression(fallback_expression),
                    "inputs": [],
                    "dependsOn": [],
                    "paperNote": localize_text(language, "generated_fallback"),
                    "chunks": [
                        {
                            "label": localize_text(language, "fallback_label"),
                            "text": parsed_pdf.full_text[:500] or localize_text(language, "no_text_extracted"),
                            "variableIds": [],
                        }
                    ],
                    "anchors": [],
                }
            )

        enrich_dependencies(formulas)
        return AnalysisResult.model_validate(
            {
                "documentTitle": parsed_pdf.title,
                "sourceFilename": parsed_pdf.source_filename,
                "pdfUrl": None,
                "pageCount": parsed_pdf.page_count,
                "language": language,
                "status": "ok",
                "variables": variables,
                "formulas": formulas,
                "documentInsight": {
                    "overview": localize_text(language, "overview").format(
                        page_count=parsed_pdf.page_count,
                        formula_count=len(formulas),
                        variable_count=len(variables),
                    ),
                    "pipeline": [
                        localize_text(language, "pipeline_pdf"),
                        localize_text(language, "pipeline_ocr"),
                        localize_text(language, "pipeline_semantic"),
                    ],
                },
                "extractedText": parsed_pdf.full_text[:20000],
                "formulaCandidates": [candidate.expression for candidate in parsed_pdf.formula_candidates[:24]],
                "warnings": [localize_warning(language, warning) for warning in parsed_pdf.warnings],
            }
        )


def build_prompt(parsed_pdf: ParsedPdf, language: str) -> str:
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

Output language for all human-readable fields:
{language_instruction(language)}

Document title: {parsed_pdf.title}
Source filename: {parsed_pdf.source_filename}
Page count: {parsed_pdf.page_count}

Extracted text (possibly truncated):
{parsed_pdf.full_text[:18000]}

Formula candidates with page grounding and bounding boxes:
{formula_lines or "- none detected"}

Requirements:
- Produce variables with stable ids and attach each variable to related formulas.
- Produce formulas with concise titles, physical meaning, memory hooks, dependencies, chunks, and semantic metadata.
- Every formula must include page, sourceCandidateId (or null), bbox (or null), and semantic object.
- Keep dependencies sparse and precise.
- Do not hallucinate symbols not present in text or candidates unless absolutely required.
- Use the requested output language for titles, explanations, notes, memory hooks, document insight, warnings, and chunk text.
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
            "language",
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
            "language": {"type": "string", "enum": ["en", "zh"]},
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
                        "id", "title", "expression", "physicalMeaning", "memory", "output", "page", "bbox",
                        "sourceCandidateId", "semantic", "inputs", "dependsOn", "paperNote", "chunks"
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


def enrich_formulas(formulas: list[dict[str, Any]], parsed_pdf: ParsedPdf, language: str) -> None:
    candidate_map = {candidate.id: candidate for candidate in parsed_pdf.formula_candidates}
    unused_candidates = rank_formula_candidates(parsed_pdf.formula_candidates)
    for idx, formula in enumerate(formulas, start=1):
        formula.setdefault("id", f"f{idx}")
        formula.setdefault("title", summarize_formula_title(str(formula.get("expression") or ""), idx, language))
        formula.setdefault("physicalMeaning", localize_text(language, "formula_context_default"))
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
    return best[1] if best and best[0] >= 0.45 else None


def enrich_dependencies(formulas: list[dict[str, Any]]) -> None:
    symbol_producer: dict[str, str] = {}
    for formula in formulas:
        lhs_symbols = (formula.get("semantic") or {}).get("lhsSymbols") or []
        if lhs_symbols:
            symbol_producer[lhs_symbols[0]] = formula["id"]
    for formula in formulas:
        rhs_symbols = (formula.get("semantic") or {}).get("rhsSymbols") or []
        computed = []
        for symbol in rhs_symbols:
            producer = symbol_producer.get(symbol)
            if producer and producer != formula["id"]:
                computed.append(producer)
        formula["dependsOn"] = unique((formula.get("dependsOn") or []) + computed)[:6]


def build_chunks(expression: str, semantic: dict[str, Any], variable_ids: list[str], language: str) -> list[dict[str, Any]]:
    operators = semantic.get("operators") or []
    lhs = ", ".join(semantic.get("lhsSymbols") or []) or "(none)"
    rhs = ", ".join(semantic.get("rhsSymbols") or []) or "(none)"
    chunks = [
        {
            "label": localize_text(language, "chunk_symbol_mapping"),
            "text": localize_text(language, "chunk_symbol_text").format(lhs=lhs, rhs=rhs),
            "variableIds": variable_ids[:6],
        },
        {
            "label": localize_text(language, "chunk_operator_structure"),
            "text": localize_text(language, "chunk_operator_text").format(
                operators=", ".join(operators) if operators else "none",
                expression=expression,
            ),
            "variableIds": variable_ids[:6],
        },
    ]
    for idx, term in enumerate(split_expression_terms(expression), start=1):
        term_symbols = {slugify_symbol(sym) for sym in extract_symbols(term)}
        chunks.append(
            {
                "label": localize_text(language, "chunk_term").format(index=idx),
                "text": localize_text(language, "chunk_term_text").format(term=term),
                "variableIds": [vid for vid in variable_ids if vid in term_symbols][:6],
            }
        )
    return chunks


def analyze_expression(expression: str) -> dict[str, Any]:
    left, right = split_expression(expression.strip())
    lhs_symbols = extract_symbols(left)
    rhs_symbols = [sym for sym in extract_symbols(right) if sym not in lhs_symbols]
    operators = list(dict.fromkeys(match.group(0) for match in OPERATOR_RE.finditer(expression)))
    return {"lhsSymbols": lhs_symbols, "rhsSymbols": rhs_symbols, "operators": operators, "complexity": len(operators) + len(rhs_symbols)}


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
    return len(a_symbols & b_symbols) / max(len(a_symbols | b_symbols), 1)


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
    for token in SYMBOL_RE.findall(expression):
        token = token.strip()
        if token.lower() in FUNCTION_WORDS:
            continue
        if token not in seen:
            seen.append(token)
    return seen[:14]


def slugify_symbol(symbol: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", symbol.lower())
    return slug.strip("-") or "var"


def infer_variable_name(symbol: str, language: str) -> str:
    mapping = {
        "en": {"E": "Energy", "J": "Objective", "P": "Power", "Q": "Query", "K": "Key", "V": "Value", "C": "Cost"},
        "zh": {"E": "能量", "J": "目标函数", "P": "功率", "Q": "查询", "K": "键", "V": "值", "C": "成本"},
    }
    return mapping[normalize_language(language)].get(symbol[:1].upper(), localize_text(language, "name_variable").format(symbol=symbol))


def infer_variable_type(symbol: str, language: str) -> str:
    if "^" in symbol or symbol[:1].isupper():
        return localize_text(language, "type_matrix")
    if "_" in symbol:
        return localize_text(language, "type_vector")
    return localize_text(language, "type_scalar")


def infer_variable_role(symbol: str, language: str) -> str:
    if symbol[:1].isupper():
        return localize_text(language, "role_objective")
    if "_" in symbol:
        return localize_text(language, "role_process")
    return localize_text(language, "role_parameter")


def summarize_formula_title(expression: str, index: int, language: str) -> str:
    lhs = expression.split("=", 1)[0].strip() if "=" in expression else expression[:24]
    return localize_text(language, "title_formula").format(index=index, lhs=lhs) if lhs else localize_text(language, "title_expression").format(index=index)


def infer_fallback_formula(text: str, language: str) -> str:
    sentence = next((line.strip() for line in text.splitlines() if len(line.strip()) > 20), "")
    return sentence[:120] if sentence else localize_text(language, "fallback_formula")


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
    complexity = len(extract_symbols(candidate.expression)) + len(OPERATOR_RE.findall(candidate.expression))
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
    variants = {variant for symbol in symbols[:6] for variant in symbol_search_variants(symbol)}
    anchors: list[str] = []
    for page_index, block in enumerate(parsed_pdf.text_blocks, start=1):
        for sentence in split_sentences(block):
            normalized = normalize_sentence(sentence)
            hits = sum(1 for variant in variants if variant in normalized)
            if hits >= 2 or (hits >= 1 and len(symbols) <= 2):
                anchors.append(f"p.{page_index}: {sentence}")
                if len(anchors) >= limit:
                    return anchors
    return anchors


def split_sentences(text: str) -> list[str]:
    return [segment.strip() for segment in re.split(r"(?<=[.!?])\s+|\n+", text) if len(segment.strip()) >= 24]


def normalize_sentence(text: str) -> str:
    return re.sub(r"\s+", " ", text).lower()


def symbol_search_variants(symbol: str) -> set[str]:
    raw = symbol.strip()
    variants = {raw.lower(), re.sub(r"[_{}\\]", "", raw).lower(), re.sub(r"[^a-z0-9]+", " ", raw.lower()).strip()}
    return {item for item in variants if item}


def split_expression_terms(expression: str) -> list[str]:
    rhs = expression.split("=", 1)[1] if "=" in expression else expression
    return [piece.strip() for piece in re.split(r"(?<!\^)\s*[+-]\s*", rhs) if piece.strip()][:4]


def normalize_language(language: str | None) -> str:
    return "zh" if str(language or "").lower().startswith("zh") else "en"


def localize_text(language: str, key: str) -> str:
    return LANGUAGE_TEXT[normalize_language(language)][key]


def language_instruction(language: str) -> str:
    return localize_text(language, "language_instruction")


def localize_warning(language: str, warning: str) -> str:
    return localize_text(language, "warning_passthrough").format(warning=warning)
