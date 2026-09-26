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
    recon = report["reconciliation"]
    assert recon["total_billed"] == 0
    assert recon["total_collected"] == 0
    assert recon["total_refunds"] == 49000  # sum of absolute amounts
    assert recon["outstanding"] == 0
    assert recon["total_refunds_by_mode"]["card"] == 24000
    assert recon["total_refunds_by_mode"]["upi"] == 25000
    assert recon["total_refunds_by_mode"]["cash"] == 0
    assert "validation_errors" not in report

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
    analytics = report["analytics"]
    assert analytics["revenue_by_hour"] == {}
    assert analytics["peak_business_hour"] == 0
    assert analytics["top_medicines_by_quantity"] == []
    assert analytics["top_medicines_by_revenue"] == []
    assert "validation_errors" not in report

def test_2026_07_27_missing_payment_mode():
    data = load_billing_log("billing_log_2026-07-27.json")
    resp = client.post("/api/v1/reports", json=data)
    assert resp.status_code == 200
    resp_json = resp.json()
    assert "report" in resp_json
    assert "validation_errors" in resp_json
    errors = resp_json["validation_errors"]
    assert len(errors) == 1
    err = errors[0]
    assert err["record_index"] == 18
    # Ensure error mentions missing payment_mode
    found = False
    for suberr in err["errors"]:
        if suberr.get("type") == "missing" and "payment_mode" in str(suberr.get("loc", "")):
            found = True
            break
    assert found, f"Expected missing payment_mode error, got {err}"

    # Validate the report matches expected values from valid records
    report = resp_json["report"]
    recon = report["reconciliation"]
    # Expected values from compute_valid.py
    assert recon["total_billed"] == 319000
    assert recon["total_collected"] == 317200
    assert recon["total_refunds"] == 0
    assert recon["outstanding"] == 1800
    assert recon["total_billed_by_mode"]["cash"] == 127500
    assert recon["total_billed_by_mode"]["card"] == 83500
    assert recon["total_billed_by_mode"]["upi"] == 108000
    assert recon["total_collected_by_mode"]["cash"] == 127000
    assert recon["total_collected_by_mode"]["card"] == 82700
    assert recon["total_collected_by_mode"]["upi"] == 107500

    analytics = report["analytics"]
    # Revenue by hour
    expected_revenue_by_hour = {
        "9": 9000,
        "10": 57000,
        "11": 33500,
        "12": 9500,
        "13": 76000,
        "14": 3500,
        "15": 41500,
        "16": 61000,
        "17": 22000,
        "18": 6000
    }
    assert analytics["revenue_by_hour"] == expected_revenue_by_hour
    assert analytics["peak_business_hour"] == 13
    # Top medicines by quantity
    expected_top_qty = [
        {"drug_name": "OMEPRAZOLE", "quantity": 18},
        {"drug_name": "METFORMIN", "quantity": 14},
        {"drug_name": "PARACETAMOL", "quantity": 11},
        {"drug_name": "AMOXICILLIN", "quantity": 11},
        {"drug_name": "ATORVASTATIN", "quantity": 10},
        {"drug_name": "PARACETMOL", "quantity": 2},
    ]
    assert analytics["top_medicines_by_quantity"] == expected_top_qty
    # Top medicines by revenue
    expected_top_rev = [
        {"drug_name": "ATORVASTATIN", "revenue_paise": 119357},
        {"drug_name": "OMEPRAZOLE", "revenue_paise": 68735},
        {"drug_name": "AMOXICILLIN", "revenue_paise": 64586},
        {"drug_name": "METFORMIN", "revenue_paise": 41409},
        {"drug_name": "PARACETAMOL", "revenue_paise": 21413},
        {"drug_name": "PARACETMOL", "revenue_paise": 3500},
    ]
    assert analytics["top_medicines_by_revenue"] == expected_top_rev
