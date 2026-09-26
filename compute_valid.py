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
    return data

def main():
    fname = "billing_log_2026-07-27.json"
    raw = load_billing_log(fname)
    print(f"Total records: {len(raw)}")
    valid_records = []
    errors = []
    for idx, item in enumerate(raw):
        try:
            rec = BillingRecord(**item)
            valid_records.append(rec)
        except Exception as e:
            errors.append((idx, str(e)))
            print(f"Record {idx} error: {e}")
    print(f"Valid records: {len(valid_records)}")
    print(f"Errors: {len(errors)}")
    if valid_records:
        recon = compute_reconciliation(valid_records)
        analytics = compute_analytics(valid_records)
        print("\nReconciliation:")
        print(json.dumps(recon, indent=2))
        print("\nAnalytics:")
        print(json.dumps(analytics, indent=2))

if __name__ == "__main__":
    main()
