from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .infrai_client import InfraiClient, InfraiError
from .usage_ledger import ActivityBatch, MeteringResult, UsageLedger


class UsageSnapshot(BaseModel):
    metering: MeteringResult
    account_timeseries: dict[str, Any]


def create_app(client: InfraiClient | None = None) -> FastAPI:
    app = FastAPI(title="Nonprofit customer usage meter")
    ledger = UsageLedger()

    @app.post("/meter", response_model=UsageSnapshot)
    def meter_batch(batch: ActivityBatch) -> UsageSnapshot:
        infrai = client or InfraiClient.from_env()
        try:
            timeseries = infrai.usage_timeseries()
        except InfraiError as exc:
            status = exc.status_code if 400 <= exc.status_code < 500 else 502
            raise HTTPException(status_code=status, detail=exc.details) from exc
        return UsageSnapshot(metering=ledger.meter(batch), account_timeseries=timeseries)

    return app


app = create_app()
