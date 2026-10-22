from __future__ import annotations

import json
import time
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from app.config import get_settings
from ml.explain import local_impacts
from ml.features import RAW_COLUMNS


class ModelNotLoaded(RuntimeError):
    pass


class ModelService:
    """Loads the saved sklearn pipeline + metadata once and scores transactions.

    The pipeline contains the preprocessing, so inference is guaranteed to apply the
    exact transformations that were fitted on the training split.
    """

    def __init__(self, model_dir: Path):
        self.pipeline = joblib.load(model_dir / "model.joblib")
        self.metadata: dict = json.loads((model_dir / "metadata.json").read_text())
        self.threshold: float = float(self.metadata["threshold"])
        self.version: str = self.metadata["model_version"]
        self.baseline: dict = self.metadata["baseline"]

    def score(self, rows: list[dict]) -> tuple[list[float], float]:
        """Returns (probabilities, latency in ms per row)."""
        df = pd.DataFrame(rows)[RAW_COLUMNS].astype(float)
        t = time.perf_counter()
        probs = self.pipeline.predict_proba(df)[:, 1]
        per_row_ms = (time.perf_counter() - t) * 1000 / max(len(df), 1)
        return [float(p) for p in probs], per_row_ms

    def risk_level(self, p: float) -> str:
        """Low < half the threshold <= Medium < threshold <= High (High == flagged)."""
        if p >= self.threshold:
            return "High"
        return "Medium" if p >= self.threshold * 0.5 else "Low"

    def explain(self, row: dict, top_n: int = 10) -> list[dict]:
        return local_impacts(self.pipeline, row, self.baseline, top_n)


@lru_cache
def _load(model_dir: str) -> ModelService:
    return ModelService(Path(model_dir))


def get_model_service() -> ModelService:
    d = get_settings().model_dir
    if not (d / "model.joblib").exists() or not (d / "metadata.json").exists():
        raise ModelNotLoaded(
            "No trained model found. Run `python -m ml.train --data ../data/creditcard.csv` in /backend first.")
    return _load(str(d))
