from __future__ import annotations

from collections import defaultdict
from enum import StrEnum

from pydantic import BaseModel, Field


class ActivityType(StrEnum):
    DONOR_RECEIPT = "donor_receipt"
    VOLUNTEER_REMINDER = "volunteer_reminder"
    CAMPAIGN_REPORT = "campaign_report"


class ActivityRecord(BaseModel):
    customer_id: str = Field(min_length=1)
    activity: ActivityType
    quantity: int = Field(gt=0)


class ActivityBatch(BaseModel):
    batch_id: str = Field(min_length=1)
    records: list[ActivityRecord] = Field(min_length=1)


class CustomerUsage(BaseModel):
    customer_id: str
    donor_receipts: int = 0
    volunteer_reminders: int = 0
    campaign_reports: int = 0
    billable_units: int


class MeteringResult(BaseModel):
    batch_id: str
    duplicate: bool
    customers: list[CustomerUsage]


class UsageLedger:
    """Aggregate customer activity with deterministic weights and batch deduplication."""

    _weights = {
        ActivityType.DONOR_RECEIPT: 1,
        ActivityType.VOLUNTEER_REMINDER: 1,
        ActivityType.CAMPAIGN_REPORT: 5,
    }

    def __init__(self) -> None:
        self._results: dict[str, MeteringResult] = {}

    def meter(self, batch: ActivityBatch) -> MeteringResult:
        previous = self._results.get(batch.batch_id)
        if previous:
            return previous.model_copy(update={"duplicate": True})

        totals: dict[str, dict[ActivityType, int]] = defaultdict(lambda: defaultdict(int))
        for record in batch.records:
            totals[record.customer_id][record.activity] += record.quantity

        customers = []
        for customer_id, activities in sorted(totals.items()):
            units = sum(activities[kind] * weight for kind, weight in self._weights.items())
            customers.append(
                CustomerUsage(
                    customer_id=customer_id,
                    donor_receipts=activities[ActivityType.DONOR_RECEIPT],
                    volunteer_reminders=activities[ActivityType.VOLUNTEER_REMINDER],
                    campaign_reports=activities[ActivityType.CAMPAIGN_REPORT],
                    billable_units=units,
                )
            )

        result = MeteringResult(batch_id=batch.batch_id, duplicate=False, customers=customers)
        self._results[batch.batch_id] = result
        return result
