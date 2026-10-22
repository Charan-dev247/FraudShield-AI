import io

import pandas as pd

from ml.features import RAW_COLUMNS


def test_health(client):
    r = client.get("/health").json()
    assert r["status"] == "ok" and r["model_loaded"] is True


def test_predict_single_fraud_scores_higher_than_normal(client, fraud_row, normal_row):
    f = client.post("/api/v1/predict", json=fraud_row)
    n = client.post("/api/v1/predict", json=normal_row)
    assert f.status_code == 200 and n.status_code == 200
    f, n = f.json(), n.json()
    assert f["probability"] > n["probability"]
    assert 0 <= f["probability"] <= 1 and f["risk_level"] in ("Low", "Medium", "High")
    assert len(f["explanation"]) == 10 and f["model_version"]


def test_predict_validation_errors(client, normal_row):
    bad = dict(normal_row); bad["Amount"] = -5
    assert client.post("/api/v1/predict", json=bad).status_code == 422
    missing = dict(normal_row); del missing["V7"]
    assert client.post("/api/v1/predict", json=missing).status_code == 422


def test_batch_ok_and_stored(client, fraud_row, normal_row):
    csv = pd.DataFrame([fraud_row, normal_row, normal_row]).to_csv(index=False)
    r = client.post("/api/v1/predict/batch", files={"file": ("t.csv", csv, "text/csv")})
    assert r.status_code == 200
    body = r.json()
    assert body["rows"] == 3 and len(body["top"]) == 3
    assert body["top"][0]["probability"] >= body["top"][-1]["probability"]


def test_batch_rejects_bad_files(client, normal_row):
    ok = pd.DataFrame([normal_row])
    r = client.post("/api/v1/predict/batch", files={"file": ("t.txt", "x", "text/plain")})
    assert r.status_code == 415
    r = client.post("/api/v1/predict/batch", files={"file": ("t.csv", ok.drop(columns=["V1"]).to_csv(index=False), "text/csv")})
    assert r.status_code == 422 and "V1" in r.json()["detail"]
    broken = ok.copy(); broken.loc[0, "Amount"] = None
    r = client.post("/api/v1/predict/batch", files={"file": ("t.csv", broken.to_csv(index=False), "text/csv")})
    assert r.status_code == 422


def test_transactions_list_detail_and_review(client, fraud_row):
    created = client.post("/api/v1/predict", json=fraud_row).json()
    page = client.get("/api/v1/transactions", params={"tx_id": created["id"]}).json()
    assert page["total"] == 1 and page["items"][0]["review_status"] == "Pending"

    detail = client.get(f"/api/v1/transactions/{created['id']}").json()
    assert detail["history"][0]["action"] == "scored" and len(detail["explanation"]) == 12

    r = client.patch(f"/api/v1/transactions/{created['id']}/review", json={"status": "Confirmed Fraud", "note": "card reported stolen"})
    assert r.status_code == 200 and r.json()["review_status"] == "Confirmed Fraud"
    detail = client.get(f"/api/v1/transactions/{created['id']}").json()
    assert [h["action"] for h in detail["history"]] == ["scored", "review"]  # persisted audit trail

    assert client.patch(f"/api/v1/transactions/{created['id']}/review", json={"status": "Nope"}).status_code == 422
    assert client.get("/api/v1/transactions/999999").status_code == 404


def test_metrics_models_monitoring_samples(client, normal_row):
    for _ in range(3):
        client.post("/api/v1/predict", json=normal_row)
    m = client.get("/api/v1/metrics").json()
    assert m["total"] >= 3 and len(m["score_histogram"]) == 8 and set(m["by_status"]) == {"Pending", "Confirmed Fraud", "Legitimate", "Escalated"}
    models = client.get("/api/v1/models").json()
    assert len(models["comparison"]) == 3 and len(models["threshold_table"]) > 50 and "baseline" not in models
    mon = client.get("/api/v1/monitoring").json()
    assert mon["latency_ms"]["p95"] >= 0 and "drift_status" in mon
    s = client.get("/api/v1/samples").json()
    assert len(s) == 4 and set(RAW_COLUMNS) == set(s[0]["values"])
