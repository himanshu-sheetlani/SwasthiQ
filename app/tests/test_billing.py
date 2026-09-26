import json
import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# DATA_DIR points to sample_billing_dataset at project root
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sample_billing_dataset")

def load_billing_log(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'r') as f:
        return json.load(f)

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

def test_2026_07_25():
    data = load_billing_log("billing_log_2026-07-25.json")
    resp = client.post("/api/v1/reports", json=data)
    assert resp.status_code == 200
    report = resp.json()["report"]
    # Validate basic totals
    recon = report["reconciliation"]
    assert recon["total_billed"] == 0
    assert recon["total_collected"] == 0
    assert recon["total_refunds"] == 49000  # sum of absolute amounts
    assert recon["outstanding"] == 0
    # Check refunds by mode
    assert recon["total_refunds_by_mode"]["card"] == 24000
    assert recon["total_refunds_by_mode"]["upi"] == 25000
    assert recon["total_refunds_by_mode"]["cash"] == 0

def test_2026_07_26():
    data = load_billing_log("billing_log_2026-07-26.json")
    resp = client.post("/api/v1/reports", json=data)
    assert resp.status_code == 200
    report = resp.json()["report"]
    recon = report["reconciliation"]
    assert recon["total_billed"] == 0
    assert recon["total_collected"] == 0
    assert recon["total_refunds"] == 0
    assert recon["outstanding"] == 0
    # analytics empty
    analytics = report["analytics"]
    assert analytics["revenue_by_hour"] == {}
    assert analytics["peak_business_hour"] == 0
    assert analytics["top_medicines_by_quantity"] == []
    assert analytics["top_medicines_by_revenue"] == []

def test_2026_07_27_missing_payment_mode():
    data = load_billing_log("billing_log_2026-07-27.json")
    resp = client.post("/api/v1/reports", json=data)
    # Expect validation error due to missing payment_mode
    assert resp.status_code == 422
    error = resp.json()
    assert "detail" in error
    # Ensure at least one error mentions missing payment_mode
    found = False
    for err in error["detail"]:
        if err.get("type") == "missing" and "payment_mode" in str(err.get("loc", "")):
            found = True
            break
    assert found, f"Expected missing payment_mode error, got {error}"
