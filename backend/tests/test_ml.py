import numpy as np
import pandas as pd

from ml.data import time_split
from ml.evaluate import confusion_at, select_threshold
from ml.features import RAW_COLUMNS, build_pipeline
from sklearn.linear_model import LogisticRegression
from tests.conftest import make_synthetic


def test_time_split_is_chronological_and_disjoint():
    df = make_synthetic()
    tr, va, te = time_split(df)
    assert tr["Time"].max() <= va["Time"].min() <= va["Time"].max() <= te["Time"].min()
    assert len(tr) + len(va) + len(te) == len(df)


def test_scaler_is_fitted_on_training_data_only():
    """The leakage bug from the notebook: preprocessing must not see test rows."""
    df = make_synthetic()
    tr, _, te = time_split(df)
    te = te.copy(); te["Amount"] = te["Amount"] * 1000  # absurd test-time shift
    pipe = build_pipeline(LogisticRegression(max_iter=500)).fit(tr[RAW_COLUMNS], tr["Class"])
    scaler = pipe.named_steps["scale"].named_transformers_["log_amount"]
    expected = np.log1p(tr["Amount"]).mean()
    assert abs(scaler.mean_[0] - expected) < 1e-9  # learned from train only, unaffected by `te`
    pipe.predict_proba(te[RAW_COLUMNS])  # and inference still works on shifted data


def test_pipeline_accepts_raw_schema_only():
    df = make_synthetic(500, 20)
    pipe = build_pipeline(LogisticRegression(max_iter=500)).fit(df[RAW_COLUMNS], df["Class"])
    p = pipe.predict_proba(df[RAW_COLUMNS].head(3))[:, 1]
    assert p.shape == (3,) and ((p >= 0) & (p <= 1)).all()


def test_confusion_counts():
    y = np.array([1, 1, 0, 0, 0]); p = np.array([0.9, 0.2, 0.8, 0.1, 0.0])
    c = confusion_at(y, p, 0.5)
    assert (c["tp"], c["fp"], c["fn"], c["tn"]) == (1, 1, 1, 2)


def test_threshold_respects_precision_floor():
    rng = np.random.default_rng(0)
    y = np.r_[np.ones(50), np.zeros(950)].astype(int)
    p = np.r_[rng.beta(5, 2, 50), rng.beta(1, 8, 950)]
    thr, rule = select_threshold(y, p, 0.8)
    assert confusion_at(y, p, thr)["precision"] >= 0.8
    assert "precision" in rule


def test_training_metadata_has_honest_reporting(metadata):
    assert set(metadata["splits"]) == {"train", "validation", "test"}
    assert all(s["fraud"] > 0 for s in metadata["splits"].values())
    assert len(metadata["comparison"]) == 3
    best = max(metadata["comparison"], key=lambda r: r["validation"]["average_precision"])
    assert metadata["model_name"] == best["name"]  # selected on VALIDATION, not test
    assert "average_precision" in metadata["comparison"][0]["test_ci_95"]
