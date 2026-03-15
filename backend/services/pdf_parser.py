from __future__ import annotations

import re
from pathlib import Path

import fitz

from backend.models import BoundingBox, ParsedFormulaCandidate, ParsedPdf


FORMULA_PATTERN = re.compile(
    r"(?:[A-Za-z][A-Za-z0-9_]*(?:\([^\)]*\))?|[∂ΣΠηλμρστuvwxyzUVWXYZ][A-Za-z0-9_]*)(?:\s*[-+*/=≤≥<>]\s*[^\n]{3,})"
)
SYMBOL_PATTERN = re.compile(r"[A-Za-zΑ-Ωα-ω]+(?:_[A-Za-z0-9()+-]+)?")


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

            page_candidates = self._extract_page_formula_candidates(page, page_index + 1)
            formula_candidates.extend(page_candidates)

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

    def _extract_page_formula_candidates(self, page: fitz.Page, page_number: int) -> list[ParsedFormulaCandidate]:
        raw = page.get_text("dict")
        lines: list[dict] = []

        for block in raw.get("blocks", []):
            if block.get("type") != 0:
                continue

            for line in block.get("lines", []):
                spans = line.get("spans", [])
                text = "".join(span.get("text", "") for span in spans).strip()
                if not text:
                    continue

                bbox = fitz.Rect(line.get("bbox", (0, 0, 0, 0)))
                lines.append(
                    {
                        "text": text,
                        "bbox": bbox,
                        "formula_score": formula_score(text),
                    }
                )

        merged_candidates = merge_formula_lines(lines)
        page_width = max(page.rect.width, 1.0)
        page_height = max(page.rect.height, 1.0)

        candidates: list[ParsedFormulaCandidate] = []
        for idx, candidate in enumerate(merged_candidates, start=1):
            if not looks_like_formula_candidate(candidate["text"]):
                continue
            bbox = normalize_bbox(candidate["bbox"], page_width, page_height)
            candidates.append(
                ParsedFormulaCandidate(
                    id=f"p{page_number}-t{idx}",
                    expression=candidate["text"],
                    page=page_number,
                    context=candidate["context"],
                    source="text",
                    bbox=bbox,
                    confidence=round(candidate["confidence"], 3),
                )
            )

        # If line-based detection was weak, fallback to pattern scan in plain text.
        if not candidates:
            plain_text = page.get_text("text") or ""
            compact = "\n".join(segment.strip() for segment in plain_text.splitlines() if segment.strip())
            for idx, match in enumerate(FORMULA_PATTERN.finditer(compact), start=1):
                expression = match.group(0).strip()
                if len(expression) < 6 or not looks_like_formula_candidate(expression):
                    continue
                candidates.append(
                    ParsedFormulaCandidate(
                        id=f"p{page_number}-rx{idx}",
                        expression=expression,
                        page=page_number,
                        context=extract_context(compact, match.start(), match.end()),
                        source="text",
                        bbox=None,
                        confidence=0.35,
                    )
                )

        return candidates


def merge_formula_lines(lines: list[dict]) -> list[dict]:
    sorted_lines = sorted(lines, key=lambda item: (item["bbox"].y0, item["bbox"].x0))
    results: list[dict] = []

    i = 0
    while i < len(sorted_lines):
        line = sorted_lines[i]
        if line["formula_score"] < 3:
            i += 1
            continue

        group = [line]
        j = i + 1
        while j < len(sorted_lines):
            nxt = sorted_lines[j]
            if nxt["formula_score"] < 2:
                break

            same_column = abs(nxt["bbox"].x0 - group[-1]["bbox"].x0) < 80
            vertical_gap = nxt["bbox"].y0 - group[-1]["bbox"].y1
            if same_column and vertical_gap < 18:
                group.append(nxt)
                j += 1
                continue
            break

        merged_bbox = fitz.Rect(group[0]["bbox"])
        for item in group[1:]:
            merged_bbox |= item["bbox"]

        text = " ".join(item["text"] for item in group)
        confidence = min(0.98, sum(item["formula_score"] for item in group) / (6.5 * len(group)))
        context = " ".join(item["text"] for item in group[:2])
        results.append(
            {
                "text": text,
                "bbox": merged_bbox,
                "context": context,
                "confidence": confidence,
            }
        )
        i = j

    # De-duplicate near-identical formula text.
    deduped: list[dict] = []
    seen: set[str] = set()
    for item in results:
        key = re.sub(r"\s+", "", item["text"]).lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return deduped


def formula_score(text: str) -> float:
    compact = text.strip()
    if len(compact) < 5:
        return 0.0

    operator_count = sum(compact.count(char) for char in "=+-*/^_<>≤≥()[]{}")
    greek_like = len(re.findall(r"[Α-Ωα-ωηλμρστ∂ΣΠ]", compact))
    token_count = len(SYMBOL_PATTERN.findall(compact))
    digit_count = sum(char.isdigit() for char in compact)
    math_ratio = (operator_count + digit_count + greek_like) / max(len(compact), 1)

    score = 0.0
    if operator_count >= 1:
        score += 1.8
    if "=" in compact:
        score += 2.2
    if token_count >= 2:
        score += 1.2
    if greek_like >= 1:
        score += 1.0
    if math_ratio >= 0.20:
        score += 1.0
    if compact.startswith("(") or compact.endswith(")"):
        score += 0.3
    if "\\" in compact:
        score += 1.4
    if re.search(r"[A-Za-z]_[A-Za-z0-9]", compact):
        score += 0.7
    if re.search(r"\b\d+\s*[\)\]]?\s*=", compact):
        score += 0.8

    return score


def looks_like_formula_candidate(text: str) -> bool:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) < 5:
        return False

    operator_count = sum(compact.count(char) for char in "=+-*/^_<>≤≥")
    symbol_count = len(SYMBOL_PATTERN.findall(compact))
    word_count = len(re.findall(r"[A-Za-z]+", compact))
    alpha_count = sum(char.isalpha() for char in compact)
    digit_count = sum(char.isdigit() for char in compact)
    has_latex = "\\" in compact
    has_matrixish = bool(re.search(r"\b[A-Z]\b|\b[a-z]_[A-Za-z0-9]", compact))
    prose_ratio = alpha_count / max(len(compact), 1)

    if has_latex and (operator_count >= 1 or symbol_count >= 1):
        return True
    if "=" in compact and symbol_count >= 2:
        return True
    if operator_count >= 3 and symbol_count >= 2:
        return True
    if re.search(r"\([A-Za-z0-9_, ]+\)\s*to\s*\(", compact):
        return False
    if compact.endswith(".") and operator_count < 2:
        return False
    if word_count > 18 and operator_count < 2:
        return False
    if prose_ratio > 0.72 and digit_count < 3 and operator_count < 2 and not has_matrixish:
        return False

    return operator_count >= 1 and symbol_count >= 2


def normalize_bbox(rect: fitz.Rect, width: float, height: float) -> BoundingBox:
    return BoundingBox(
        x0=clamp(rect.x0 / width, 0.0, 1.0),
        y0=clamp(rect.y0 / height, 0.0, 1.0),
        x1=clamp(rect.x1 / width, 0.0, 1.0),
        y1=clamp(rect.y1 / height, 0.0, 1.0),
    )


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def extract_context(text: str, start: int, end: int, radius: int = 180) -> str:
    snippet = text[max(0, start - radius) : min(len(text), end + radius)]
    return re.sub(r"\s+", " ", snippet).strip()
