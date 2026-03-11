from __future__ import annotations

import base64
from typing import Iterable

import httpx
import fitz

from backend.config import settings
from backend.models import ParsedFormulaCandidate


class OcrService:
    @property
    def available(self) -> bool:
        return bool(settings.mathpix_app_id and settings.mathpix_app_key)

    async def extract_formula_candidates(self, payload: bytes, existing_ids: set[str]) -> list[ParsedFormulaCandidate]:
        if not self.available:
            return []

        candidates: list[ParsedFormulaCandidate] = []
        document = fitz.open(stream=payload, filetype="pdf")

        async with httpx.AsyncClient(timeout=45.0) as client:
            for page_index, page in enumerate(document):
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image_bytes = pixmap.tobytes("png")
                latex = await self._call_mathpix(client, image_bytes)
                if not latex:
                    continue

                formula_id = f"p{page_index + 1}-ocr"
                if formula_id in existing_ids:
                    formula_id = f"p{page_index + 1}-ocr-alt"

                candidates.append(
                    ParsedFormulaCandidate(
                        id=formula_id,
                        expression=latex,
                        page=page_index + 1,
                        context="OCR extracted from rendered page image.",
                        source="ocr",
                    )
                )

        return candidates

    async def _call_mathpix(self, client: httpx.AsyncClient, image_bytes: bytes) -> str | None:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        response = await client.post(
            "https://api.mathpix.com/v3/text",
            headers={
                "app_id": settings.mathpix_app_id or "",
                "app_key": settings.mathpix_app_key or "",
                "Content-type": "application/json",
            },
            json={
                "src": f"data:image/png;base64,{encoded}",
                "formats": ["latex_styled"],
                "math_inline_delimiters": ["$", "$"],
                "rm_spaces": True,
            },
        )
        response.raise_for_status()
        data = response.json()
        latex = (data.get("latex_styled") or "").strip()
        if len(latex) < 6:
            return None
        return latex
