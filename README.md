# FraudShield AI

An explainable credit card fraud scoring and case-review app: a leakage-free scikit-learn pipeline, a FastAPI service, and a React dashboard where analysts score transactions, inspect why they were flagged, and record decisions.

> **Scope.** The data is the public ULB/Kaggle credit card dataset (European cardholders, Sept 2013) whose features `V1`–`V28` are anonymised PCA components. This is a portfolio project, not a validated bank fraud system, and explanations are about model inputs, never about merchants, locations or behaviour.

<!-- Add screenshots to /Images (dashboard.png, check.png, investigations.png, models.png), then uncomment:
![Dashboard](Images/dashboard.png)
-->

## What it does

| Page | Purpose |
|---|---|
| Dashboard | Volume, flagged rate, score distribution, 14-day trend, review queue, precision of reviewed alerts |
| Check a transaction | Score one transaction (form or JSON) or a CSV batch; shows probability, risk band, alert threshold and the inputs that drove the score |
| Investigations | Filter and page through cases, open one, record **Confirm fraud / Legitimate / Escalate** with a note; every action is stored in an audit history |
| Model and monitoring | Model comparison with confidence intervals, PR curves, permutation importance, **threshold simulator** with a cost calculator, volume/latency/error counts and input-drift check |

## Results (honest version)

Chronological split by `Time`: train 199,364 rows (384 fraud) · validation 42,721 (56 fraud) · test 42,722 (**52 fraud**).
Models are ranked on **validation** PR-AUC; each model's alert threshold is chosen on validation (maximise recall subject to precision ≥ 0.80); the test set is used once, for reporting.

| Model | Val PR-AUC | Test PR-AUC | Precision | Recall | False alarms | Missed fraud |
|---|---|---|---|---|---|---|
| Logistic regression | 0.817 | 0.692 | 0.97 | 0.67 | 1 | 17 |
| **Random forest (deployed)** | **0.878** | **0.778** | 0.76 | 0.75 | 12 | 13 |
| Gradient boosting | 0.849 | 0.742 | 0.78 | 0.73 | 11 | 14 |

95% bootstrap intervals for the deployed model on test: PR-AUC 0.67–0.87, precision 0.65–0.88, recall 0.63–0.85.

How to read this:
- With only 52 test frauds the intervals are wide and **overlap across models**. The ranking is suggestive, not proven.
- The precision floor was met on validation (≥ 0.80) but test precision came out at 0.76, a reminder that a threshold tuned on ~56 frauds is itself uncertain.
- These numbers are lower than the original notebook's random-split result (RF F1 ≈ 0.87) because a time-ordered split is a harder and more realistic test: models are used on future transactions.
- Logistic regression's threshold lands near 1.0 because `class_weight="balanced"` pushes its probabilities towards the extremes (uncalibrated). Its false-alarm count is low only at that extreme threshold.

## Architecture

```
React + Vite + TypeScript + Tailwind (Recharts)
        │  JSON over HTTP  (/api/v1/…)
        ▼
FastAPI ── Pydantic validation ── routers: predict · transactions · insights
   │                │
   ▼                ▼
sklearn Pipeline    SQLAlchemy ── SQLite (local) / PostgreSQL (docker, prod)
(preprocess +       tables: transactions, audit_events
 classifier)
+ metadata.json (threshold, metrics, importance, baselines)
```

Key ML decisions (all in `backend/ml/`):
- **No leakage.** The only learned preprocessing step (scaling log-amount) lives inside the `Pipeline`, so it is fitted on training rows only and replayed identically at inference. `tests/test_ml.py` checks this.
- **Time features.** `Time` is a running counter that cannot generalise to the future, so only time-of-day (sin/cos) is used; `Amount` is `log1p`-scaled.
- **Metrics for imbalance.** PR-AUC, precision, recall, F1, ROC-AUC, false positives/negatives and single-row latency; accuracy is not used.
- **Explanations.** Local: replace each input with its training median and measure the change in fraud probability ("baseline substitution"). Global: permutation importance on validation. These are model-agnostic approximations, **not Shapley values**.

## Run it locally (Windows PowerShell)

Put `creditcard.csv` in `data/` (it is git-ignored), then:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
pip install -r requirements-dev.txt

python -m ml.train --data ..\data\creditcard.csv   # ~6 min on one core; add --fast for a quick check
python -m scripts.seed_demo                        # optional: loads 660 synthetic demo transactions
uvicorn app.main:app --reload                      # API docs: http://localhost:8000/docs
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev                                         # http://localhost:5173
```

`backend/artifacts/` (a 2.7 MB model + metadata) and `backend/data/demo_transactions.csv` (synthetic) are committed so the app runs and deploys without the 150 MB dataset. Re-run training to regenerate them.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Service and model status |
| POST | `/api/v1/predict` | Score one transaction (`Time`, `V1`–`V28`, `Amount`) with explanation |
| POST | `/api/v1/predict/batch` | Score a CSV (≤ 5 MB, ≤ 5,000 rows, strict column/number validation) |
| GET | `/api/v1/transactions` | Filter by status, risk, flagged, id; sort; paginate |
| GET | `/api/v1/transactions/{id}` | Detail, explanation, audit history |
| PATCH | `/api/v1/transactions/{id}/review` | Set status + note (writes an audit event) |
| GET | `/api/v1/metrics` | Dashboard aggregates |
| GET | `/api/v1/models` | Model comparison, threshold table, importance, split report |
| GET | `/api/v1/monitoring` | Volume, latency, errors, input drift |
| GET | `/api/v1/samples` | Synthetic example inputs for the demo form |

```bash
curl -X POST localhost:8000/api/v1/predict -H "Content-Type: application/json" -d @transaction.json
```

## Tests and CI

```powershell
cd backend; pytest -q          # 13 tests; train a tiny model on synthetic data, no real dataset needed
cd frontend; npm run build     # type-check + production build
```

GitHub Actions (`.github/workflows/ci.yml`) runs both on every push and pull request.

## Docker

```powershell
docker compose up --build      # Postgres + API + nginx-served frontend → http://localhost:8080
```

## Deploying

Suggested: frontend on Vercel (root `frontend`, env `VITE_API_URL=https://<your-api>`), API on Render using `backend/Dockerfile`, managed PostgreSQL (e.g. Neon) via `DATABASE_URL`, and `CORS_ORIGINS=https://<your-frontend>`. Check each provider's current free-tier limits and sleep behaviour first. SQLite is not suitable on hosts with ephemeral disks. Use HTTPS and keep secrets out of git.

## What changed from the original notebook

| Problem in the notebook | Fix |
|---|---|
| `Amount` scaled on the full dataset before splitting (leakage) | Scaling inside a `Pipeline`, fitted on training data only |
| `Scaled_Time` created after `X_train/X_test` were built, so it never reached the models | Time handled by the pipeline's feature step |
| Data path `../Data/…` did not match the `data/` folder | Corrected |
| Random split, threshold fixed at 0.5, README claimed RF "better" although ROC-AUC favoured LR | Chronological split, validation-chosen threshold, PR-AUC, confidence intervals |
| README listed a `notebooks/` folder that did not exist | Corrected structure below |

The notebook is kept for EDA; its modelling cells were fixed and their stale outputs cleared (Restart & Run All to refresh).

## Limitations

- Anonymised PCA features: no human-readable reasons ("unusual location") can or should be produced.
- 52 test frauds: metrics are uncertain; see the intervals.
- Explanations are one-feature-at-a-time approximations and can show ~0 impact when the score is already near 0.
- Demo data are synthetic resamples with jitter and over-represent fraud (~9%), so the drift panel showing a warning on seeded data is expected.
- Not implemented: authentication/roles, Alembic migrations (tables are created at startup), rate limiting beyond upload caps, true SHAP values, LLM summaries.

## Project structure

```
backend/   app/ (FastAPI) · ml/ (train, features, evaluate, explain) · scripts/ · tests/ · artifacts/ · data/
frontend/  src/pages · src/components · src/lib
NoteBook/  fraud_detection.ipynb (EDA + corrected baseline)
Images/    screenshots
```

**Author:** Suluru Charan, B.Tech CSE (AI), IIITDM Kancheepuram
