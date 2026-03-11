from __future__ import annotations

import json
import re
from typing import Any

import httpx

from backend.config import settings
from backend.models import AnalysisResult, ParsedPdf


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
                fallback.warnings.append(f"LLM request failed and heuristic fallback was used: {exc}")
                return fallback

        fallback = self._heuristic_analysis(parsed_pdf)
        fallback.status = "fallback"
        fallback.warnings.append("OPENAI_API_KEY is not configured, so heuristic analysis was used.")
        return fallback

    async def _analyze_with_openai(self, parsed_pdf: ParsedPdf) -> AnalysisResult:
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
                                        "You convert parsed academic paper content into a structured graph for an interactive reader. "
                                        "Return only valid JSON matching the schema. Preserve formula identifiers when possible."
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
        payload.setdefault("extractedText", parsed_pdf.full_text[:12000])
        payload.setdefault(
            "formulaCandidates",
            [candidate.expression for candidate in parsed_pdf.formula_candidates[:20]],
        )
        return AnalysisResult.model_validate(payload)

    def _heuristic_analysis(self, parsed_pdf: ParsedPdf) -> AnalysisResult:
        symbol_to_id: dict[str, str] = {}
        variables: list[dict[str, Any]] = []
        formulas: list[dict[str, Any]] = []
        dependencies: list[str] = []

        for index, candidate in enumerate(parsed_pdf.formula_candidates[:12], start=1):
            formula_id = f"f{index}"
            expression = candidate.expression
            symbols = extract_symbols(expression)
            input_ids: list[str] = []

            for symbol in symbols:
                variable_id = slugify_symbol(symbol)
                if variable_id not in symbol_to_id.values():
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
                        }
                    )
                else:
                    variable_id = symbol_to_id[symbol]
                    for variable in variables:
                        if variable["id"] == variable_id and formula_id not in variable["formulas"]:
                            variable["formulas"].append(formula_id)
                            break

                input_ids.append(variable_id)

            lhs_symbol = symbols[0] if symbols else None
            output_id = symbol_to_id.get(lhs_symbol) if lhs_symbol else None
            depends_on = dependencies[-1:] if dependencies else []
            dependencies.append(formula_id)

            formulas.append(
                {
                    "id": formula_id,
                    "title": summarize_formula_title(expression, index),
                    "expression": expression,
                    "physicalMeaning": candidate.context or "Formula extracted from PDF content.",
                    "memory": f"Formula candidate from page {candidate.page}.",
                    "output": output_id,
                    "inputs": unique(input_ids),
                    "dependsOn": depends_on,
                    "paperNote": f"Page {candidate.page} · source {candidate.source}",
                    "chunks": [
                        {
                            "label": "Context",
                            "text": candidate.context or "No additional context available.",
                            "variableIds": unique(input_ids[:6]),
                        }
                    ],
                }
            )

        if not formulas:
            fallback_expression = infer_fallback_formula(parsed_pdf.full_text)
            formulas.append(
                {
                    "id": "f1",
                    "title": "Recovered formula candidate",
                    "expression": fallback_expression,
                    "physicalMeaning": "No explicit formula-like line was detected, so this placeholder summarizes the extracted text.",
                    "memory": "Connect real OCR or richer parsing to improve this result.",
                    "output": None,
                    "inputs": [],
                    "dependsOn": [],
                    "paperNote": "Generated fallback",
                    "chunks": [{"label": "Fallback", "text": parsed_pdf.full_text[:500] or "No text extracted.", "variableIds": []}],
                }
            )

        overview = (
            f"Paper parsed from {parsed_pdf.page_count} page(s). {len(formulas)} formula candidates and "
            f"{len(variables)} variable candidates were reconstructed into the interactive graph."
        )

        return AnalysisResult.model_validate(
            {
                "documentTitle": parsed_pdf.title,
                "sourceFilename": parsed_pdf.source_filename,
                "pageCount": parsed_pdf.page_count,
                "status": "ok",
                "variables": variables,
                "formulas": formulas,
                "documentInsight": {
                    "overview": overview,
                    "pipeline": [
                        "PDF parsing layer: PyMuPDF text extraction and formula-pattern scan.",
                        "OCR layer: Mathpix integration when credentials are configured.",
                        "Semantic layer: heuristic reconstruction because LLM output was unavailable.",
                    ],
                },
                "extractedText": parsed_pdf.full_text[:20000],
                "formulaCandidates": [candidate.expression for candidate in parsed_pdf.formula_candidates[:20]],
                "warnings": parsed_pdf.warnings,
            }
        )


def build_prompt(parsed_pdf: ParsedPdf) -> str:
    formula_lines = "\n".join(
        f"- {candidate.id} | page {candidate.page} | {candidate.source}: {candidate.expression}\n  context: {candidate.context}"
        for candidate in parsed_pdf.formula_candidates[:25]
    )
    return f"""
Analyze this parsed paper and reconstruct it into an interactive graph dataset.

Document title: {parsed_pdf.title}
Source filename: {parsed_pdf.source_filename}
Page count: {parsed_pdf.page_count}

Extracted text (possibly truncated):
{parsed_pdf.full_text[:18000]}

Formula candidates:
{formula_lines or '- none detected'}

Requirements:
- Produce variables with stable ids and attach each variable to related formulas.
- Produce formulas with concise titles, physical meaning, memory hooks, dependencies, and explanation chunks.
- Keep dependsOn relationships sparse and plausible.
- Return document insight summary for the three-layer pipeline.
- If information is missing, infer conservatively from the provided text only.
""".strip()


def build_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "documentTitle",
            "sourceFilename",
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
                    },
                },
            },
            "formulas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "title", "expression", "physicalMeaning", "memory", "output", "inputs", "dependsOn", "paperNote", "chunks"],
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "expression": {"type": "string"},
                        "physicalMeaning": {"type": "string"},
                        "memory": {"type": "string"},
                        "output": {"type": ["string", "null"]},
                        "inputs": {"type": "array", "items": {"type": "string"}},
                        "dependsOn": {"type": "array", "items": {"type": "string"}},
                        "paperNote": {"type": "string"},
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
        if token.lower() in {"min", "max", "arg", "s", "t"}:
            continue
        if token not in seen:
            seen.append(token)
    return seen[:10]


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
    return f"Formula {index}: {lhs}"


def infer_fallback_formula(text: str) -> str:
    sentence = next((line.strip() for line in text.splitlines() if len(line.strip()) > 20), "No recoverable formula")
    return sentence[:120]


def unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))
