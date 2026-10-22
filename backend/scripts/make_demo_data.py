"""Create SYNTHETIC demo transactions (backend/data/demo_transactions.csv).

Rows are resampled from the training split and jittered with Gaussian noise, so no real
cardholder record is published. Run once locally; the small output file is safe to commit.

    python -m scripts.make_demo_data --data ../data/creditcard.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from ml.data import load_dataset, time_split
from ml.features import RAW_COLUMNS, TARGET


def main(data: str, out: str, n_normal: int, n_fraud: int, seed: int) -> None:
    rng = np.random.default_rng(seed)
    train, _, _ = time_split(load_dataset(data))
    parts = []
    for label, n in ((0, n_normal), (1, n_fraud)):
        pool = train[train[TARGET] == label]
        s = pool.sample(n, replace=n > len(pool), random_state=seed).copy()
        for c in RAW_COLUMNS:
            if c == "Time":
                continue
            s[c] = s[c] + rng.normal(0, 0.1 * pool[c].std(), len(s))
        s["Amount"] = s["Amount"].clip(lower=0).round(2)
        parts.append(s)
    demo = pd.concat(parts).sample(frac=1, random_state=seed).reset_index(drop=True)
    demo["Time"] = np.sort(rng.uniform(0, 172_000, len(demo))).round(0)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    demo[RAW_COLUMNS + [TARGET]].to_csv(out, index=False)
    print(f"Wrote {len(demo)} synthetic rows ({int(demo[TARGET].sum())} fraud-like) to {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data/creditcard.csv")
    ap.add_argument("--out", default="data/demo_transactions.csv")
    ap.add_argument("--normal", type=int, default=600)
    ap.add_argument("--fraud", type=int, default=60)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    main(a.data, a.out, a.normal, a.fraud, a.seed)
