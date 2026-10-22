from __future__ import annotations

import numpy as np
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score


def confusion_at(y, p, thr: float) -> dict:
    y, pred = np.asarray(y).astype(int), (np.asarray(p) >= thr).astype(int)
    tp = int(((pred == 1) & (y == 1)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    tn = int(((pred == 0) & (y == 0)).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "threshold": float(thr), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": precision, "recall": recall, "f1": f1,
        "flagged_rate": (tp + fp) / len(y),
    }


def summarize(y, p, thr: float) -> dict:
    y = np.asarray(y)
    out = confusion_at(y, p, thr)
    out["average_precision"] = float(average_precision_score(y, p)) if y.sum() else 0.0
    out["roc_auc"] = float(roc_auc_score(y, p)) if 0 < y.sum() < len(y) else 0.0
    return out


def select_threshold(y, p, min_precision: float = 0.80) -> tuple[float, str]:
    """Stated objective: catch as much fraud as possible while keeping at least
    `min_precision` of alerts genuine (so analysts are not flooded with false alarms).
    Falls back to the max-F1 threshold if no threshold reaches the precision floor.
    """
    prec, rec, thr = precision_recall_curve(y, p)
    prec, rec = prec[:-1], rec[:-1]
    ok = prec >= min_precision
    if ok.any():
        best_recall = rec[ok].max()
        cand = np.where(ok & (rec >= best_recall - 1e-12))[0]
        return float(thr[cand].max()), f"max recall with precision >= {min_precision:.2f} (validation)"
    f1 = 2 * prec * rec / np.clip(prec + rec, 1e-12, None)
    return float(thr[int(f1.argmax())]), "max F1 (validation); precision floor was not reachable"


def bootstrap_ci(y, p, thr: float, n: int = 300, seed: int = 42) -> dict:
    """95% bootstrap intervals. With only ~100 frauds in a test set these are WIDE; report them."""
    rng = np.random.default_rng(seed)
    y, p = np.asarray(y), np.asarray(p)
    aps, precs, recs = [], [], []
    for _ in range(n):
        idx = rng.integers(0, len(y), len(y))
        if y[idx].sum() == 0:
            continue
        aps.append(average_precision_score(y[idx], p[idx]))
        c = confusion_at(y[idx], p[idx], thr)
        precs.append(c["precision"]); recs.append(c["recall"])
    q = lambda a: [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]
    return {"average_precision": q(aps), "precision": q(precs), "recall": q(recs)}


def threshold_table(y, p, step: float = 0.01) -> list[dict]:
    return [confusion_at(y, p, t) for t in np.round(np.arange(step, 1.0, step), 4)]


def pr_points(y, p, max_points: int = 150) -> list[dict]:
    prec, rec, _ = precision_recall_curve(y, p)
    idx = np.unique(np.linspace(0, len(prec) - 1, min(max_points, len(prec))).astype(int))
    return [{"recall": float(rec[i]), "precision": float(prec[i])} for i in idx]
