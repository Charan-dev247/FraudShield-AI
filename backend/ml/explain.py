"""Model-agnostic explanations (work for any sklearn pipeline).

Local:  baseline substitution. Replace one input at a time with its training-median and
        measure how the fraud probability moves. impact > 0 => that value pushed the
        score UP versus a typical transaction. This is a one-feature-at-a-time
        approximation, not Shapley values (see README for the SHAP upgrade path).
Global: permutation importance on the validation set (average-precision drop).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance

from ml.features import RAW_COLUMNS


def local_impacts(pipeline, row: dict, baseline: dict, top_n: int | None = None) -> list[dict]:
    base_row = pd.DataFrame([{c: float(row[c]) for c in RAW_COLUMNS}])
    batch = pd.concat([base_row] * (len(RAW_COLUMNS) + 1), ignore_index=True)
    for k, col in enumerate(RAW_COLUMNS, start=1):
        batch.loc[k, col] = baseline[col]
    probs = pipeline.predict_proba(batch)[:, 1]
    full = probs[0]
    out = [
        {"feature": col, "value": float(base_row.loc[0, col]), "impact": float(full - probs[k])}
        for k, col in enumerate(RAW_COLUMNS, start=1)
    ]
    out.sort(key=lambda d: abs(d["impact"]), reverse=True)
    return out[:top_n] if top_n else out


def global_importance(pipeline, X_val: pd.DataFrame, y_val, seed: int = 42, n_repeats: int = 3) -> list[dict]:
    y_val = np.asarray(y_val)
    pos = np.where(y_val == 1)[0]
    neg = np.where(y_val == 0)[0]
    rng = np.random.default_rng(seed)
    keep = np.concatenate([pos, rng.choice(neg, size=min(len(neg), 6000), replace=False)])
    res = permutation_importance(
        pipeline, X_val.iloc[keep][RAW_COLUMNS], y_val[keep],
        scoring="average_precision", n_repeats=n_repeats, random_state=seed, n_jobs=-1,
    )
    items = [{"feature": c, "importance": float(m), "std": float(s)}
             for c, m, s in zip(RAW_COLUMNS, res.importances_mean, res.importances_std)]
    return sorted(items, key=lambda d: d["importance"], reverse=True)
