from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.models import AnalysisResult, HealthResponse
from backend.services import LlmAnalysisService, OcrService, PdfParserService

app = FastAPI(title="PaperNexus API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pdf_parser = PdfParserService()
ocr_service = OcrService()
llm_service = LlmAnalysisService()
base_dir = Path(__file__).resolve().parent.parent
upload_dir = base_dir / settings.upload_dir
upload_dir.mkdir(parents=True, exist_ok=True)

app.mount("/src", StaticFiles(directory=base_dir / "src"), name="src")
app.mount("/backend", StaticFiles(directory=base_dir / "backend"), name="backend")


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        pdf_parser="PyMuPDF",
        ocr="Mathpix" if ocr_service.available else "disabled",
        llm=settings.openai_model if llm_service.available else "heuristic fallback",
    )


@app.post("/api/analyze", response_model=AnalysisResult)
async def analyze_pdf(file: UploadFile = File(...)) -> AnalysisResult:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    max_size = settings.max_upload_mb * 1024 * 1024
    if len(payload) > max_size:
        raise HTTPException(status_code=400, detail=f"File too large. Max size is {settings.max_upload_mb} MB.")

    saved_path = upload_dir / Path(file.filename).name
    saved_path.write_bytes(payload)

    parsed = pdf_parser.parse(file.filename, payload)
    ocr_candidates = await ocr_service.extract_formula_candidates(payload, {item.id for item in parsed.formula_candidates})
    if ocr_candidates:
        parsed.formula_candidates.extend(ocr_candidates)
    elif ocr_service.available:
        parsed.warnings.append("OCR was configured but did not return additional formulas.")
    else:
        parsed.warnings.append("OCR credentials are not configured; only embedded PDF text was parsed.")

    return await llm_service.analyze(parsed)


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    return FileResponse(base_dir / "index.html")


@app.get("/styles.css", include_in_schema=False)
def styles() -> FileResponse:
    return FileResponse(base_dir / "styles.css")
