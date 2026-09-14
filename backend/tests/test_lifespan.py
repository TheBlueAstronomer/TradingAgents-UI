from datetime import UTC, datetime

from fastapi.testclient import TestClient

from backend.main import create_app
from backend.models import AnalysisCreate
from backend.services.store import AnalysisStore
from backend.settings import Settings


class RecordingRunner:
    def __init__(self) -> None:
        self.enqueued = []
        self.started = False
        self.stopped = False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def enqueue(self, run_id) -> None:
        self.enqueued.append(run_id)


def request(ticker: str) -> AnalysisCreate:
    return AnalysisCreate(
        ticker=ticker,
        analysis_date=datetime.now(UTC).date(),
        analysts=["market"],
        llm_provider="openai",
        quick_think_llm="gpt-5.6-luna",
        deep_think_llm="gpt-5.6",
        research_depth=1,
    )


def test_startup_reconciles_running_and_reenqueues_queued(tmp_path):
    database = tmp_path / "lifespan.sqlite3"
    store = AnalysisStore(database)
    store.initialize()
    queued = store.create_run(request("AAPL"), "stock")
    running = store.create_run(request("MSFT"), "stock")
    store.transition(running.id, status="running")
    runner = RecordingRunner()
    app = create_app(Settings(database_path=database), store, runner)  # type: ignore[arg-type]

    with TestClient(app):
        assert runner.started is True
        assert runner.enqueued == [queued.id]
        failed = store.get_run(running.id)
        assert failed.status == "failed"
        assert [event.type for event in store.events_after(running.id, 0)[-2:]] == [
            "status",
            "error",
        ]

    assert runner.stopped is True
