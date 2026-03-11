from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Variable(BaseModel):
    id: str
    symbol: str
    name: str
    type: str
    unit: str = "-"
    role: str
    meaning: str
    memory: str
    source: str
    formulas: list[str] = Field(default_factory=list)


class FormulaChunk(BaseModel):
    label: str
    text: str
    variable_ids: list[str] = Field(default_factory=list, alias="variableIds")

    model_config = {"populate_by_name": True}


class Formula(BaseModel):
    id: str
    title: str
    expression: str
    physical_meaning: str = Field(alias="physicalMeaning")
    memory: str
    output: str | None = None
    inputs: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list, alias="dependsOn")
    paper_note: str = Field(alias="paperNote")
    chunks: list[FormulaChunk] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class DocumentInsight(BaseModel):
    overview: str
    pipeline: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    document_title: str = Field(alias="documentTitle")
    source_filename: str = Field(alias="sourceFilename")
    page_count: int = Field(alias="pageCount")
    status: Literal["ok", "fallback"] = "ok"
    variables: list[Variable]
    formulas: list[Formula]
    document_insight: DocumentInsight = Field(alias="documentInsight")
    extracted_text: str = Field(alias="extractedText")
    formula_candidates: list[str] = Field(default_factory=list, alias="formulaCandidates")
    warnings: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class ParsedFormulaCandidate(BaseModel):
    id: str
    expression: str
    page: int
    context: str
    source: Literal["text", "ocr"]


class ParsedPdf(BaseModel):
    title: str
    source_filename: str
    page_count: int
    full_text: str
    text_blocks: list[str] = Field(default_factory=list)
    formula_candidates: list[ParsedFormulaCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    pdf_parser: str
    ocr: str
    llm: str
