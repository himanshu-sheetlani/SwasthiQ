from typing import List
from app.models.billing import BillingRecord

class InMemoryBillingRepository:
    def __init__(self):
        self._records: List[BillingRecord] = []

    def add_record(self, record: BillingRecord) -> None:
        self._records.append(record)

    def add_records(self, records: List[BillingRecord]) -> None:
        self._records.extend(records)

    def get_all_records(self) -> List[BillingRecord]:
        return self._records.copy()

    def clear(self) -> None:
        self._records.clear()

    def count(self) -> int:
        return len(self._records)
