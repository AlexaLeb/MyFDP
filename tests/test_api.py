"""Интеграционные тесты REST API (очередь замокана в conftest)."""
import numpy as np
import pandas as pd


def _csv(n_days: int = 65, n_sku: int = 1) -> str:
    np.random.seed(0)
    rows = []
    for sku in range(n_sku):
        for d in pd.date_range("2024-01-01", periods=n_days):
            rows.append({
                "date": d.date().isoformat(),
                "sku_id": f"S{sku}",
                "sales": int(max(0, np.random.poisson(3))),
            })
    return pd.DataFrame(rows).to_csv(index=False)


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json() == {"status": "healthy"}


def test_signup_and_duplicate(client):
    r = client.post("/api/users/signup", json={"email": "a@a.ru", "password": "pw"})
    assert r.status_code == 201
    r2 = client.post("/api/users/signup", json={"email": "a@a.ru", "password": "pw"})
    assert r2.status_code == 409


def test_upload_requires_auth(client):
    r = client.post("/api/v1/upload", files={"file": ("h.csv", _csv(), "text/csv")},
                    data={"horizon": "7"})
    assert r.status_code in (401, 403)


def test_upload_happy_path_creates_job(auth_client):
    r = auth_client.post("/api/v1/upload",
                         files={"file": ("h.csv", _csv(), "text/csv")},
                         data={"horizon": "7"})
    assert r.status_code == 202
    body = r.json()
    assert body["job_id"] and body["status"] == "pending"
    assert body["sku_count"] == 1 and body["row_count"] == 65


def test_upload_short_history_400(auth_client):
    r = auth_client.post("/api/v1/upload",
                         files={"file": ("s.csv", _csv(n_days=30), "text/csv")},
                         data={"horizon": "7"})
    assert r.status_code == 400


def test_upload_bad_horizon_400(auth_client):
    r = auth_client.post("/api/v1/upload",
                         files={"file": ("h.csv", _csv(), "text/csv")},
                         data={"horizon": "5"})
    assert r.status_code == 400


def test_upload_charges_credits(auth_client):
    before = auth_client.get("/api/balance/").json()["balance"]
    auth_client.post("/api/v1/upload",
                     files={"file": ("h.csv", _csv(), "text/csv")},
                     data={"horizon": "7"})
    after = auth_client.get("/api/balance/").json()["balance"]
    assert before - after == 50


def test_insufficient_credits_402(auth_client):
    # тратим бонус (200) за 4 прогноза, пятый → 402
    for _ in range(4):
        auth_client.post("/api/v1/upload",
                         files={"file": ("h.csv", _csv(), "text/csv")},
                         data={"horizon": "7"})
    r = auth_client.post("/api/v1/upload",
                         files={"file": ("h.csv", _csv(), "text/csv")},
                         data={"horizon": "7"})
    assert r.status_code == 402


def test_job_status_and_results_empty_until_done(auth_client):
    r = auth_client.post("/api/v1/upload",
                         files={"file": ("h.csv", _csv(), "text/csv")},
                         data={"horizon": "7"})
    job_id = r.json()["job_id"]
    jr = auth_client.get(f"/api/v1/jobs/{job_id}")
    assert jr.status_code == 200 and jr.json()["status"] == "pending"
    rr = auth_client.get(f"/api/v1/results/{job_id}")
    assert rr.status_code == 200 and rr.json()["count"] == 0


def test_foreign_job_forbidden(auth_client, client):
    # job создан первым пользователем
    r = auth_client.post("/api/v1/upload",
                         files={"file": ("h.csv", _csv(), "text/csv")},
                         data={"horizon": "7"})
    job_id = r.json()["job_id"]
    # второй пользователь
    client.post("/api/users/signup", json={"email": "b@b.ru", "password": "pw"})
    client.post("/login/token", data={"username": "b@b.ru", "password": "pw"})
    assert client.get(f"/api/v1/jobs/{job_id}").status_code == 403
