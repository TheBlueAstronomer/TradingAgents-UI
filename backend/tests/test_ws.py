from datetime import UTC, datetime
from uuid import uuid4

import pytest
from starlette.testclient import WebSocketDisconnect

from backend.models import AnalysisCreate


def request():
    return AnalysisCreate(ticker="AAPL", analysis_date=datetime.now(UTC).date(), analysts=["market"], llm_provider="openai", quick_think_llm="gpt-5.6-luna", deep_think_llm="gpt-5.6", research_depth=1)


def test_initial_snapshot_then_later_terminal_event(app_client):
    client, store, _ = app_client
    run = store.create_run(request(), "stock")
    with client.websocket_connect(f"/ws/analysis/{run.id}") as socket:
        snapshot = socket.receive_json()
        assert snapshot["type"] == "snapshot" and snapshot["seq"] == 1
        store.complete_run(run.id)
        status = socket.receive_json()
        complete = socket.receive_json()
        assert status["type"] == "status" and status["data"] == {
            "status": "completed"
        }
        assert complete["type"] == "complete"
        assert complete["data"]["run"]["status"] == "completed"
        assert complete["data"]["run"]["last_event_seq"] == complete["seq"]
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
        assert closed.value.code == 1000


def test_cursor_replays_only_events_after_requested_sequence(app_client):
    client, store, _ = app_client
    run = store.create_run(request(), "stock")
    store.record_event(run.id, "message", {"content": "first", "category": "Agent"})
    store.fail_run(run.id, error_message="terminal", code="X")
    with client.websocket_connect(f"/ws/analysis/{run.id}?after=1") as socket:
        assert socket.receive_json()["data"]["content"] == "first"
        failed = socket.receive_json()
        error = socket.receive_json()
        assert failed["type"] == "status" and failed["data"] == {
            "status": "failed"
        }
        assert error["type"] == "error" and error["data"]["code"] == "X"
        assert error["data"]["run"]["status"] == "failed"


@pytest.mark.parametrize("path,code", [("?after=-1", 4400), ("", 4404)])
def test_invalid_cursor_and_unknown_run_close_with_protocol_codes(app_client, path, code):
    client, _, _ = app_client
    with pytest.raises(WebSocketDisconnect) as raised, client.websocket_connect(f"/ws/analysis/{uuid4()}{path}"):
        pass
    assert raised.value.code == code


def test_future_cursor_is_rejected_instead_of_waiting_forever(app_client):
    client, store, _ = app_client
    run = store.create_run(request(), "stock")
    with pytest.raises(WebSocketDisconnect) as raised, client.websocket_connect(
        f"/ws/analysis/{run.id}?after={run.last_event_seq + 1}"
    ):
        pass
    assert raised.value.code == 4400


@pytest.mark.parametrize("outcome", ["completed", "failed"])
def test_terminal_run_snapshot_is_sent_once_then_closed(app_client, outcome):
    client, store, _ = app_client
    run = store.create_run(request(), "stock")
    if outcome == "completed":
        store.complete_run(run.id)
    else:
        store.fail_run(run.id, error_message="terminal")

    with client.websocket_connect(f"/ws/analysis/{run.id}") as socket:
        snapshot = socket.receive_json()
        assert snapshot["type"] == "snapshot"
        assert snapshot["data"]["run"]["status"] == outcome
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
        assert closed.value.code == 1000


def test_caught_up_terminal_cursor_closes_without_hanging(app_client):
    client, store, _ = app_client
    run = store.create_run(request(), "stock")
    terminal = store.fail_run(run.id, error_message="terminal")

    with client.websocket_connect(
        f"/ws/analysis/{run.id}?after={terminal.seq}"
    ) as socket:
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
        assert closed.value.code == 1000
