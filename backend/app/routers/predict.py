from __future__ import annotations

import io

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.model_service import ModelService, get_model_service
from app.schemas import BatchOut, PredictionOut, TransactionIn
from app.services import store_scored
from ml.features import RAW_COLUMNS

router = APIRouter(prefix="/api/v1", tags=["prediction"])


def _out(tx, svc: ModelService, row: dict | None = None) -> PredictionOut:
    return PredictionOut(
        id=tx.id, probability=tx.probability, threshold=tx.threshold, flagged=tx.flagged,
        risk_level=tx.risk_level, model_version=tx.model_version, latency_ms=round(tx.latency_ms, 3),
        explanation=svc.explain(row) if row else [])


@router.post("/predict", response_model=PredictionOut)
def predict(body: TransactionIn, db: Session = Depends(get_db), svc: ModelService = Depends(get_model_service)):  # type: ignore[valid-type]
    row = body.model_dump()
    probs, ms = svc.score([row])
    tx = store_scored(db, svc, [row], "api", ms, probs)[0]
    return _out(tx, svc, row)


@router.post("/predict/batch", response_model=BatchOut)
async def predict_batch(file: UploadFile = File(...), db: Session = Depends(get_db),
                        svc: ModelService = Depends(get_model_service)):
    cfg = get_settings()
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(415, "Upload a .csv file.")
    raw = await file.read(cfg.max_upload_bytes + 1)
    if len(raw) > cfg.max_upload_bytes:
        raise HTTPException(413, f"File too large (limit {cfg.max_upload_bytes // 1024 // 1024} MB).")
    try:
        df = pd.read_csv(io.BytesIO(raw), nrows=cfg.max_batch_rows + 1)
    except Exception:
        raise HTTPException(400, "Could not parse the file as CSV.")
    missing = [c for c in RAW_COLUMNS if c not in df.columns]
    if missing:
        raise HTTPException(422, f"Missing required columns: {', '.join(missing)}")
    if len(df) == 0:
        raise HTTPException(422, "The CSV has no rows.")
    if len(df) > cfg.max_batch_rows:
        raise HTTPException(413, f"Too many rows (limit {cfg.max_batch_rows}).")
    num = df[RAW_COLUMNS].apply(pd.to_numeric, errors="coerce")
    bad = num.isnull().any(axis=1) | (num["Amount"] < 0) | (num["Time"] < 0)
    if bad.any():
        first = int(bad.idxmax()) + 2  # +2: header row + 1-based
        raise HTTPException(422, f"{int(bad.sum())} row(s) have missing, non-numeric or negative values (first bad row: line {first}).")

    rows = num.to_dict("records")
    probs, ms = svc.score(rows)
    txs = store_scored(db, svc, rows, "batch", ms, probs)
    flagged = sum(t.flagged for t in txs)
    top = sorted(txs, key=lambda t: t.probability, reverse=True)[:20]
    return BatchOut(rows=len(txs), flagged=flagged, flagged_rate=flagged / len(txs),
                    model_version=svc.version, threshold=svc.threshold,
                    top=[_out(t, svc) for t in top])
