from datetime import UTC, datetime

from backend.models import AnalysisCreate


def request(ticker: str) -> AnalysisCreate:
    return AnalysisCreate(ticker=ticker, analysis_date=datetime.now(UTC).date(), analysts=["market"], llm_provider="openai", quick_think_llm="gpt-5.6-luna", deep_think_llm="gpt-5.6", research_depth=1)


def test_history_filters_sorts_and_pages(app_client):
    client, store, _ = app_client
    _, beta, _ = (store.create_run(request(t), "stock") for t in ("AAA", "BBB", "CCC"))
    store.transition(beta.id, status="completed")
    store.record_event(beta.id, "signal", {"signal": "BUY"}, signal="BUY")
    filtered = client.get("/api/history?ticker=B&status=completed&signal=BUY&sort_by=ticker&sort_order=asc")
    assert filtered.status_code == 200 and filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["id"] == str(beta.id)
    page = client.get("/api/history?page=2&page_size=1&sort_by=ticker&sort_order=asc")
    assert page.json()["total"] == 3 and page.json()["items"][0]["ticker"] == "BBB"


def test_history_rejects_bad_bounds_and_sqlish_sort_parameter(app_client):
    client, _, _ = app_client
    for url in ("/api/history?page=0", "/api/history?page_size=101", "/api/history?sort_by=ticker;DROP%20TABLE%20analysis_runs"):
        assert client.get(url).status_code == 422
