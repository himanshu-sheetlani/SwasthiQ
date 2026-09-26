import json
import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

DATA_DIR = os.path.join(os.path.dirname(__file__), "sample_billing_dataset")

def load_billing_log(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'r') as f:
        return json.load(f)

print("Loading 2026-07-25")
data = load_billing_log("billing_log_2026-07-25.json")
print(f"Loaded {len(data)} records")
resp = client.post("/api/v1/reports", json=data)
print("Status:", resp.status_code)
print("Response:", resp.text)
