from nonprofit_meter.usage_ledger import ActivityBatch, ActivityRecord, ActivityType, UsageLedger


def test_campaign_reports_receive_the_reporting_weight_and_batches_deduplicate() -> None:
    ledger = UsageLedger()
    batch = ActivityBatch(
        batch_id="september-import-17",
        records=[
            ActivityRecord(customer_id="food-bank", activity=ActivityType.DONOR_RECEIPT, quantity=12),
            ActivityRecord(customer_id="food-bank", activity=ActivityType.CAMPAIGN_REPORT, quantity=2),
            ActivityRecord(customer_id="housing-trust", activity=ActivityType.VOLUNTEER_REMINDER, quantity=7),
        ],
    )

    first = ledger.meter(batch)
    repeated = ledger.meter(batch)

    assert [(row.customer_id, row.billable_units) for row in first.customers] == [
        ("food-bank", 22),
        ("housing-trust", 7),
    ]
    assert first.duplicate is False
    assert repeated.duplicate is True
    assert repeated.customers == first.customers
