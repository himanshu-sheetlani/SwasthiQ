#!/usr/bin/env python3
"""
Demonstration script showing the complete flow:
billing log -> validation -> deterministic report -> LLM narrative -> structured output
"""

import json
import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.models.billing import BillingRecord
from app.services.repository import InMemoryBillingRepository
from app.services.reconciliation import compute_reconciliation
from app.services.analytics import compute_analytics
from app.services.llm_narrative import generate_llm_narrative

def load_billing_log(filename):
    """Load a billing log from the sample_billing_dataset directory."""
    data_dir = os.path.join(os.path.dirname(__file__), "frontend", "public", "sample_billing_dataset")
    path = os.path.join(data_dir, filename)
    with open(path, 'r') as f:
        return json.load(f)

def process_billing_log(filename):
    """Process a billing log and return the deterministic report and LLM narrative."""
    print(f"\n=== Processing {filename} ===")

    # Load the data
    raw_data = load_billing_log(filename)
    print(f"Loaded {len(raw_data)} records")

    # Validate and convert to BillingRecord objects
    valid_records = []
    validation_errors = []

    for idx, item in enumerate(raw_data):
        try:
            record = BillingRecord(**item)
            valid_records.append(record)
        except Exception as e:
            validation_errors.append({
                "record_index": idx,
                "error": str(e)
            })
            print(f"  Record {idx} validation error: {e}")

    print(f"Valid records: {len(valid_records)}")
    print(f"Validation errors: {len(validation_errors)}")

    # Store valid records
    repository = InMemoryBillingRepository()
    repository.clear()
    repository.add_records(valid_records)

    stored = repository.get_all_records()

    # Compute deterministic report
    reconciliation = compute_reconciliation(stored)
    analytics = compute_analytics(stored)

    deterministic_report = {
        "reconciliation": reconciliation,
        "analytics": analytics
    }

    # Generate LLM narrative (will use fallback since no LLM configured)
    llm_narrative_response = generate_llm_narrative(deterministic_report)

    return {
        "deterministic_report": deterministic_report,
        "llm_narrative": llm_narrative_response.to_dict(),
        "validation_errors": validation_errors
    }

def main():
    """Run the demonstration for all sample billing logs."""
    print("LLM Narrative Layer Demonstration")
    print("=" * 50)

    # Process each sample file
    for filename in [
        "billing_log_2026-07-25.json",  # Refund day
        "billing_log_2026-07-26.json",  # Empty day
        "billing_log_2026-07-27.json"   # Normal day with one invalid record
    ]:
        result = process_billing_log(filename)

        # Display key information
        print(f"\n--- Deterministic Report ---")
        recon = result["deterministic_report"]["reconciliation"]
        print(f"Total Billed: {recon['total_billed']} paise ({recon['total_billed']/100:.2f} INR)")
        print(f"Total Collected: {recon['total_collected']} paise ({recon['total_collected']/100:.2f} INR)")
        print(f"Total Refunds: {recon['total_refunds']} paise ({recon['total_refunds']/100:.2f} INR)")
        print(f"Outstanding: {recon['outstanding']} paise ({recon['outstanding']/100:.2f} INR)")

        analytics = result["deterministic_report"]["analytics"]
        print(f"Peak Business Hour: {analytics['peak_business_hour']}:00")

        print(f"\n--- LLM Generated Narrative ---")
        # Handle potential encoding issues in console by replacing rupee symbol
        narrative = result["llm_narrative"]["narrative"]
        # Replace ₹ with Rs. for better console compatibility
        narrative_clean = narrative.replace('₹', 'Rs.')
        print(narrative_clean)

        print(f"\n--- Traced Figures ---")
        for fig in result["llm_narrative"]["traced_figures"]:
            # Handle potential encoding issues in console by replacing rupee symbol
            display_value_clean = fig['display_value'].replace('₹', 'Rs.')
            print(f"  {fig['report_field']}: {display_value_clean} (value: {fig['value']})")

        if result["validation_errors"]:
            print(f"\n--- Validation Errors ---")
            for err in result["validation_errors"]:
                print(f"  Record {err['record_index']}: {err['error']}")

        print("\n" + "-" * 50)

if __name__ == "__main__":
    main()