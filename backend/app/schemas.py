from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, create_model

from ml.features import V_COLUMNS

ReviewStatus = Literal["Pending", "Confirmed Fraud", "Legitimate", "Escalated"]

# Time, V1..V28, Amount -> a validated request model with a real OpenAPI schema.
_fields = {"Time": (float, Field(ge=0, allow_inf_nan=False, description="Seconds since first transaction")),
           "Amount": (float, Field(ge=0, le=1_000_000, allow_inf_nan=False, description="Transaction amount"))}
_fields.update({v: (float, Field(allow_inf_nan=False)) for v in V_COLUMNS})
TransactionIn = create_model("TransactionIn", **_fields)  # type: ignore[call-overload]


class Impact(BaseModel):
    feature: str
    value: float
    impact: float


class PredictionOut(BaseModel):
    id: int
    probability: float
    threshold: float
    flagged: bool
    risk_level: Literal["Low", "Medium", "High"]
    model_version: str
    latency_ms: float
    explanation: list[Impact] = []


class BatchOut(BaseModel):
    rows: int
    flagged: int
    flagged_rate: float
    model_version: str
    threshold: float
    top: list[PredictionOut]  # highest-risk rows, capped


class TransactionRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    source: str
    amount: float
    probability: float
    threshold: float
    flagged: bool
    risk_level: str
    model_version: str
    review_status: str
    review_note: str | None = None
    reviewed_at: datetime | None = None


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    created_at: datetime
    action: str
    detail: str


class TransactionDetail(TransactionRow):
    features: dict[str, float]
    latency_ms: float
    explanation: list[Impact]
    history: list[AuditOut]


class TransactionPage(BaseModel):
    items: list[TransactionRow]
    total: int
    page: int
    page_size: int


class ReviewIn(BaseModel):
    status: ReviewStatus
    note: str | None = Field(default=None, max_length=500)
