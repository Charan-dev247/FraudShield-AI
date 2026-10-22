
"""Train, compare and save the fraud model.

    python -m ml.train --data ../data/creditcard.csv

Protocol (nothing here peeks at the test set until the very end):
  1. chronological split: train 70% / validation 15% / test 15%
  2. fit each candidate on TRAIN only (scaler lives inside the pipeline)
  3. rank candidates by validation average precision (PR-AUC)
  4. pick each model's alert threshold on VALIDATION (precision floor, max recall)
  5. report test metrics once, with bootstrap intervals
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from ml.data import load_dataset, split_report, time_split
from ml.evaluate import bootstrap_ci, pr_points, select_threshold, summarize, threshold_table
from ml.explain import global_importance
from ml.features import RAW_COLUMNS, TARGET, build_pipeline


def candidates(seed: int, fast: bool = False) -> dict:
    n_trees = 60 if fast else 300
    return {
        "logistic_regression": LogisticRegression(
            max_iter=2000, solver="liblinear", class_weight="balanced", random_state=seed),
        "random_forest": RandomForestClassifier(
            n_estimators=n_trees, min_samples_leaf=2, max_depth=18, class_weight="balanced_subsample",
            n_jobs=-1, random_state=seed),
        "gradient_boosting": HistGradientBoostingClassifier(
            max_iter=100 if fast else 300, learning_rate=0.08, max_leaf_nodes=15,
            l2_regularization=1.0, class_weight="balanced", random_state=seed),
    }


def latency_ms(pipeline, X: pd.DataFrame, n: int = 100) -> dict:
    """Latency of scoring ONE transaction (what the API does), in milliseconds."""
    times = []
    for i in range(n):
        row = X.iloc[[i % len(X)]]
        t = time.perf_counter()
        pipeline.predict_proba(row)
        times.append((time.perf_counter() - t) * 1000)
    return {"p50": float(np.percentile(times, 50)), "p95": float(np.percentile(times, 95))}


def run(data_path: str, out_dir: str, min_precision: float = 0.80, seed: int = 42, fast: bool = False) -> dict:
    df = load_dataset(data_path)
    train, val, test = time_split(df)
    splits = split_report(train, val, test)
    print("Split report:", json.dumps(splits, indent=2))

    X_tr, y_tr = train[RAW_COLUMNS], train[TARGET].values
    X_va, y_va = val[RAW_COLUMNS], val[TARGET].values
    X_te, y_te = test[RAW_COLUMNS], test[TARGET].values

    fitted, results = {}, []
    for name, clf in candidates(seed, fast).items():
        t0 = time.perf_counter()

        # Fit on TRAIN only.
        pipe = build_pipeline(clf).fit(X_tr, y_tr)

        # Select threshold using VALIDATION predictions.
        p_va = pipe.predict_proba(X_va)[:, 1]
        thr, thr_rule = select_threshold(y_va, p_va, min_precision)

        # Test predictions are for final evaluation/reporting.
        p_te = pipe.predict_proba(X_te)[:, 1]

        row = {
            "name": name,
            "fit_seconds": round(time.perf_counter() - t0, 1),
            "threshold": thr,
            "threshold_rule": thr_rule,
            "validation": summarize(y_va, p_va, thr),
            "test": summarize(y_te, p_te, thr),
            "test_ci_95": bootstrap_ci(y_te, p_te, thr, seed=seed),
            "latency_ms": latency_ms(pipe, X_te),
            "pr_curve": pr_points(y_te, p_te),
        }

        # Retain both sets of predictions so the threshold simulator
        # can use validation data rather than test data.
        fitted[name] = (pipe, p_te, p_va)
        results.append(row)

        print(f"{name:20s} val AP={row['validation']['average_precision']:.3f}  "
              f"test AP={row['test']['average_precision']:.3f}  thr={thr:.3f}  "
              f"P={row['test']['precision']:.3f} R={row['test']['recall']:.3f}")

    # Select the deployed model using validation average precision.
    best = max(results, key=lambda r: r["validation"]["average_precision"])
    best_name = best["name"]
    pipe, p_te, p_va_best = fitted[best_name]

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    model_path = out / "model.joblib"
    joblib.dump(pipe, model_path, compress=3)
    digest = hashlib.sha256(model_path.read_bytes()).hexdigest()[:8]
    version = f"{best_name}-{datetime.now(timezone.utc):%Y%m%d}-{digest}"

    importance = global_importance(pipe, val, y_va, seed=seed)
    metadata = {
        "model_version": version,
        "model_name": best_name,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "selection_metric": "validation average precision (PR-AUC)",
        "threshold": best["threshold"],
        "threshold_rule": best["threshold_rule"],
        "min_precision": min_precision,
        "splits": splits,
        "split_strategy": "chronological 70/15/15 by Time",
        "input_columns": RAW_COLUMNS,
        "baseline": {c: float(train[c].median()) for c in RAW_COLUMNS},
        "train_stats": {
            c: {"mean": float(train[c].mean()), "std": float(train[c].std())}
            for c in RAW_COLUMNS
        },
        "comparison": results,

        # Use VALIDATION labels and predictions for threshold simulation.
        "threshold_table": threshold_table(y_va, p_va_best),

        "feature_importance": importance,
        "dataset_note": "Kaggle/ULB credit card fraud (European cardholders, Sept 2013). "
                        "V1-V28 are anonymised PCA components; this is not a validated bank system.",
    }
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2))
    print(f"\nSaved {model_path} ({model_path.stat().st_size/1e6:.1f} MB) and metadata.json")
    print(f"Selected: {version}")
    return metadata


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data/creditcard.csv")
    ap.add_argument("--out-dir", default="artifacts")
    ap.add_argument("--min-precision", type=float, default=0.80)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--fast", action="store_true", help="smaller models, for quick checks")
    a = ap.parse_args()
    run(a.data, a.out_dir, a.min_precision, a.seed, a.fast)
