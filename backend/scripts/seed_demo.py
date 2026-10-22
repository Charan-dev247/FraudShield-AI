"""Score the synthetic demo CSV and store it, spread over the last 14 days, so the
dashboard has something to show.   python -m scripts.seed_demo [--reset]
"""
from __future__ import annotations

import argparse
from datetime import timedelta

import numpy as np
import pandas as pd

from app.config import get_settings
from app.db import Base, SessionLocal, engine, init_db
from app.model_service import get_model_service
from app.models import utcnow
from app.services import store_scored
from ml.features import RAW_COLUMNS


def main(reset: bool) -> None:
    if reset:
        Base.metadata.drop_all(bind=engine)
    init_db()
    path = get_settings().demo_csv
    if not path.exists():
        raise SystemExit(f"{path} not found. Run: python -m scripts.make_demo_data --data ../data/creditcard.csv")
    svc = get_model_service()
    df = pd.read_csv(path)
    rows = df[RAW_COLUMNS].to_dict("records")
    probs, ms = svc.score(rows)
    rng = np.random.default_rng(1)
    now = utcnow()
    stamps = [now - timedelta(days=float(rng.uniform(0, 14))) for _ in rows]
    with SessionLocal() as db:
        store_scored(db, svc, rows, "demo", ms, probs, labels=df["Class"].tolist(), created_at=stamps)
    print(f"Seeded {len(rows)} synthetic transactions (model {svc.version}).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="drop and recreate all tables first")
    main(ap.parse_args().reset)
