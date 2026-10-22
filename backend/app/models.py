from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

REVIEW_STATUSES = ("Pending", "Confirmed Fraud", "Legitimate", "Escalated")


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    source: Mapped[str] = mapped_column(String(32), default="api")  # api | batch | demo
    amount: Mapped[float] = mapped_column(Float)
    features: Mapped[dict] = mapped_column(JSON)
    probability: Mapped[float] = mapped_column(Float, index=True)
    threshold: Mapped[float] = mapped_column(Float)
    flagged: Mapped[bool] = mapped_column(Boolean, index=True)
    risk_level: Mapped[str] = mapped_column(String(16), index=True)
    model_version: Mapped[str] = mapped_column(String(64))
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    review_status: Mapped[str] = mapped_column(String(24), default="Pending", index=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Only set for demo/synthetic data where the answer is known. Real labels come from review_status.
    demo_label: Mapped[int | None] = mapped_column(Integer, nullable=True)

    events: Mapped[list["AuditEvent"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan", order_by="AuditEvent.id")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    action: Mapped[str] = mapped_column(String(32))
    detail: Mapped[str] = mapped_column(Text, default="")

    transaction: Mapped[Transaction] = relationship(back_populates="events")
