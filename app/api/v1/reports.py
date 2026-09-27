from fastapi import APIRouter, HTTPException
from typing import List
from app.models.billing import BillingRecord
from pydantic import ValidationError
from app.services.repository import InMemoryBillingRepository
from app.services.reconciliation import compute_reconciliation
from app.services.analytics import compute_analytics
from app.services.llm_narrative import generate_llm_narrative

router = APIRouter()
repository = InMemoryBillingRepository()

@router.post("/reports")
async def generate_report(records_input: List[dict]):
    """
    Accepts a billing log (list of dicts) and returns deterministic report with LLM narrative.
    Validation errors are collected per record; valid records are processed.
    """
    valid_records: List[BillingRecord] = []
    validation_errors = []

    for idx, item in enumerate(records_input):
        try:
            record = BillingRecord(**item)
            valid_records.append(record)
        except ValidationError as e:
            validation_errors.append({
                "record_index": idx,
                "errors": e.errors()
            })
        except Exception as e:
            validation_errors.append({
                "record_index": idx,
                "error": str(e)
            })

    # Store valid records
    repository.clear()
    repository.add_records(valid_records)

    stored = repository.get_all_records()
    # Compute reconciliation and analytics
    reconciliation = compute_reconciliation(stored)
    analytics = compute_analytics(stored)

    # Compute additional counts for narrative
    visit_count = len(valid_records)
    refund_visit_count = sum(1 for r in valid_records if r.is_refund)

    # Determine a date string for the narrative (use first record's date if available)
    date_str = "Today"
    if valid_records:
        # Use the date from the first record (format DD MMM)
        first_date = valid_records[0].timestamp
        date_str = first_date.strftime("%d %b")  # e.g., "27 Jul"

    # Generate LLM narrative
    deterministic_report = {
        "reconciliation": reconciliation,
        "analytics": analytics,
        "visit_count": visit_count,
        "refund_visit_count": refund_visit_count,
        "date_str": date_str
    }
    llm_narrative_response = generate_llm_narrative(deterministic_report)

    response = {
        "report": {
            "reconciliation": reconciliation,
            "analytics": analytics,
        },
        "llm_narrative": llm_narrative_response.to_dict()
    }
    if validation_errors:
        response["validation_errors"] = validation_errors

    return response
