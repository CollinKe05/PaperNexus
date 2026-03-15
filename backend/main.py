from __future__ import annotations

import asyncio
from pathlib import Path

import fitz
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.models import AnalysisResult, AnalysisTaskCreateResponse, AnalysisTaskStatusResponse, HealthResponse
from backend.services import AnalysisTaskManager, LlmAnalysisService, NougatService, OcrService, PdfParserService

app = FastAPI(title="PaperNexus API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pdf_parser = PdfParserService()
nougat_service = NougatService()
ocr_service = OcrService()
llm_service = LlmAnalysisService()
task_manager = AnalysisTaskManager()
base_dir = Path(__file__).resolve().parent.parent
upload_dir = base_dir / settings.upload_dir
upload_dir.mkdir(parents=True, exist_ok=True)

app.mount("/src", StaticFiles(directory=base_dir / "src"), name="src")
app.mount("/backend", StaticFiles(directory=base_dir / "backend"), name="backend")
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        pdf_parser="PyMuPDF(line+bbox detection)",
        nougat="enabled" if nougat_service.available else "disabled",
        ocr="Mathpix" if ocr_service.available else "disabled",
        llm=settings.openai_model if llm_service.available else "semantic fallback",
    )


@app.post("/api/analyze", response_model=AnalysisTaskCreateResponse)
async def analyze_pdf(
    file: UploadFile = File(...),
    quick_mode: bool = Form(False),
) -> AnalysisTaskCreateResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    max_size = settings.max_upload_mb * 1024 * 1024
    if len(payload) > max_size:
        raise HTTPException(status_code=400, detail=f"File too large. Max size is {settings.max_upload_mb} MB.")

    safe_name = Path(file.filename).name
    saved_path = upload_dir / safe_name
    saved_path.write_bytes(payload)

    task = task_manager.create(quick_mode=quick_mode)
    await task_manager.update(
        task.task_id,
        status="queued",
        stage="uploaded",
        progress=0.05,
        message=f"Uploaded {safe_name}. Waiting to start parsing.",
    )
    asyncio.create_task(run_analysis_pipeline(task.task_id, safe_name, payload, quick_mode))

    return AnalysisTaskCreateResponse(
        taskId=task.task_id,
        status=task.status,
        stage=task.stage,
        message=task.message,
    )


@app.get("/api/tasks/{task_id}", response_model=AnalysisTaskStatusResponse)
def get_analysis_task(task_id: str) -> AnalysisTaskStatusResponse:
    task = task_manager.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Analysis task not found.")
    return task.to_response()


async def run_analysis_pipeline(task_id: str, safe_name: str, payload: bytes, quick_mode: bool) -> None:
    try:
        await task_manager.update(
            task_id,
            status="running",
            stage="pymupdf_processing",
            progress=0.12,
            message="Running PyMuPDF formula extraction.",
        )
        parsed = pdf_parser.parse(safe_name, payload)

        await task_manager.update(
            task_id,
            status="running",
            stage="pymupdf_done",
            progress=0.34,
            message=f"PyMuPDF extracted {len(parsed.formula_candidates)} formula candidates from {parsed.page_count} page(s).",
        )

        await task_manager.update(
            task_id,
            status="running",
            stage="semantic_analysis",
            progress=0.48,
            message="Building the first interactive view from PyMuPDF results.",
        )
        initial_result = await llm_service.analyze(parsed)
        attach_pdf_url(initial_result, safe_name)

        should_skip_nougat = quick_mode or parsed.page_count > settings.nougat_max_pages or not nougat_service.available
        if quick_mode:
            initial_result.warnings.append("Quick mode enabled: Nougat enhancement was skipped.")
        elif parsed.page_count > settings.nougat_max_pages:
            initial_result.warnings.append(
                f"Nougat skipped because the document has {parsed.page_count} pages, above the {settings.nougat_max_pages}-page threshold."
            )
        elif not nougat_service.available:
            initial_result.warnings.append("Nougat is disabled or not installed, so only PyMuPDF candidates were used.")

        await task_manager.update(
            task_id,
            status="running" if not should_skip_nougat else "completed",
            stage="pymupdf_done" if not should_skip_nougat else "completed",
            progress=0.55 if not should_skip_nougat else 1.0,
            message="Initial result is ready. Rendering PyMuPDF output." if not should_skip_nougat else "Analysis completed in quick path.",
            result=initial_result,
        )

        if should_skip_nougat:
            return

        try:
            await task_manager.update(
                task_id,
                status="running",
                stage="nougat_processing",
                progress=0.68,
                message="Nougat is processing the PDF in the background.",
            )
            nougat_candidates = await nougat_service.extract_formula_candidates(
                payload,
                {item.id for item in parsed.formula_candidates},
                parsed.page_count,
            )
            if nougat_candidates:
                parsed.formula_candidates.extend(nougat_candidates)
            else:
                parsed.warnings.append("Nougat finished but did not return additional formula candidates.")
        except Exception as exc:
            parsed.warnings.append(f"Nougat enhancement failed: {exc}")

        if ocr_service.available:
            try:
                await task_manager.update(
                    task_id,
                    status="running",
                    stage="nougat_processing",
                    progress=0.78,
                    message="Nougat finished. OCR enhancement is running.",
                )
                ocr_candidates = await ocr_service.extract_formula_candidates(payload, {item.id for item in parsed.formula_candidates})
                if ocr_candidates:
                    parsed.formula_candidates.extend(ocr_candidates)
                else:
                    parsed.warnings.append("OCR was configured but did not return additional formulas.")
            except Exception as exc:
                parsed.warnings.append(f"OCR enhancement failed: {exc}")

        try:
            await task_manager.update(
                task_id,
                status="running",
                stage="semantic_analysis",
                progress=0.88,
                message="Rebuilding the semantic graph with Nougat-enhanced formulas.",
            )
            enhanced_result = await llm_service.analyze(parsed)
            attach_pdf_url(enhanced_result, safe_name)
        except Exception as exc:
            initial_result.warnings.append(f"Enhanced semantic rebuild failed, so the initial PyMuPDF result was kept: {exc}")
            await task_manager.update(
                task_id,
                status="completed",
                stage="completed",
                progress=1.0,
                message="Analysis completed, but enhancement fell back to the initial PyMuPDF result.",
                result=initial_result,
            )
            return

        await task_manager.update(
            task_id,
            status="completed",
            stage="completed",
            progress=1.0,
            message="Analysis completed with Nougat enhancement.",
            result=enhanced_result,
        )
    except Exception as exc:
        await task_manager.update(
            task_id,
            status="failed",
            stage="failed",
            progress=1.0,
            message="Analysis failed.",
            error=str(exc),
        )


def attach_pdf_url(result: AnalysisResult, filename: str) -> None:
    result.pdf_url = f"/uploads/{filename}"


@app.get("/api/pdf-page-image/{filename}/{page}")
def pdf_page_image(filename: str, page: int, scale: float = Query(2.0, ge=1.0, le=4.0)) -> Response:
    safe_name = Path(filename).name
    file_path = upload_dir / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found.")

    try:
        document = fitz.open(file_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to open PDF: {exc}") from exc

    if page < 1 or page > document.page_count:
        raise HTTPException(status_code=400, detail=f"Page out of range. Must be between 1 and {document.page_count}.")

    pdf_page = document[page - 1]
    pixmap = pdf_page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    return Response(content=pixmap.tobytes("png"), media_type="image/png")


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    return FileResponse(base_dir / "index.html")


@app.get("/styles.css", include_in_schema=False)
def styles() -> FileResponse:
    return FileResponse(base_dir / "styles.css")
