"""Feature engineering + preprocessing, packaged as part of the sklearn Pipeline.

Everything that learns from data (the scaler) lives INSIDE the pipeline, so it is
fitted on training rows only and replayed identically at inference time.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

V_COLUMNS = [f"V{i}" for i in range(1, 29)]
RAW_COLUMNS = ["Time"] + V_COLUMNS + ["Amount"]  # the exact input schema of the dataset
TARGET = "Class"


def add_features(X: pd.DataFrame) -> pd.DataFrame:
    """Stateless transforms (nothing is learned, so no leakage is possible).

    * Time is "seconds since the first transaction". A raw counter cannot generalise to
      future data, so we keep only the time-of-day signal as sin/cos.
    * Amount is heavily right-skewed, so we use log1p(Amount).
    """
    X = X.copy()
    hour = (X["Time"].astype(float) % 86_400) / 3_600
    X["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    X["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    X["log_amount"] = np.log1p(X["Amount"].astype(float).clip(lower=0))
    return X.drop(columns=["Time", "Amount"])


def build_pipeline(classifier: BaseEstimator) -> Pipeline:
    scale = ColumnTransformer(
        [("log_amount", StandardScaler(), ["log_amount"])],
        remainder="passthrough",
        verbose_feature_names_out=False,
    )
    scale.set_output(transform="pandas")
    return Pipeline(
        [
            ("features", FunctionTransformer(add_features).set_output(transform="pandas")),
            ("scale", scale),
            ("clf", classifier),
        ]
    )
