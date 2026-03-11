from __future__ import annotations

import io
import re
from pathlib import Path

import fitz

from backend.models import ParsedFormulaCandidate, ParsedPdf


FORMULA_PATTERN = re.compile(
    r"(?:[A-Za-z][A-Za-z0-9_]*(?:\([^\)]*\))?|[∂ΣΠηλμρστuvwxyzUVWXYZ][A-Za-z0-9_]*)(?:\s*[-+*/=≤≥<>]\s*[^\n]{3,})"
)


class PdfParserService:
    def parse(self, filename: str, payload: bytes) -> ParsedPdf:
        document = fitz.open(stream=payload, filetype="pdf")
        text_blocks: list[str] = []
        formula_candidates: list[ParsedFormulaCandidate] = []
        warnings: list[str] = []

        for page_index, page in enumerate(document):
            page_text = page.get_text("text") or ""
            cleaned = "\n".join(line.strip() for line in page_text.splitlines() if line.strip())
            if cleaned:
                text_blocks.append(cleaned)

            for match_index, match in enumerate(FORMULA_PATTERN.finditer(cleaned), start=1):
                expression = match.group(0).strip()
                context = extract_context(cleaned, match.start(), match.end())
                formula_candidates.append(
                    ParsedFormulaCandidate(
                        id=f"p{page_index + 1}-t{match_index}",
                        expression=expression,
                        page=page_index + 1,
                        context=context,
                        source="text",
                    )
                )

        title = Path(filename).stem or "Untitled paper"
        full_text = "\n\n".join(text_blocks)

        if not formula_candidates:
            warnings.append("No formula-like text was detected directly from PDF text extraction.")

        return ParsedPdf(
            title=title,
            source_filename=filename,
            page_count=document.page_count,
            full_text=full_text,
            text_blocks=text_blocks,
            formula_candidates=formula_candidates,
            warnings=warnings,
        )


def extract_context(text: str, start: int, end: int, radius: int = 180) -> str:
    snippet = text[max(0, start - radius) : min(len(text), end + radius)]
    return re.sub(r"\s+", " ", snippet).strip()
