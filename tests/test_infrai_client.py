import httpx
import pytest

from nonprofit_meter.infrai_client import InfraiClient, InfraiError


def test_decodes_rejection_envelope_before_status_handling() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/v1/account/usage/timeseries"
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(
            400,
            json={"ok": False, "data": None, "error": {"code": "BAD_REQUEST"}, "metadata": {}},
        )

    client = InfraiClient(api_key="test-key", transport=httpx.MockTransport(handler))
    with pytest.raises(InfraiError) as caught:
        client.usage_timeseries()

    assert caught.value.code == "BAD_REQUEST"
    assert caught.value.status_code == 400


def test_retries_rate_limit_using_retry_after() -> None:
    calls = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "2"},
                json={"ok": False, "data": None, "error": {"code": "RATE_LIMITED"}, "metadata": {}},
            )
        return httpx.Response(200, json={"ok": True, "data": {"points": []}, "error": None, "metadata": {}})

    client = InfraiClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
        sleeper=delays.append,
    )

    assert client.usage_timeseries() == {"points": []}
    assert calls == 2
    assert delays == [2.0]
