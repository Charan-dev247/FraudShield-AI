"""Tests never need the real dataset: they train a tiny model on synthetic data first."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.features import RAW_COLUMNS, TARGET

_TMP = Path(tempfile.mkdtemp(prefix="fraudshield-test-"))
os.environ["MODEL_DIR"] = str(_TMP / "artifacts")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP / 'test.db'}"
os.environ["DEMO_CSV"] = str(_TMP / "demo.csv")


def make_synthetic(n: int = 6000, n_fraud: int = 150, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(rng.normal(size=(n, 28)), columns=[f"V{i}" for i in range(1, 29)])
    df["Time"] = np.sort(rng.uniform(0, 172_000, n))
    df["Amount"] = rng.gamma(2.0, 40.0, n)
    y = np.zeros(n, dtype=int)
    y[rng.choice(n, n_fraud, replace=False)] = 1
    df.loc[y == 1, ["V3", "V10", "V14"]] -= 3.0  # a learnable fraud signature
    df[TARGET] = y
    return df[RAW_COLUMNS + [TARGET]]


@pytest.fixture(scope="session")
def synthetic_csv() -> Path:
    path = _TMP / "synthetic.csv"
    make_synthetic().to_csv(path, index=False)
    make_synthetic(120, 20, seed=1).to_csv(_TMP / "demo.csv", index=False)
    return path


@pytest.fixture(scope="session")
def metadata(synthetic_csv):
    from ml.train import run
    return run(str(synthetic_csv), os.environ["MODEL_DIR"], min_precision=0.7, fast=True)


@pytest.fixture(scope="session")
def client(metadata):
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def fraud_row():
    r = make_synthetic(50, 5, seed=3)
    return r[r[TARGET] == 1].iloc[0][RAW_COLUMNS].to_dict()


@pytest.fixture()
def normal_row():
    r = make_synthetic(50, 5, seed=3)
    return r[r[TARGET] == 0].iloc[0][RAW_COLUMNS].to_dict()
