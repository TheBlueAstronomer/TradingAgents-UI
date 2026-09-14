from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from backend.models import AnalysisCreate


def payload(**overrides):
    value = {"ticker": " aapl ", "analysis_date": datetime.now(UTC).date().isoformat(), "analysts": ["market"], "llm_provider": "openai", "quick_think_llm": "gpt-5.6-luna", "deep_think_llm": "gpt-5.6", "research_depth": 1}
    value.update(overrides)
    return value


@pytest.mark.parametrize("ticker,asset_type", [("BTC-USD", "crypto"), ("0700.HK", "stock"), ("GC=F", "stock"), ("^NSEI", "stock")])
def test_accepts_market_symbol_forms(app_client, ticker, asset_type):
    client, _, runner = app_client
    response = client.post("/api/analysis", json=payload(ticker=ticker))
    assert response.status_code == 202 and response.json()["ticker"] == ticker
    assert response.json()["asset_type"] == asset_type and len(runner.enqueued) == 1


def test_post_is_async_and_normalizes_ticker(app_client):
    client, store, runner = app_client
    response = client.post("/api/analysis", json=payload())
    body = response.json(); run_id = UUID(body["id"])
    assert response.status_code == 202 and body["ticker"] == "AAPL" and body["status"] == "queued"
    assert store.events_after(run_id, 0)[0].data == {"status": "queued"} and runner.enqueued == [run_id]


@pytest.mark.parametrize("bad", ["AAPL/../../etc", "", "A" * 33])
def test_rejects_unsafe_ticker(bad):
    with pytest.raises(ValidationError): AnalysisCreate(**payload(ticker=bad))


@pytest.mark.parametrize("change", [{"analysts": []}, {"analysts": ["market", "market"]}, {"analysts": ["unknown"]}, {"analysis_date": (datetime.now(UTC).date() + timedelta(days=1)).isoformat()}])
def test_request_validation_rejects_bad_analysts_and_future_dates(app_client, change):
    client, _, _ = app_client
    assert client.post("/api/analysis", json=payload(**change)).status_code == 422


def test_provider_and_model_errors_are_structured(app_client):
    client, _, _ = app_client
    unknown = client.post("/api/analysis", json=payload(llm_provider="not-a-provider"))
    incompatible = client.post("/api/analysis", json=payload(quick_think_llm="not-openai"))
    assert unknown.status_code == incompatible.status_code == 422
    assert unknown.json()["detail"]["code"] == "INVALID_PROVIDER"
    assert incompatible.json()["detail"] == {"code": "INVALID_MODEL", "message": "Model is incompatible with provider", "field": "quick_think_llm"}


def test_openai_compatible_requires_backend_url_and_missing_run_is_404(app_client):
    client, _, _ = app_client
    response = client.post("/api/analysis", json=payload(llm_provider="openai_compatible", quick_think_llm="custom", deep_think_llm="custom"))
    assert response.status_code == 422
    missing = client.get(f"/api/analysis/{uuid4()}")
    assert missing.status_code == 404 and missing.json()["detail"]["code"] == "RUN_NOT_FOUND"


def test_literal_custom_placeholder_is_not_a_custom_model_id(app_client):
    client, _, _ = app_client
    response = client.post("/api/analysis", json=payload(llm_provider="openai_compatible", quick_think_llm="custom", deep_think_llm="custom", backend_url="http://localhost:11434"))
    assert response.status_code == 422
