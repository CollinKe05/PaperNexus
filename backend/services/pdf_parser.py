from __future__ import annotations

import re
from pathlib import Path

import fitz

from backend.models import BoundingBox, ParsedFormulaCandidate, ParsedPdf


FORMULA_PATTERN = re.compile(r"(?:[A-Za-z][A-Za-z0-9_]*(?:\([^\)]*\))?)(?:\s*[-+*/=<>]\s*[^\n]{3,})")
SYMBOL_PATTERN = re.compile(r"[A-Za-z]+(?:_[A-Za-z0-9()+-]+)?")
PROSE_MARKERS = {
    "where",
    "which",
    "that",
    "this",
    "these",
    "those",
    "therefore",
    "because",
    "while",
    "although",
    "however",
    "suppose",
    "denotes",
    "represents",
    "defined",
    "definition",
    "theorem",
    "proof",
    "figure",
    "table",
    "algorithm",
    "appendix",
}


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
                lines.append({"text": text, "bbox": bbox, "formula_score": formula_score(text)})

        merged_candidates = merge_formula_lines(lines)
        page_width = max(page.rect.width, 1.0)
        page_height = max(page.rect.height, 1.0)

        candidates: list[ParsedFormulaCandidate] = []
        candidate_index = 0
        for candidate in merged_candidates:
            for expression in split_formula_candidate(candidate["text"]):
                trimmed = trim_formula_candidate(expression)
                if not trimmed or not looks_like_formula_candidate(trimmed):
                    continue
                candidate_index += 1
                candidates.append(
                    ParsedFormulaCandidate(
                        id=f"p{page_number}-t{candidate_index}",
                        expression=trimmed,
                        page=page_number,
                        context=candidate["context"],
                        source="text",
                        bbox=normalize_bbox(candidate["bbox"], page_width, page_height),
                        confidence=round(candidate["confidence"], 3),
                    )
                )

        if not candidates:
            plain_text = page.get_text("text") or ""
            compact = "\n".join(segment.strip() for segment in plain_text.splitlines() if segment.strip())
            regex_index = 0
            for match in FORMULA_PATTERN.finditer(compact):
                expression = trim_formula_candidate(match.group(0).strip())
                if len(expression) < 6 or not looks_like_formula_candidate(expression):
                    continue
                regex_index += 1
                candidates.append(
                    ParsedFormulaCandidate(
                        id=f"p{page_number}-rx{regex_index}",
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

            same_column = abs(nxt["bbox"].x0 - group[-1]["bbox"].x0) < 48
            vertical_gap = nxt["bbox"].y0 - group[-1]["bbox"].y1
            if should_merge_formula_lines(group[-1], nxt, same_column, vertical_gap):
                group.append(nxt)
                j += 1
                continue
            break

        merged_bbox = fitz.Rect(group[0]["bbox"])
        for item in group[1:]:
            merged_bbox |= item["bbox"]

        results.append(
            {
                "text": " ".join(item["text"] for item in group),
                "bbox": merged_bbox,
                "context": " ".join(item["text"] for item in group[:2]),
                "confidence": min(0.98, sum(item["formula_score"] for item in group) / (6.5 * len(group))),
            }
        )
        i = j

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

    operator_count = sum(compact.count(char) for char in "=+-*/^_<>()[ ]{}")
    token_count = len(SYMBOL_PATTERN.findall(compact))
    digit_count = sum(char.isdigit() for char in compact)
    math_ratio = (operator_count + digit_count) / max(len(compact), 1)

    score = 0.0
    if operator_count >= 1:
        score += 1.8
    if "=" in compact:
        score += 2.2
    if token_count >= 2:
        score += 1.2
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
    if prose_marker_count(compact) >= 2:
        score -= 1.8
    if len(compact) > 180:
        score -= 0.8
    return score


def looks_like_formula_candidate(text: str) -> bool:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) < 5:
        return False

    operator_count = sum(compact.count(char) for char in "=+-*/^_<>")
    symbol_count = len(SYMBOL_PATTERN.findall(compact))
    word_count = len(re.findall(r"[A-Za-z]+", compact))
    alpha_count = sum(char.isalpha() for char in compact)
    digit_count = sum(char.isdigit() for char in compact)
    has_latex = "\\" in compact
    has_matrixish = bool(re.search(r"\b[A-Z]\b|\b[a-z]_[A-Za-z0-9]", compact))
    prose_ratio = alpha_count / max(len(compact), 1)
    prose_hits = prose_marker_count(compact)

    if has_latex and (operator_count >= 1 or symbol_count >= 1):
        return prose_hits < 3 or "=" in compact or "\\frac" in compact or "\\sum" in compact
    if "=" in compact and symbol_count >= 2:
        return not (prose_hits >= 4 and operator_count <= 2)
    if operator_count >= 3 and symbol_count >= 2:
        return prose_hits < 4
    if re.search(r"\([A-Za-z0-9_, ]+\)\s*to\s*\(", compact):
        return False
    if prose_hits >= 3 and operator_count < 3:
        return False
    if compact.endswith(".") and operator_count < 2:
        return False
    if len(compact) > 220 and operator_count < 4:
        return False
    if word_count > 18 and operator_count < 2:
        return False
    if prose_ratio > 0.72 and digit_count < 3 and operator_count < 2 and not has_matrixish:
        return False

    return operator_count >= 1 and symbol_count >= 2


def should_merge_formula_lines(previous: dict, current: dict, same_column: bool, vertical_gap: float) -> bool:
    if not same_column:
        return False
    if vertical_gap < 0 or vertical_gap > 12:
        return False
    if looks_like_standalone_formula_line(previous["text"]) and looks_like_standalone_formula_line(current["text"]):
        return False
    if starts_explanatory_tail(current["text"]):
        return False
    return True


def looks_like_standalone_formula_line(text: str) -> bool:
    compact = re.sub(r"\s+", " ", text).strip()
    operator_count = sum(compact.count(char) for char in "=+-*/^_<>")
    return operator_count >= 1 and prose_marker_count(compact) == 0 and len(compact) <= 120


def starts_explanatory_tail(text: str) -> bool:
    compact = re.sub(r"\s+", " ", text).strip().lower()
    return any(compact.startswith(prefix) for prefix in ("where ", "with ", "for ", "if ", "subject to", "such that"))


def split_formula_candidate(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text).strip()
    if compact.count("=") >= 2:
        pieces = re.split(r"(?<=[A-Za-z0-9\)\]}])\s+(?=[A-Za-z\\][A-Za-z0-9_\\]{0,20}\s*=)", compact)
        cleaned = [piece.strip() for piece in pieces if piece.strip()]
        if len(cleaned) > 1:
            return cleaned
    return [compact]


def trim_formula_candidate(text: str) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    compact = re.split(r"\b(?:where|with|for|if|subject to|such that)\b", compact, maxsplit=1, flags=re.I)[0].strip()
    return compact.rstrip(".,;:")


def prose_marker_count(text: str) -> int:
    words = [word.lower() for word in re.findall(r"[A-Za-z]+", text)]
    return sum(word in PROSE_MARKERS for word in words)


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
