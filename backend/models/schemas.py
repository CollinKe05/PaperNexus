from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


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
    anchors: list[str] = Field(default_factory=list)


class FormulaChunk(BaseModel):
    label: str
    text: str
    variable_ids: list[str] = Field(default_factory=list, alias="variableIds")

    model_config = {"populate_by_name": True}


class FormulaSemantic(BaseModel):
    lhs_symbols: list[str] = Field(default_factory=list, alias="lhsSymbols")
    rhs_symbols: list[str] = Field(default_factory=list, alias="rhsSymbols")
    operators: list[str] = Field(default_factory=list)
    complexity: int = 0

    model_config = {"populate_by_name": True}


class Formula(BaseModel):
    id: str
    title: str
    expression: str
    physical_meaning: str = Field(alias="physicalMeaning")
    memory: str
    output: str | None = None
    page: int | None = None
    bbox: BoundingBox | None = None
    source_candidate_id: str | None = Field(default=None, alias="sourceCandidateId")
    semantic: FormulaSemantic | None = None
    inputs: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list, alias="dependsOn")
    paper_note: str = Field(alias="paperNote")
    chunks: list[FormulaChunk] = Field(default_factory=list)
    anchors: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class DocumentInsight(BaseModel):
    overview: str
    pipeline: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    document_title: str = Field(alias="documentTitle")
    source_filename: str = Field(alias="sourceFilename")
    pdf_url: str | None = Field(default=None, alias="pdfUrl")
    page_count: int = Field(alias="pageCount")
    language: str = "en"
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
    source: Literal["text", "ocr", "nougat"]
    bbox: BoundingBox | None = None
    confidence: float = 0.0


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
    nougat: str
    ocr: str
    llm: str


class AnalysisTaskCreateResponse(BaseModel):
    task_id: str = Field(alias="taskId")
    status: str
    stage: str
    message: str

    model_config = {"populate_by_name": True}


class AnalysisTaskStatusResponse(BaseModel):
    task_id: str = Field(alias="taskId")
    status: Literal["queued", "running", "completed", "failed"]
    stage: str
    progress: float
    message: str
    quick_mode: bool = Field(alias="quickMode")
    result: AnalysisResult | None = None
    error: str | None = None

    model_config = {"populate_by_name": True}
