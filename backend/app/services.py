from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.model_service import ModelService
from app.models import AuditEvent, Transaction
from ml.features import RAW_COLUMNS


def store_scored(db: Session, svc: ModelService, rows: list[dict], source: str,
                 latency_ms: float, probs: list[float], labels: list[int | None] | None = None,
                 created_at: list[datetime] | None = None) -> list[Transaction]:
    """Persist already-scored rows (one DB transaction) and write an audit event for each."""
    out = []
    for i, (row, p) in enumerate(zip(rows, probs)):
        tx = Transaction(
            source=source, amount=float(row["Amount"]),
            features={c: float(row[c]) for c in RAW_COLUMNS},
            probability=p, threshold=svc.threshold, flagged=p >= svc.threshold,
            risk_level=svc.risk_level(p), model_version=svc.version, latency_ms=latency_ms,
            demo_label=labels[i] if labels else None,
        )
        if created_at:
            tx.created_at = created_at[i]
        tx.events.append(AuditEvent(
            action="scored", detail=f"p={p:.4f} thr={svc.threshold:.4f} model={svc.version} via {source}"))
        db.add(tx)
        out.append(tx)
    db.commit()
    return out
