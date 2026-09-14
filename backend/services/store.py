from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from backend.models import (
    AnalysisCreate,
    AnalysisDetail,
    AnalysisSummary,
    HistoryPage,
    StreamEvent,
)

UTC = timezone.utc
SORT_COLUMNS = {"created_at": "created_at", "ticker": "ticker", "analysis_date": "analysis_date", "status": "status", "signal": "signal"}

def now() -> datetime: return datetime.now(UTC)
def stamp(value: datetime | None = None) -> str: return (value or now()).isoformat()

@dataclass(frozen=True, slots=True)
class CheckpointCleanup:
    run_id: UUID
    data_cache_dir: str
    ticker: str
    trade_date: str
    signature: str

class AnalysisStore:
    def __init__(self, database_path: Path) -> None: self.database_path = database_path
    def _conn(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.database_path, timeout=20, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    def initialize(self) -> None:
        with self._conn() as conn: conn.executescript((Path(__file__).parents[1] / "schema.sql").read_text())
    def _detail(self, row: sqlite3.Row) -> AnalysisDetail:
        raw = dict(row)
        return AnalysisDetail(id=UUID(raw["id"]), ticker=raw["ticker"], analysis_date=raw["analysis_date"], asset_type=raw["asset_type"], analysts=json.loads(raw["analysts_json"]), llm_provider=raw["llm_provider"], research_depth=raw["max_debate_rounds"], status=raw["status"], signal=raw["signal"], created_at=raw["created_at"], started_at=raw["started_at"], completed_at=raw["completed_at"], quick_think_llm=raw["quick_think_llm"], deep_think_llm=raw["deep_think_llm"], reports=json.loads(raw["reports_json"]), agent_statuses=json.loads(raw["agent_statuses_json"]), final_state=json.loads(raw["final_state_json"]) if raw["final_state_json"] else None, error_message=raw["error_message"], last_event_seq=raw["last_event_seq"])
    @staticmethod
    def _summary(detail: AnalysisDetail) -> AnalysisSummary: return AnalysisSummary(**detail.model_dump(exclude={"quick_think_llm", "deep_think_llm", "reports", "agent_statuses", "final_state", "error_message", "last_event_seq"}))
    def _append(self, conn: sqlite3.Connection, run_id: UUID, event_type: str, payload: dict[str, Any]) -> StreamEvent:
        seq = conn.execute("SELECT last_event_seq FROM analysis_runs WHERE id=?", (str(run_id),)).fetchone()[0] + 1
        emitted = stamp(); clean = json.loads(json.dumps(payload, default=str))
        conn.execute("UPDATE analysis_runs SET last_event_seq=? WHERE id=?", (seq, str(run_id)))
        conn.execute("INSERT INTO analysis_events VALUES(?,?,?,?,?)", (str(run_id), seq, event_type, json.dumps(clean), emitted))
        return StreamEvent(run_id=run_id, seq=seq, emitted_at=emitted, type=event_type, data=clean)
    def create_run(self, request: AnalysisCreate, asset_type: str) -> AnalysisDetail:
        run_id = uuid4(); created = stamp(); config = request.model_dump(mode="json")
        statuses = {name: "pending" for name in self._agent_names(request.analysts)}
        with self._conn() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("INSERT INTO analysis_runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (str(run_id), request.ticker, request.analysis_date.isoformat(), asset_type, json.dumps(request.analysts), request.llm_provider, request.quick_think_llm, request.deep_think_llm, request.research_depth, request.research_depth, str(request.backend_url) if request.backend_url else None, json.dumps(config), "queued", None, "{}", json.dumps(statuses), None, None, 0, created, None, None))
            self._append(conn, run_id, "status", {"status": "queued"}); conn.commit()
        return self.get_run(run_id)  # type: ignore[return-value]
    @staticmethod
    def _agent_names(analysts: list[str]) -> list[str]:
        labels = {"market": "Market Analyst", "social": "Sentiment Analyst", "news": "News Analyst", "fundamentals": "Fundamentals Analyst"}
        return [labels[a] for a in analysts] + ["Bull Researcher", "Bear Researcher", "Research Manager", "Trader", "Aggressive Analyst", "Neutral Analyst", "Conservative Analyst", "Portfolio Manager"]
    def get_run(self, run_id: UUID) -> AnalysisDetail | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM analysis_runs WHERE id=?", (str(run_id),)).fetchone()
        return self._detail(row) if row else None
    def request_config(self, run_id: UUID) -> dict[str, Any]:
        with self._conn() as conn: row = conn.execute("SELECT config_json FROM analysis_runs WHERE id=?", (str(run_id),)).fetchone()
        return json.loads(row[0]) if row else {}
    def list_queued_run_ids(self) -> list[UUID]:
        with self._conn() as conn: rows = conn.execute("SELECT id FROM analysis_runs WHERE status='queued' ORDER BY created_at").fetchall()
        return [UUID(row[0]) for row in rows]
    def list_runs(self, *, page: int, page_size: int, ticker: str | None, status: str | None, signal: str | None, sort_by: str, sort_order: str) -> HistoryPage:
        column = SORT_COLUMNS[sort_by]; direction = "ASC" if sort_order == "asc" else "DESC"; clauses=[]; values: list[Any]=[]
        if ticker: clauses.append("ticker LIKE ?"); values.append(f"%{ticker.upper()}%")
        if status: clauses.append("status=?"); values.append(status)
        if signal: clauses.append("signal=?"); values.append(signal)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._conn() as conn:
            total=conn.execute("SELECT COUNT(*) FROM analysis_runs" + where, values).fetchone()[0]
            rows=conn.execute(f"SELECT * FROM analysis_runs{where} ORDER BY {column} {direction} LIMIT ? OFFSET ?", [*values, page_size, (page-1)*page_size]).fetchall()
        return HistoryPage(items=[self._summary(self._detail(row)) for row in rows], total=total, page=page, page_size=page_size)
    def transition(self, run_id: UUID, *, status: str, error_message: str | None = None) -> StreamEvent:
        with self._conn() as conn:
            conn.execute("BEGIN IMMEDIATE"); field = "started_at" if status == "running" else "completed_at" if status in {"completed", "failed"} else None
            sets="status=?, error_message=?" + (f", {field}=?" if field else ""); vals=[status,error_message] + ([stamp()] if field else []) + [str(run_id)]
            conn.execute(f"UPDATE analysis_runs SET {sets} WHERE id=?", vals); event=self._append(conn, run_id, "status", {"status": status}); conn.commit(); return event
    def _finalize_run(
        self,
        run_id: UUID,
        *,
        status: str,
        terminal_type: str,
        terminal_data: dict[str, Any],
        error_message: str | None,
        agent_statuses: dict[str, str] | None = None,
        checkpoint_cleanup: CheckpointCleanup | None = None,
    ) -> StreamEvent:
        """Persist terminal state and its stream events in one transaction."""
        if checkpoint_cleanup and checkpoint_cleanup.run_id != run_id:
            raise ValueError("Checkpoint cleanup marker must match the completed run")
        with self._conn() as conn:
            conn.execute("BEGIN IMMEDIATE")
            sets = ["status=?", "error_message=?", "completed_at=?"]
            values: list[Any] = [status, error_message, stamp()]
            if agent_statuses is not None:
                sets.append("agent_statuses_json=?")
                values.append(json.dumps(agent_statuses))
            result = conn.execute(
                "UPDATE analysis_runs SET " + ", ".join(sets) + " WHERE id=?",
                [*values, str(run_id)],
            )
            if result.rowcount != 1:
                conn.rollback()
                raise KeyError(f"Unknown analysis run: {run_id}")

            if checkpoint_cleanup:
                conn.execute(
                    "INSERT INTO checkpoint_cleanups "
                    "(run_id, data_cache_dir, ticker, trade_date, signature) "
                    "VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT(run_id) DO UPDATE SET "
                    "data_cache_dir=excluded.data_cache_dir, "
                    "ticker=excluded.ticker, trade_date=excluded.trade_date, "
                    "signature=excluded.signature",
                    (
                        str(checkpoint_cleanup.run_id),
                        checkpoint_cleanup.data_cache_dir,
                        checkpoint_cleanup.ticker,
                        checkpoint_cleanup.trade_date,
                        checkpoint_cleanup.signature,
                    ),
                )

            self._append(conn, run_id, "status", {"status": status})
            terminal = self._append(conn, run_id, terminal_type, terminal_data)

            # The terminal payload is assembled only after its sequence is assigned,
            # so a reconnect never receives a run snapshot one event behind.
            row = conn.execute(
                "SELECT * FROM analysis_runs WHERE id=?", (str(run_id),)
            ).fetchone()
            detail = self._detail(row)
            payload = {
                **terminal_data,
                "run": detail.model_dump(mode="json"),
            }
            clean = json.loads(json.dumps(payload, default=str))
            conn.execute(
                "UPDATE analysis_events SET payload_json=? WHERE run_id=? AND seq=?",
                (json.dumps(clean), str(run_id), terminal.seq),
            )
            conn.commit()
            return terminal.model_copy(update={"data": clean})

    def complete_run(
        self,
        run_id: UUID,
        *,
        checkpoint_cleanup: CheckpointCleanup | None = None,
    ) -> StreamEvent:
        return self._finalize_run(
            run_id,
            status="completed",
            terminal_type="complete",
            terminal_data={},
            error_message=None,
            checkpoint_cleanup=checkpoint_cleanup,
        )

    def fail_run(
        self,
        run_id: UUID,
        *,
        error_message: str,
        code: str = "ANALYSIS_FAILED",
        retryable: bool = False,
        agent_statuses: dict[str, str] | None = None,
    ) -> StreamEvent:
        return self._finalize_run(
            run_id,
            status="failed",
            terminal_type="error",
            terminal_data={
                "code": code,
                "message": error_message,
                "retryable": retryable,
            },
            error_message=error_message,
            agent_statuses=agent_statuses,
        )
    def list_checkpoint_cleanups(self) -> list[CheckpointCleanup]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT run_id, data_cache_dir, ticker, trade_date, signature "
                "FROM checkpoint_cleanups ORDER BY run_id"
            ).fetchall()
        return [
            CheckpointCleanup(
                run_id=UUID(row["run_id"]),
                data_cache_dir=row["data_cache_dir"],
                ticker=row["ticker"],
                trade_date=row["trade_date"],
                signature=row["signature"],
            )
            for row in rows
        ]

    def finish_checkpoint_cleanup(self, run_id: UUID) -> None:
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM checkpoint_cleanups WHERE run_id=?", (str(run_id),)
            )
    def record_event(self, run_id: UUID, event_type: str, payload: dict[str, Any], *, reports: dict[str, str] | None = None, agent_statuses: dict[str, str] | None = None, signal: str | None = None, final_state: dict[str, Any] | None = None) -> StreamEvent:
        with self._conn() as conn:
            conn.execute("BEGIN IMMEDIATE"); sets=[]; vals=[]
            for column, value in (("reports_json", reports), ("agent_statuses_json", agent_statuses), ("signal", signal), ("final_state_json", final_state)):
                if value is not None: sets.append(f"{column}=?"); vals.append(json.dumps(value, default=str) if column.endswith("json") else value)
            if sets: conn.execute("UPDATE analysis_runs SET " + ", ".join(sets) + " WHERE id=?", [*vals, str(run_id)])
            event=self._append(conn, run_id, event_type, payload); conn.commit(); return event
    def events_after(self, run_id: UUID, seq: int) -> list[StreamEvent]:
        with self._conn() as conn: rows=conn.execute("SELECT * FROM analysis_events WHERE run_id=? AND seq>? ORDER BY seq", (str(run_id),seq)).fetchall()
        return [StreamEvent(run_id=UUID(row["run_id"]),seq=row["seq"],emitted_at=row["created_at"],type=row["event_type"],data=json.loads(row["payload_json"])) for row in rows]
    def reconcile_interrupted_runs(self) -> int:
        with self._conn() as conn:
            rows=conn.execute("SELECT id FROM analysis_runs WHERE status='running'").fetchall()
        for row in rows:
            self.fail_run(
                UUID(row[0]),
                error_message="PROCESS_RESTARTED",
                code="PROCESS_RESTARTED",
                retryable=True,
            )
        return len(rows)
