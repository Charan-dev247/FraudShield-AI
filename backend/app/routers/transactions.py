from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.model_service import ModelService, get_model_service
from app.models import AuditEvent, Transaction, utcnow
from app.schemas import ReviewIn, TransactionDetail, TransactionPage, TransactionRow

router = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])

SORTS = {
    "newest": Transaction.id.desc(),
    "risk": Transaction.probability.desc(),
    "amount": Transaction.amount.desc(),
}


@router.get("", response_model=TransactionPage)
def list_transactions(
    status: str | None = Query(None, pattern="^(Pending|Confirmed Fraud|Legitimate|Escalated)$"),
    flagged: bool | None = None,
    risk: Literal["Low", "Medium", "High"] | None = None,
    min_probability: float = Query(0, ge=0, le=1),
    tx_id: int | None = Query(None, ge=1),
    sort: Literal["newest", "risk", "amount"] = "risk",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = select(Transaction)
    if status: q = q.where(Transaction.review_status == status)
    if flagged is not None: q = q.where(Transaction.flagged == flagged)
    if risk: q = q.where(Transaction.risk_level == risk)
    if min_probability: q = q.where(Transaction.probability >= min_probability)
    if tx_id: q = q.where(Transaction.id == tx_id)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    items = db.scalars(q.order_by(SORTS[sort], Transaction.id.desc())
                       .offset((page - 1) * page_size).limit(page_size)).all()
    return TransactionPage(items=items, total=total, page=page, page_size=page_size)  # type: ignore[arg-type]


@router.get("/{tx_id}", response_model=TransactionDetail)
def get_transaction(tx_id: int, db: Session = Depends(get_db), svc: ModelService = Depends(get_model_service)):
    tx = db.get(Transaction, tx_id)
    if not tx:
        raise HTTPException(404, "Transaction not found.")
    # Explanations are recomputed with the CURRENT model; note the stored score is from tx.model_version.
    return TransactionDetail(
        **TransactionRow.model_validate(tx).model_dump(),
        features=tx.features, latency_ms=tx.latency_ms,
        explanation=svc.explain(tx.features, top_n=12), history=tx.events)  # type: ignore[arg-type]


@router.patch("/{tx_id}/review", response_model=TransactionRow)
def review(tx_id: int, body: ReviewIn, db: Session = Depends(get_db)):
    tx = db.get(Transaction, tx_id)
    if not tx:
        raise HTTPException(404, "Transaction not found.")
    old = tx.review_status
    tx.review_status, tx.review_note, tx.reviewed_at = body.status, body.note, utcnow()
    tx.events.append(AuditEvent(action="review", detail=f"{old} -> {body.status}" + (f": {body.note}" if body.note else "")))
    db.commit()
    return tx
