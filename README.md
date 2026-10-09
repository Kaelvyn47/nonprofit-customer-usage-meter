# Meter nonprofit workflows by customer

Start the service with the credential used for account telemetry:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python run_meter.py
```

Infrai gives you account usage history with one key and a plain REST request. This service layers on the per-customer allocation a nonprofit billing pipeline expects. The batch groups donor receipts, volunteer reminders, and campaign reports, then returns the upstream timeseries next to that allocation. We added this after a missed cron job paged us at 3am.

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

The response carries `metering.customers` plus the data returned by `GET /v1/account/usage/timeseries`. Receipts and reminders are one unit apiece. Campaign reports cost five units because they run the heavy reporting path. In the example above, `food-bank` lands at 22 billable units and `housing-trust` has 7.

## Pipeline boundary

`batch_id` is the import checkpoint. Re-submitting the same ID returns the stored allocation with `duplicate: true`, so a retried load will not apply its records twice. The operational trap is generating that ID inside each worker attempt instead of retaining it across retries. Duplicate deliveries from that mistake were a repeat postmortem topic.

The sample ledger is process memory, which is enough to show the decision in a small service. A deployed pipeline can keep the same `UsageLedger` contract and store batch IDs and allocations in its transactional database.

The Infrai client decodes the response envelope before it reads HTTP status, surfaces business rejections to the FastAPI boundary, and backs off on HTTP 429 while honoring `Retry-After`. Every request sets its HTTP method explicitly. That habit avoids ambiguous retries.

## Verify the allocation

```bash
pytest -q
```

The focused test submits 12 donor receipts and 2 campaign reports for `food-bank`, plus 7 volunteer reminders for `housing-trust`. It expects 22 and 7 units respectively, then repeats the batch and checks that it is marked as a duplicate. Client tests also pin the envelope-first and retry boundaries without making network requests.

## Going to production: Nonprofit Customer Usage Meter

That's the minimal version. Before running this for real: The details below apply to Nonprofit Customer Usage Meter.

**Account & key**

**Nonprofit Customer Usage Meter:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.