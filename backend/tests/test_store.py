from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest

from backend.models import AnalysisCreate
from backend.services.store import AnalysisStore, CheckpointCleanup


def request(ticker="AAPL"):
    return AnalysisCreate(ticker=ticker, analysis_date=datetime.now(UTC).date(), analysts=["market"], llm_provider="openai", quick_think_llm="gpt-5.6-luna", deep_think_llm="gpt-5.6", research_depth=2)


def test_persists_detail_events_and_survives_reopen(store):
    run = store.create_run(request(), "stock")
    store.record_event(run.id, "report", {"key": "market_report", "markdown": "Evidence"}, reports={"market_report": "Evidence"})
    reopened = AnalysisStore(store.database_path)
    assert reopened.get_run(run.id).reports == {"market_report": "Evidence"}
    assert [event.seq for event in reopened.events_after(run.id, 0)] == [1, 2]


def test_filter_sort_and_page_are_stable(store):
    runs = [store.create_run(request(ticker), "stock") for ticker in ("ZZZ", "AAA", "MMM")]
    store.record_event(runs[1].id, "signal", {"signal": "BUY"}, signal="BUY")
    store.complete_run(runs[1].id)
    result = store.list_runs(page=1, page_size=1, ticker=None, status=None, signal=None, sort_by="ticker", sort_order="asc")
    assert result.total == 3 and result.items[0].ticker == "AAA"
    assert store.list_runs(page=1, page_size=10, ticker="AA", status="completed", signal="BUY", sort_by="ticker", sort_order="asc").total == 1


def test_concurrent_writers_assign_unique_monotonic_sequences(store):
    run = store.create_run(request(), "stock")
    with ThreadPoolExecutor(max_workers=8) as pool:
        events = list(pool.map(lambda n: store.record_event(run.id, "message", {"content": str(n)}), range(24)))
    sequences = sorted(event.seq for event in events)
    assert sequences == list(range(2, 26))
    assert [event.seq for event in store.events_after(run.id, 0)] == list(range(1, 26))


def test_transitions_are_persisted_and_restart_marks_stale_running_failed(store):
    stale = store.create_run(request("STALE"), "stock")
    queued = store.create_run(request("QUEUED"), "stock")
    store.transition(stale.id, status="running")
    assert store.reconcile_interrupted_runs() == 1
    assert store.get_run(stale.id).status == "failed"
    assert store.get_run(stale.id).error_message == "PROCESS_RESTARTED"
    terminal_events = store.events_after(stale.id, 0)[-2:]
    assert [event.type for event in terminal_events] == ["status", "error"]
    assert terminal_events[0].data == {"status": "failed"}
    assert terminal_events[1].data["code"] == "PROCESS_RESTARTED"
    assert terminal_events[1].data["retryable"] is True
    assert terminal_events[1].data["run"]["last_event_seq"] == terminal_events[1].seq
    assert store.list_queued_run_ids() == [queued.id]


def test_terminal_operations_persist_status_then_terminal_snapshot(store):
    completed = store.create_run(request("DONE"), "stock")
    store.transition(completed.id, status="running")
    complete = store.complete_run(completed.id)
    completed_events = store.events_after(completed.id, 0)

    assert [event.type for event in completed_events[-2:]] == ["status", "complete"]
    assert completed_events[-2].data == {"status": "completed"}
    assert complete.data["run"]["status"] == "completed"
    assert complete.data["run"]["last_event_seq"] == complete.seq
    assert store.get_run(completed.id).last_event_seq == complete.seq

    failed = store.create_run(request("FAILED"), "stock")
    store.transition(failed.id, status="running")
    error = store.fail_run(
        failed.id,
        error_message="Analysis failed: RuntimeError",
        agent_statuses={"Market Analyst": "error"},
    )
    failed_events = store.events_after(failed.id, 0)

    assert [event.type for event in failed_events[-2:]] == ["status", "error"]
    assert failed_events[-2].data == {"status": "failed"}
    assert error.data["run"]["status"] == "failed"
    assert error.data["run"]["agent_statuses"] == {"Market Analyst": "error"}
    assert error.data["run"]["last_event_seq"] == error.seq


def test_checkpoint_cleanup_marker_survives_reopen_until_explicitly_finished(store):
    run = store.create_run(request("CLEAN"), "stock")
    marker = CheckpointCleanup(
        run_id=run.id,
        data_cache_dir="/var/lib/tradingagents/cache",
        ticker="CLEAN",
        trade_date="2026-09-14",
        signature="analysts=market|debate=2|risk=2|asset=stock",
    )

    terminal = store.complete_run(run.id, checkpoint_cleanup=marker)
    assert terminal.data["run"]["status"] == "completed"
    assert store.list_checkpoint_cleanups() == [marker]

    reopened = AnalysisStore(store.database_path)
    reopened.initialize()
    reopened.initialize()
    assert reopened.list_checkpoint_cleanups() == [marker]

    reopened.finish_checkpoint_cleanup(run.id)
    reopened.finish_checkpoint_cleanup(run.id)
    assert reopened.list_checkpoint_cleanups() == []


def test_checkpoint_cleanup_marker_rolls_back_if_completion_fails(
    store, monkeypatch
):
    run = store.create_run(request("ROLLBACK"), "stock")
    marker = CheckpointCleanup(
        run_id=run.id,
        data_cache_dir="/tmp/cache",
        ticker="ROLLBACK",
        trade_date="2026-09-14",
        signature="signature",
    )
    original_append = store._append

    def fail_completed_status(conn, run_id, event_type, payload):
        if event_type == "status" and payload == {"status": "completed"}:
            raise RuntimeError("terminal write failed")
        return original_append(conn, run_id, event_type, payload)

    monkeypatch.setattr(store, "_append", fail_completed_status)
    with pytest.raises(RuntimeError, match="terminal write failed"):
        store.complete_run(run.id, checkpoint_cleanup=marker)

    assert store.get_run(run.id).status == "queued"
    assert store.list_checkpoint_cleanups() == []
    assert [event.type for event in store.events_after(run.id, 0)] == ["status"]
