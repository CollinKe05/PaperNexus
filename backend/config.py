from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class Settings:
    app_name: str = "PaperNexus"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    mathpix_app_id: str | None = None
    mathpix_app_key: str | None = None
    nougat_enabled: bool = False
    nougat_command: str = "nougat"
    nougat_timeout_sec: int = 1800
    nougat_tmp_dir: str = ".nougat_tmp/runs"
    nougat_cache_dir: str = ".nougat_tmp/cache"
    nougat_nltk_data_dir: str = ".nougat_tmp/nltk_data"
    nougat_max_pages: int = 12
    upload_dir: str = "uploads"
    max_upload_mb: int = 25


settings = Settings(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
    openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    mathpix_app_id=os.getenv("MATHPIX_APP_ID"),
    mathpix_app_key=os.getenv("MATHPIX_APP_KEY"),
    nougat_enabled=os.getenv("NOUGAT_ENABLED", "false").lower() in {"1", "true", "yes", "on"},
    nougat_command=os.getenv("NOUGAT_COMMAND", "nougat"),
    nougat_timeout_sec=int(os.getenv("NOUGAT_TIMEOUT_SEC", "1800")),
    nougat_tmp_dir=os.getenv("NOUGAT_TMP_DIR", ".nougat_tmp/runs"),
    nougat_cache_dir=os.getenv("NOUGAT_CACHE_DIR", ".nougat_tmp/cache"),
    nougat_nltk_data_dir=os.getenv("NOUGAT_NLTK_DATA_DIR", ".nougat_tmp/nltk_data"),
    nougat_max_pages=int(os.getenv("NOUGAT_MAX_PAGES", "12")),
    upload_dir=os.getenv("PAPERNEXUS_UPLOAD_DIR", "uploads"),
    max_upload_mb=int(os.getenv("PAPERNEXUS_MAX_UPLOAD_MB", "25")),
)
