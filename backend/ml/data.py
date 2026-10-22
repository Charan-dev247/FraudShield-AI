from __future__ import annotations

from pathlib import Path

import pandas as pd

from ml.features import RAW_COLUMNS, TARGET


def load_dataset(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in RAW_COLUMNS + [TARGET] if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing columns: {missing}")
    if df[RAW_COLUMNS + [TARGET]].isnull().any().any():
        raise ValueError("Dataset contains null values")
    return df


def time_split(df: pd.DataFrame, train_frac: float = 0.70, val_frac: float = 0.15):
    """Chronological split: train = earliest, validation = next, test = latest.

    Fraud models are deployed on FUTURE transactions, so a random split is optimistic.
    """
    df = df.sort_values("Time", kind="stable").reset_index(drop=True)
    n = len(df)
    i, j = int(n * train_frac), int(n * (train_frac + val_frac))
    return df.iloc[:i], df.iloc[i:j], df.iloc[j:]


def split_report(train: pd.DataFrame, val: pd.DataFrame, test: pd.DataFrame) -> dict:
    return {
        name: {"rows": int(len(d)), "fraud": int(d[TARGET].sum()), "fraud_rate": float(d[TARGET].mean())}
        for name, d in (("train", train), ("validation", val), ("test", test))
    }
