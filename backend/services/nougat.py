from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path

from backend.config import settings
from backend.models import ParsedFormulaCandidate


BLOCK_PATTERN = re.compile(r"\$\$(.*?)\$\$", re.S)
ENV_PATTERN = re.compile(r"\\begin\{(equation\*?|align\*?|gather\*?)\}(.*?)\\end\{\1\}", re.S)
INLINE_PATTERN = re.compile(r"\$(.{8,200}?)\$")
BRACKET_BLOCK_PATTERN = re.compile(r"\\\[(.*?)\\\]", re.S)
PAREN_INLINE_PATTERN = re.compile(r"\\\((.{3,200}?)\\\)")


class NougatService:
    @property
    def available(self) -> bool:
        return settings.nougat_enabled and self._resolve_command() is not None

    async def extract_formula_candidates(
        self,
        payload: bytes,
        existing_ids: set[str],
        page_count: int,
    ) -> list[ParsedFormulaCandidate]:
        if not self.available:
            return []

        return await asyncio.to_thread(self._extract_sync, payload, existing_ids, page_count)

    def _extract_sync(self, payload: bytes, existing_ids: set[str], page_count: int) -> list[ParsedFormulaCandidate]:
        tmp_root = self._resolve_path(settings.nougat_tmp_dir)
        tmp_root.mkdir(parents=True, exist_ok=True)
        tmpdir = tmp_root / f"run-{uuid.uuid4().hex}"
        tmpdir.mkdir(parents=True, exist_ok=True)

        try:
            input_pdf = tmpdir / "input.pdf"
            output_dir = tmpdir / "out"
            output_dir.mkdir(parents=True, exist_ok=True)
            input_pdf.write_bytes(payload)

            command_path = self._resolve_command()
            if command_path is None:
                raise RuntimeError("Nougat command is not installed or not reachable.")

            command = [command_path, str(input_pdf), "--out", str(output_dir)]
            env = os.environ.copy()
            cache_root = self._resolve_path(settings.nougat_cache_dir)
            cache_root.mkdir(parents=True, exist_ok=True)
            nltk_data_root = self._resolve_path(settings.nougat_nltk_data_dir)
            nltk_data_root.mkdir(parents=True, exist_ok=True)
            env["TORCH_HOME"] = str(cache_root)
            env["XDG_CACHE_HOME"] = str(cache_root)
            env["HF_HOME"] = str(cache_root / "huggingface")
            env["NLTK_DATA"] = str(nltk_data_root)
            env["NO_ALBUMENTATIONS_UPDATE"] = "1"
            proc = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=settings.nougat_timeout_sec,
                env=env,
            )
            if proc.returncode != 0:
                stderr = (proc.stderr or proc.stdout or "").strip()
                raise RuntimeError(f"Nougat command failed (exit {proc.returncode}): {stderr[:1200]}")

            markdown_files = list(output_dir.rglob("*.mmd"))
            if not markdown_files:
                return []

            markdown_text = "\n\n".join(file.read_text(encoding="utf-8", errors="ignore") for file in markdown_files)
            expressions = extract_latex_blocks(markdown_text)

            candidates: list[ParsedFormulaCandidate] = []
            for idx, expression in enumerate(expressions, start=1):
                formula_id = f"ng-{idx}"
                if formula_id in existing_ids:
                    formula_id = f"ng-{idx}-alt"

                page = infer_page(idx, len(expressions), page_count)
                candidates.append(
                    ParsedFormulaCandidate(
                        id=formula_id,
                        expression=expression,
                        page=page,
                        context="Formula extracted via Nougat markdown conversion.",
                        source="nougat",
                        bbox=None,
                        confidence=0.72,
                    )
                )

            return candidates
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _resolve_command(self) -> str | None:
        command = settings.nougat_command.strip()
        if not command:
            return None

        command_path = Path(command)
        if command_path.exists():
            return str(command_path)

        return shutil.which(command)

    def _resolve_path(self, raw_path: str) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path
        return Path(__file__).resolve().parents[2] / path


def extract_latex_blocks(markdown_text: str) -> list[str]:
    results: list[str] = []

    for match in BLOCK_PATTERN.finditer(markdown_text):
        expr = normalize_formula_text(match.group(1))
        if is_useful_formula(expr):
            results.append(expr)

    for match in ENV_PATTERN.finditer(markdown_text):
        expr = normalize_formula_text(match.group(2))
        if is_useful_formula(expr):
            results.append(expr)

    for match in BRACKET_BLOCK_PATTERN.finditer(markdown_text):
        expr = normalize_formula_text(match.group(1))
        if is_useful_formula(expr):
            results.append(expr)

    for match in INLINE_PATTERN.finditer(markdown_text):
        expr = normalize_formula_text(match.group(1))
        if is_useful_formula(expr):
            results.append(expr)

    for match in PAREN_INLINE_PATTERN.finditer(markdown_text):
        expr = normalize_formula_text(match.group(1))
        if is_useful_formula(expr):
            results.append(expr)

    deduped: list[str] = []
    seen: set[str] = set()
    for expr in results:
        key = re.sub(r"\s+", "", expr).lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(expr)

    return deduped


def normalize_formula_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def is_useful_formula(expression: str) -> bool:
    if len(expression) < 6:
        return False
    operator_count = sum(expression.count(op) for op in ["=", "+", "-", "*", "/", "\\frac", "\\sum", "\\int"])
    symbol_count = len(re.findall(r"[A-Za-zΑ-Ωα-ω]", expression))
    return operator_count >= 1 and symbol_count >= 2


def infer_page(index: int, total: int, page_count: int) -> int:
    if total <= 1:
        return 1
    ratio = (index - 1) / max(total - 1, 1)
    return max(1, min(page_count, int(round(1 + ratio * (page_count - 1)))))
