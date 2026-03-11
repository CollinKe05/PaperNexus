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
    upload_dir: str = "uploads"
    max_upload_mb: int = 25


settings = Settings(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
    openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    mathpix_app_id=os.getenv("MATHPIX_APP_ID"),
    mathpix_app_key=os.getenv("MATHPIX_APP_KEY"),
    upload_dir=os.getenv("PAPERNEXUS_UPLOAD_DIR", "uploads"),
    max_upload_mb=int(os.getenv("PAPERNEXUS_MAX_UPLOAD_MB", "25")),
)
