from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings:
    def __init__(self) -> None:
        self.model_dir = Path(os.getenv("MODEL_DIR", BACKEND_DIR / "artifacts"))
        self.database_url = os.getenv("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'fraudshield.db'}")
        # Render/Heroku style URLs start with postgres:// ; SQLAlchemy wants postgresql://
        if self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace("postgres://", "postgresql://", 1)
        self.cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
        self.demo_csv = Path(os.getenv("DEMO_CSV", BACKEND_DIR / "data" / "demo_transactions.csv"))
        self.max_upload_bytes = int(os.getenv("MAX_UPLOAD_BYTES", 5 * 1024 * 1024))
        self.max_batch_rows = int(os.getenv("MAX_BATCH_ROWS", 5000))


@lru_cache
def get_settings() -> Settings:
    return Settings()
