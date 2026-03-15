from __future__ import annotations

import base64

import fitz
import httpx

from backend.config import settings
from backend.models import BoundingBox, ParsedFormulaCandidate


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
                response_json = await self._call_mathpix(client, image_bytes)
                latex = (response_json.get("latex_styled") or "").strip()
                if len(latex) < 6:
                    continue

                formula_id = f"p{page_index + 1}-ocr"
                if formula_id in existing_ids:
                    formula_id = f"p{page_index + 1}-ocr-alt"

                bbox = parse_mathpix_bbox(response_json, pixmap.width, pixmap.height)
                confidence = parse_mathpix_confidence(response_json)

                candidates.append(
                    ParsedFormulaCandidate(
                        id=formula_id,
                        expression=latex,
                        page=page_index + 1,
                        context="OCR extracted from rendered page image.",
                        source="ocr",
                        bbox=bbox,
                        confidence=confidence,
                    )
                )

        return candidates

    async def _call_mathpix(self, client: httpx.AsyncClient, image_bytes: bytes) -> dict:
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
                "include_line_data": True,
            },
        )
        response.raise_for_status()
        return response.json()


def parse_mathpix_bbox(payload: dict, image_width: int, image_height: int) -> BoundingBox | None:
    line_data = payload.get("line_data") or []
    if not line_data:
        return None

    # Mathpix line_data can expose either a bbox-like object or cnt polygon.
    item = line_data[0]
    if isinstance(item, dict):
        if all(key in item for key in ("left", "top", "width", "height")):
            x0 = float(item["left"]) / max(image_width, 1)
            y0 = float(item["top"]) / max(image_height, 1)
            x1 = x0 + float(item["width"]) / max(image_width, 1)
            y1 = y0 + float(item["height"]) / max(image_height, 1)
            return clamp_bbox(x0, y0, x1, y1)

        cnt = item.get("cnt")
        if isinstance(cnt, list) and len(cnt) >= 4:
            xs = [point[0] for point in cnt if isinstance(point, (list, tuple)) and len(point) >= 2]
            ys = [point[1] for point in cnt if isinstance(point, (list, tuple)) and len(point) >= 2]
            if xs and ys:
                x0 = min(xs) / max(image_width, 1)
                y0 = min(ys) / max(image_height, 1)
                x1 = max(xs) / max(image_width, 1)
                y1 = max(ys) / max(image_height, 1)
                return clamp_bbox(x0, y0, x1, y1)

    return None


def parse_mathpix_confidence(payload: dict) -> float:
    confidence = payload.get("confidence")
    if isinstance(confidence, (float, int)):
        return float(max(0.0, min(1.0, confidence)))
    return 0.62


def clamp_bbox(x0: float, y0: float, x1: float, y1: float) -> BoundingBox:
    return BoundingBox(
        x0=max(0.0, min(1.0, x0)),
        y0=max(0.0, min(1.0, y0)),
        x1=max(0.0, min(1.0, x1)),
        y1=max(0.0, min(1.0, y1)),
    )
