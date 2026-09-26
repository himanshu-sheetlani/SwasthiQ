from fastapi import APIRouter, HTTPException
from typing import List
from app.models.billing import BillingRecord
from pydantic import ValidationError
from app.services.repository import InMemoryBillingRepository
from app.services.reconciliation import compute_reconciliation
from app.services.analytics import compute_analytics

router = APIRouter()
repository = InMemoryBillingRepository()

@router.post("/reports")
async def generate_report(records_input: List[dict]):
    """
    Accepts a billing log (list of dicts) and returns deterministic report.
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

    response = {
        "report": {
            "reconciliation": reconciliation,
            "analytics": analytics,
        }
    }
    if validation_errors:
        response["validation_errors"] = validation_errors

    return response
