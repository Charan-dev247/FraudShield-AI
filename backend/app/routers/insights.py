from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, Request
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.model_service import ModelService, get_model_service
from app.models import REVIEW_STATUSES, Transaction, utcnow

router = APIRouter(prefix="/api/v1", tags=["insights"])

BINS = [(0, .01), (.01, .05), (.05, .1), (.1, .25), (.25, .5), (.5, .75), (.75, .9), (.9, 1.0001)]


@router.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count(Transaction.id))) or 0
    flagged = db.scalar(select(func.count(Transaction.id)).where(Transaction.flagged.is_(True))) or 0
    by_status = dict(db.execute(select(Transaction.review_status, func.count()).group_by(Transaction.review_status)).all())
    by_risk = dict(db.execute(select(Transaction.risk_level, func.count()).group_by(Transaction.risk_level)).all())
    probs = np.array(db.scalars(select(Transaction.probability).order_by(Transaction.id.desc()).limit(50_000)).all())
    hist = [{"bucket": f"{int(lo*100)}–{min(int(hi*100),100)}%", "count": int(((probs >= lo) & (probs < hi)).sum())} for lo, hi in BINS]
    since = utcnow() - timedelta(days=14)
    daily_rows = db.execute(
        select(func.date(Transaction.created_at), func.count(), func.sum(case((Transaction.flagged.is_(True), 1), else_=0)))
        .where(Transaction.created_at >= since).group_by(func.date(Transaction.created_at))
        .order_by(func.date(Transaction.created_at))).all()
    daily = [{"date": str(d), "total": int(n), "flagged": int(f or 0)} for d, n, f in daily_rows]

    confirmed = by_status.get("Confirmed Fraud", 0)
    legit = by_status.get("Legitimate", 0)
    flagged_confirmed = db.scalar(select(func.count()).select_from(Transaction).where(Transaction.flagged.is_(True), Transaction.review_status == "Confirmed Fraud")) or 0
    flagged_legit = db.scalar(select(func.count()).select_from(Transaction).where(Transaction.flagged.is_(True), Transaction.review_status == "Legitimate")) or 0
    reviewed_flagged = flagged_confirmed + flagged_legit
    return {
        "total": total, "flagged": flagged, "flagged_rate": flagged / total if total else 0.0,
        "avg_probability": float(probs.mean()) if len(probs) else 0.0,
        "by_status": {s: int(by_status.get(s, 0)) for s in REVIEW_STATUSES},
        "by_risk": {r: int(by_risk.get(r, 0)) for r in ("Low", "Medium", "High")},
        "score_histogram": hist, "daily": daily,
        "review_quality": {
            "reviewed_alerts": reviewed_flagged,
            "alert_precision": flagged_confirmed / reviewed_flagged if reviewed_flagged else None,
            "fraud_found_in_unflagged": int(confirmed - flagged_confirmed),
            "marked_legitimate": int(legit),
        },
    }


@router.get("/monitoring")
def monitoring(request: Request, db: Session = Depends(get_db), svc: ModelService = Depends(get_model_service)):
    recent = db.execute(select(Transaction.features, Transaction.latency_ms, Transaction.probability, Transaction.created_at)
                        .order_by(Transaction.id.desc()).limit(2000)).all()
    n = len(recent)
    day_ago, week_ago = utcnow() - timedelta(days=1), utcnow() - timedelta(days=7)
    vol24 = db.scalar(select(func.count()).select_from(Transaction).where(Transaction.created_at >= day_ago)) or 0
    vol7 = db.scalar(select(func.count()).select_from(Transaction).where(Transaction.created_at >= week_ago)) or 0
    lat = np.array([r[1] for r in recent]) if n else np.array([0.0])
    drift, status = [], "insufficient data (need 100+ scored transactions)"
    if n >= 100:
        df = pd.DataFrame([r[0] for r in recent])
        stats = svc.metadata["train_stats"]
        for col, st in stats.items():
            if col == "Time" or col not in df or st["std"] == 0:
                continue  # Time is a running counter; it drifts by construction
            drift.append({"feature": col, "shift_std": float((df[col].mean() - st["mean"]) / st["std"])})
        drift.sort(key=lambda d: abs(d["shift_std"]), reverse=True)
        drift = drift[:8]
        status = "warning" if drift and abs(drift[0]["shift_std"]) > 0.5 else "ok"
    return {
        "model_version": svc.version,
        "volume_24h": vol24, "volume_7d": vol7, "sample_size": n,
        "latency_ms": {"avg": float(lat.mean()), "p95": float(np.percentile(lat, 95))},
        "api_errors_since_restart": getattr(request.app.state, "errors", 0),
        "score_mean": float(np.mean([r[2] for r in recent])) if n else 0.0,
        "drift_status": status,
        "drift_note": "Mean of each input vs its training mean, in training standard deviations. >0.5 raises a warning.",
        "drift": drift,
    }


@router.get("/models")
def models(svc: ModelService = Depends(get_model_service)):
    m = {k: v for k, v in svc.metadata.items() if k not in ("baseline", "train_stats")}
    return m


@router.get("/samples")
def samples():
    path = get_settings().demo_csv
    if not path.exists():
        return []
    df = pd.read_csv(path)
    out = []
    for label, name in ((0, "Typical-looking"), (1, "Fraud-like")):
        for _, r in df[df["Class"] == label].head(2).iterrows():
            out.append({"name": f"{name} #{len(out) % 2 + 1}", "synthetic_label": int(label),
                        "values": {k: float(v) for k, v in r.drop("Class").items()}})
    return out
