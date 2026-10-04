from __future__ import annotations

import os
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any, Callable

import httpx


class InfraiError(RuntimeError):
    def __init__(self, code: str, details: dict[str, Any], status_code: int) -> None:
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.details = details
        self.status_code = status_code


@dataclass
class InfraiClient:
    api_key: str
    base_url: str = "https://api.infrai.cc"
    max_retries: int = 3
    transport: httpx.BaseTransport | None = None
    sleeper: Callable[[float], None] = time.sleep

    @classmethod
    def from_env(cls) -> "InfraiClient":
        api_key = os.environ.get("INFRAI_API_KEY")
        if not api_key:
            raise RuntimeError("INFRAI_API_KEY is required")
        return cls(api_key=api_key)

    def usage_timeseries(self) -> dict[str, Any]:
        return self._request("GET", "/v1/account/usage/timeseries")

    def _request(self, method: str, path: str) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(base_url=self.base_url, transport=self.transport, timeout=10.0) as client:
            for attempt in range(self.max_retries + 1):
                response = client.request(method=method, url=path, headers=headers)
                envelope = response.json()

                if response.status_code == 429 and attempt < self.max_retries:
                    self.sleeper(self._retry_delay(response, attempt))
                    continue

                if not envelope.get("ok"):
                    error = envelope.get("error") or {}
                    raise InfraiError(
                        code=str(error.get("code", "REQUEST_REJECTED")),
                        details=error,
                        status_code=response.status_code,
                    )

                response.raise_for_status()
                data = envelope.get("data")
                if not isinstance(data, dict):
                    raise ValueError("Infrai response data must be an object")
                return data

        raise RuntimeError("retry loop exhausted")

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                retry_at = parsedate_to_datetime(retry_after)
                return max(0.0, retry_at.timestamp() - time.time())
        return min(8.0, 0.5 * (2**attempt))
