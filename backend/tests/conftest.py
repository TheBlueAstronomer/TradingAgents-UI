from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.services.store import AnalysisStore
from backend.settings import Settings


class IdleRunner:
    """Lifecycle-safe runner used by HTTP and websocket contract tests."""
    def __init__(self) -> None: self.enqueued = []
    async def start(self) -> None: pass
    async def stop(self) -> None: pass
    async def enqueue(self, run_id) -> None: self.enqueued.append(run_id)
    async def wait_for_events(self, run_id, after, timeout=20.0) -> None:
        import asyncio
        await asyncio.sleep(0.01)


@pytest.fixture
def store(tmp_path: Path) -> AnalysisStore:
    value = AnalysisStore(tmp_path / "test.sqlite3")
    value.initialize()
    return value


@pytest.fixture
def app_client(tmp_path: Path) -> Iterator[tuple[TestClient, AnalysisStore, IdleRunner]]:
    database = tmp_path / "api.sqlite3"
    store = AnalysisStore(database)
    runner = IdleRunner()
    app = create_app(Settings(database_path=database), store, runner)  # type: ignore[arg-type]
    with TestClient(app) as client: yield client, store, runner
