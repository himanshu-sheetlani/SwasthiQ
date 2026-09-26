import json
import os
from app.models.billing import BillingRecord
from app.services.reconciliation import compute_reconciliation
from app.services.analytics import compute_analytics

DATA_DIR = os.path.join(os.path.dirname(__file__), "sample_billing_dataset")

def load_billing_log(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'r') as f:
        data = json.load(f)
    # Validate and convert to BillingRecord objects
    records = []
    for idx, item in enumerate(data):
        try:
            rec = BillingRecord(**item)
            records.append(rec)
        except Exception as e:
            print(f"Error in {filename} record {idx}: {e}")
            raise
    return records

for fname in ["billing_log_2026-07-25.json", "billing_log_2026-07-26.json", "billing_log_2026-07-27.json"]:
    print(f"\n=== {fname} ===")
    records = load_billing_log(fname)
    print(f"Number of records: {len(records)}")
    recon = compute_reconciliation(records)
    print("Reconciliation:")
    print(json.dumps(recon, indent=2))
    analytics = compute_analytics(records)
    print("Analytics:")
    print(json.dumps(analytics, indent=2))
