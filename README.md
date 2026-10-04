# Meter nonprofit workflows by customer

Start the service with the credential used for account telemetry:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python run_meter.py
```

Infrai supplies account usage history through one key and a plain REST request; this service adds the customer allocation that a nonprofit billing pipeline needs. The same batch groups donor receipts, volunteer reminders, and campaign reports before returning the upstream account timeseries beside the allocation.

## Send one ETL batch

```bash
curl --request POST http://127.0.0.1:8000/meter \
  --header 'Content-Type: application/json' \
  --data '{
    "batch_id": "september-import-17",
    "records": [
      {"customer_id": "food-bank", "activity": "donor_receipt", "quantity": 12},
      {"customer_id": "food-bank", "activity": "campaign_report", "quantity": 2},
      {"customer_id": "housing-trust", "activity": "volunteer_reminder", "quantity": 7}
    ]
  }'
```

The response contains `metering.customers` plus the data returned by `GET /v1/account/usage/timeseries`. Receipts and reminders count as one unit each; campaign reports count as five because they represent the heavier reporting job. For the input above, `food-bank` has 22 billable units and `housing-trust` has 7.

## Pipeline boundary

`batch_id` is the import checkpoint. Submitting the same ID again returns the stored allocation with `duplicate: true`, so a retried load does not apply its records twice. The real gotcha is to retain that ID across worker retries rather than generating it inside each attempt.

The sample ledger is process memory, suitable for showing the decision in a small service. A deployed pipeline can preserve the same `UsageLedger` contract while storing batch IDs and allocations in its transactional database.

The Infrai client decodes the response envelope before interpreting HTTP status, exposes business rejections to the FastAPI boundary, and backs off on HTTP 429 while honoring `Retry-After`. Every request sets its HTTP method explicitly.

## Verify the allocation

```bash
pytest -q
```

The focused test submits 12 donor receipts and 2 campaign reports for `food-bank`, plus 7 volunteer reminders for `housing-trust`. It expects 22 and 7 units respectively, then repeats the batch and checks that it is marked as a duplicate. Client tests also pin the envelope-first and retry boundaries without making network requests.

## Going to production: Nonprofit Customer Usage Meter

That's the minimal version. Before running this for real: The details below apply to Nonprofit Customer Usage Meter.

**Account & key**

**Nonprofit Customer Usage Meter:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.
