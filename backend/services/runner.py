from __future__ import annotations

import ast
import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from backend.services.store import AnalysisStore, CheckpointCleanup

log = logging.getLogger(__name__)
REPORTS = {
    "market_report": ("Market Analyst", "Market analysis"),
    "sentiment_report": ("Sentiment Analyst", "Sentiment analysis"),
    "news_report": ("News Analyst", "News analysis"),
    "fundamentals_report": ("Fundamentals Analyst", "Fundamentals analysis"),
    "investment_plan": ("Research Manager", "Research memorandum"),
    "trader_investment_plan": ("Trader", "Trading plan"),
    "final_trade_decision": ("Portfolio Manager", "Final memorandum"),
}
RESEARCH_TEAM = ("Bull Researcher", "Bear Researcher", "Research Manager")
RISK_TEAM = ("Aggressive Analyst", "Conservative Analyst", "Neutral Analyst")
CHECKPOINT_CLEANUP_ATTEMPTS = 3
TEAMS = {
    "Market Analyst": "Analyst Team",
    "Sentiment Analyst": "Analyst Team",
    "News Analyst": "Analyst Team",
    "Fundamentals Analyst": "Analyst Team",
    "Bull Researcher": "Research Team",
    "Bear Researcher": "Research Team",
    "Research Manager": "Research Team",
    "Trader": "Trading Team",
    "Aggressive Analyst": "Risk Management",
    "Neutral Analyst": "Risk Management",
    "Conservative Analyst": "Risk Management",
    "Portfolio Manager": "Portfolio Management",
}


@dataclass
class RunAccumulator:
    reports: dict[str, str] = field(default_factory=dict)
    statuses: dict[str, str] = field(default_factory=dict)
    seen_messages: set[str] = field(default_factory=set)
    seen_debate_responses: set[str] = field(default_factory=set)
    final_state: dict[str, Any] = field(default_factory=dict)
    analyst_steps: tuple[tuple[str, str, str], ...] = ()


class AnalysisRunner:
    def __init__(self, store: AnalysisStore) -> None:
        self.store, self.queue, self.task, self.wake = (
            store,
            asyncio.Queue(),
            None,
            asyncio.Condition(),
        )

    async def start(self) -> None:
        if self.task is None:
            # A process may have committed completion and crashed before deleting
            # LangGraph's terminal checkpoint. Reconcile those durable markers
            # before any queued work is allowed to inspect checkpoint state.
            await asyncio.to_thread(self._reconcile_checkpoint_cleanups)
            self.task = asyncio.create_task(self._worker_loop())

    async def stop(self) -> None:
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
            self.task = None

    async def enqueue(self, run_id: UUID) -> None:
        await self.queue.put(run_id)

    async def wait_for_events(
        self, run_id: UUID, after: int, timeout: float = 20.0
    ) -> None:
        async with self.wake:
            # Close the check/subscribe gap: if an event committed after the
            # websocket's last read but before this waiter acquired the condition,
            # return immediately instead of sleeping until the long-poll timeout.
            run = self.store.get_run(run_id)
            if run is None or run.last_event_seq > after:
                return
            try:
                await asyncio.wait_for(self.wake.wait(), timeout)
            except asyncio.TimeoutError:
                pass

    async def _worker_loop(self) -> None:
        while True:
            run_id = await self.queue.get()
            try:
                await asyncio.to_thread(
                    self._execute_sync, run_id, asyncio.get_running_loop()
                )
            except Exception:
                log.exception("Worker failed for %s", run_id)
            finally:
                self.queue.task_done()

    def _notify(self, loop: asyncio.AbstractEventLoop) -> None:
        async def inner() -> None:
            async with self.wake:
                self.wake.notify_all()

        asyncio.run_coroutine_threadsafe(inner(), loop)

    def _event(
        self,
        loop: asyncio.AbstractEventLoop,
        run_id: UUID,
        kind: str,
        data: dict[str, Any],
        **updates: Any,
    ) -> None:
        self.store.record_event(run_id, kind, data, **updates)
        self._notify(loop)

    @staticmethod
    def _same_checkpoint(
        left: CheckpointCleanup, right: CheckpointCleanup
    ) -> bool:
        return (
            left.data_cache_dir,
            left.ticker,
            left.trade_date,
            left.signature,
        ) == (
            right.data_cache_dir,
            right.ticker,
            right.trade_date,
            right.signature,
        )

    def _retry_checkpoint_cleanup(self, cleanup: CheckpointCleanup) -> bool:
        """Clear and verify one durable cleanup marker with bounded retries."""
        from tradingagents.graph.checkpointer import (
            checkpoint_step,
            clear_checkpoint,
        )

        for attempt in range(1, CHECKPOINT_CLEANUP_ATTEMPTS + 1):
            try:
                clear_checkpoint(
                    cleanup.data_cache_dir,
                    cleanup.ticker,
                    cleanup.trade_date,
                    cleanup.signature,
                )
            except Exception:
                log.warning(
                    "Checkpoint cleanup failed for %s (attempt %d/%d)",
                    cleanup.run_id,
                    attempt,
                    CHECKPOINT_CLEANUP_ATTEMPTS,
                    exc_info=True,
                )
            try:
                remaining_step = checkpoint_step(
                    cleanup.data_cache_dir,
                    cleanup.ticker,
                    cleanup.trade_date,
                    cleanup.signature,
                )
                if remaining_step is None:
                    self.store.finish_checkpoint_cleanup(cleanup.run_id)
                    return True
                log.warning(
                    "Checkpoint cleanup verification found step %s for %s "
                    "(attempt %d/%d)",
                    remaining_step,
                    cleanup.run_id,
                    attempt,
                    CHECKPOINT_CLEANUP_ATTEMPTS,
                )
            except Exception:
                log.warning(
                    "Checkpoint cleanup verification failed for %s "
                    "(attempt %d/%d)",
                    cleanup.run_id,
                    attempt,
                    CHECKPOINT_CLEANUP_ATTEMPTS,
                    exc_info=True,
                )
        log.error("Checkpoint cleanup remains pending for %s", cleanup.run_id)
        return False

    def _reconcile_checkpoint_cleanups(
        self, matching: CheckpointCleanup | None = None
    ) -> bool:
        """Retry persisted cleanups, optionally limiting work to one graph key."""
        pending = self.store.list_checkpoint_cleanups()
        if matching is not None:
            pending = [
                cleanup
                for cleanup in pending
                if self._same_checkpoint(cleanup, matching)
            ]
        results = [self._retry_checkpoint_cleanup(cleanup) for cleanup in pending]
        return all(results)

    def _set_agent_status(
        self,
        loop: asyncio.AbstractEventLoop,
        run_id: UUID,
        state: RunAccumulator,
        agent: str,
        status: str,
    ) -> None:
        """Persist one real status transition without emitting duplicate events."""
        previous = state.statuses.get(agent)
        if previous is None or previous == status:
            return
        # Stream mode ``values`` repeats prior completed fields on every later
        # node. Those cumulative values must never move a terminal agent back to
        # in-progress while downstream teams are working.
        if previous in {"completed", "error"}:
            return
        state.statuses[agent] = status
        self._event(
            loop,
            run_id,
            "agent_status",
            {"agent": agent, "team": TEAMS[agent], "status": status},
            agent_statuses=dict(state.statuses),
        )

    def _emit_report(
        self,
        loop: asyncio.AbstractEventLoop,
        run_id: UUID,
        state: RunAccumulator,
        key: str,
        title: str,
        value: Any,
    ) -> bool:
        """Persist a report only when its complete markdown value changes."""
        if not isinstance(value, str) or not value.strip():
            return False
        if state.reports.get(key) == value:
            return True
        state.reports[key] = value
        self._event(
            loop,
            run_id,
            "report",
            {"key": key, "title": title, "markdown": value},
            reports=dict(state.reports),
            agent_statuses=dict(state.statuses),
        )
        return True

    def _emit_debate_response(
        self,
        loop: asyncio.AbstractEventLoop,
        run_id: UUID,
        state: RunAccumulator,
        *,
        phase: str,
        source: str,
        count: Any,
        content: Any,
    ) -> None:
        """Project each distinct cumulative-debate response into activity once."""
        if not isinstance(content, str) or not content.strip():
            return
        response = content.strip()
        digest = hashlib.sha256(response.encode("utf-8")).hexdigest()[:16]
        identity = f"{phase}:{count}:{source}:{digest}"
        if identity in state.seen_debate_responses:
            return
        state.seen_debate_responses.add(identity)
        self._event(
            loop,
            run_id,
            "message",
            {
                "messageId": identity,
                "category": "Agent",
                "source": source,
                "stage": "Research debate" if phase == "research" else "Risk debate",
                "content": response[:8192],
            },
        )

    def _sync_analyst_statuses(
        self,
        loop: asyncio.AbstractEventLoop,
        run_id: UUID,
        state: RunAccumulator,
    ) -> None:
        """Mirror the selected-analyst progression used by the upstream CLI."""
        found_active = False
        for agent, report_key, _ in state.analyst_steps:
            if state.reports.get(report_key):
                self._set_agent_status(loop, run_id, state, agent, "completed")
            elif not found_active:
                self._set_agent_status(loop, run_id, state, agent, "in_progress")
                found_active = True

        if (
            state.analyst_steps
            and not found_active
            and state.statuses.get("Bull Researcher") == "pending"
        ):
            self._set_agent_status(
                loop, run_id, state, "Bull Researcher", "in_progress"
            )

    @staticmethod
    def _extract_content_string(content: Any) -> str | None:
        """Mirror the pinned CLI's structured LangChain content extraction."""

        def is_empty(value: Any) -> bool:
            if value is None or value == "":
                return True
            if isinstance(value, str):
                stripped = value.strip()
                if not stripped:
                    return True
                try:
                    return not bool(ast.literal_eval(stripped))
                except (ValueError, SyntaxError):
                    return False
            return not bool(value)

        if is_empty(content):
            return None
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, dict):
            text = content.get("text", "")
            return text.strip() if isinstance(text, str) and not is_empty(text) else None
        if isinstance(content, list):
            text_parts = [
                item.get("text", "").strip()
                if isinstance(item, dict)
                and item.get("type") == "text"
                and isinstance(item.get("text"), str)
                else item.strip()
                if isinstance(item, str)
                else ""
                for item in content
            ]
            result = " ".join(
                text for text in text_parts if text and not is_empty(text)
            )
            return result or None
        return str(content).strip() if not is_empty(content) else None

    @classmethod
    def _classify_message(cls, message: Any) -> tuple[str, str | None]:
        """Return the browser category used by the pinned CLI for a message."""
        from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

        content = cls._extract_content_string(getattr(message, "content", None))
        if isinstance(message, HumanMessage):
            return ("Control" if content == "Continue" else "User", content)
        if isinstance(message, ToolMessage):
            return "Data", content
        if isinstance(message, AIMessage):
            return "Agent", content
        return "System", content

    def _build_config(self, run: Any) -> dict[str, Any]:
        from tradingagents.default_config import DEFAULT_CONFIG

        original = self.store.request_config(run.id)
        config = DEFAULT_CONFIG.copy()
        config.update(
            {
                "llm_provider": run.llm_provider,
                "quick_think_llm": run.quick_think_llm,
                "deep_think_llm": run.deep_think_llm,
                "backend_url": original.get("backend_url"),
                "max_debate_rounds": run.research_depth,
                "max_risk_discuss_rounds": run.research_depth,
            }
        )
        return config

    @staticmethod
    def _tool_arguments(value: Any) -> dict[str, Any] | list[Any] | str:
        """Project untrusted tool metadata without allowing it to abort a run."""
        try:
            serialized = json.dumps(value, default=str)
        except Exception:  # noqa: BLE001 - third-party metadata can be circular or hostile
            try:
                fallback = str(value)
            except Exception:  # noqa: BLE001 - third-party __str__ may itself fail
                fallback = "<unserializable tool arguments>"
            return fallback[:2047] + ("…" if len(fallback) > 2048 else "")
        if len(serialized) > 2048:
            return serialized[:2047] + "…"
        try:
            parsed = json.loads(serialized)
        except (TypeError, ValueError):
            return serialized
        return parsed if isinstance(parsed, (dict, list)) else serialized

    def _consume_chunk(
        self,
        run_id: UUID,
        chunk: dict[str, Any],
        state: RunAccumulator,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        if loop is None:
            return
        state.final_state.update(chunk)
        for message in chunk.get("messages", []) or []:
            message_id = getattr(message, "id", None)
            if message_id and message_id in state.seen_messages:
                continue
            if message_id:
                state.seen_messages.add(message_id)
            category, content = self._classify_message(message)
            if content and content.strip():
                self._event(
                    loop,
                    run_id,
                    "message",
                    {
                        "messageId": message_id,
                        "category": category,
                        "content": content[:8192],
                    },
                )
            for call in getattr(message, "tool_calls", []) or []:
                try:
                    name = (
                        call.get("name", "tool")
                        if isinstance(call, dict)
                        else getattr(call, "name", "tool")
                    )
                    args = (
                        call.get("args")
                        if isinstance(call, dict)
                        else getattr(call, "args", {})
                    )
                    self._event(
                        loop,
                        run_id,
                        "tool_call",
                        {
                            "toolName": str(name),
                            "arguments": self._tool_arguments(args),
                        },
                    )
                except (
                    Exception
                ):  # tool metadata is observational, not analysis-critical
                    log.warning("Could not project tool metadata", exc_info=True)
        # Selected analysts run in the order supplied to the upstream graph.
        for _, report_key, title in state.analyst_steps:
            self._emit_report(
                loop, run_id, state, report_key, title, chunk.get(report_key)
            )
        self._sync_analyst_statuses(loop, run_id, state)

        debate = chunk.get("investment_debate_state")
        if isinstance(debate, dict):
            investment_plan = chunk.get("investment_plan")
            has_judgment = bool(debate.get("judge_decision"))
            has_history = any(
                isinstance(debate.get(key), str) and debate.get(key, "").strip()
                for key in ("bull_history", "bear_history")
            )
            if has_history:
                # A resumed stream may first yield an already-accumulated debate.
                # Preserve the CLI's in-progress step before completing the team.
                for agent in RESEARCH_TEAM:
                    if state.statuses.get(agent) != "completed":
                        self._set_agent_status(
                            loop, run_id, state, agent, "in_progress"
                        )
            if has_judgment and self._emit_report(
                loop,
                run_id,
                state,
                "investment_plan",
                REPORTS["investment_plan"][1],
                investment_plan,
            ):
                for agent in RESEARCH_TEAM:
                    self._set_agent_status(
                        loop, run_id, state, agent, "completed"
                    )
                self._set_agent_status(loop, run_id, state, "Trader", "in_progress")
            elif not has_judgment:
                response = debate.get("current_response")
                source = None
                if isinstance(response, str):
                    if response.lstrip().startswith("Bull Analyst:"):
                        source = "Bull Researcher"
                    elif response.lstrip().startswith("Bear Analyst:"):
                        source = "Bear Researcher"
                if source and not has_history:
                    # The CLI exposes the research group as active before it
                    # displays the debate content, including on a resumed stream
                    # whose first value already contains cumulative history.
                    for agent in RESEARCH_TEAM:
                        if state.statuses.get(agent) != "completed":
                            self._set_agent_status(
                                loop, run_id, state, agent, "in_progress"
                            )
                if source:
                    self._emit_debate_response(
                        loop,
                        run_id,
                        state,
                        phase="research",
                        source=source,
                        count=debate.get("count", "unknown"),
                        content=response,
                    )

        trader_plan = chunk.get("trader_investment_plan")
        if self._emit_report(
            loop,
            run_id,
            state,
            "trader_investment_plan",
            REPORTS["trader_investment_plan"][1],
            trader_plan,
        ):
            self._set_agent_status(loop, run_id, state, "Trader", "completed")
            self._set_agent_status(
                loop, run_id, state, "Aggressive Analyst", "in_progress"
            )

        risk = chunk.get("risk_debate_state")
        if isinstance(risk, dict):
            speaker = risk.get("latest_speaker")
            risk_speakers = {
                "Aggressive": ("Aggressive Analyst", "current_aggressive_response"),
                "Conservative": (
                    "Conservative Analyst",
                    "current_conservative_response",
                ),
                "Neutral": ("Neutral Analyst", "current_neutral_response"),
            }
            final_decision = chunk.get("final_trade_decision")
            for agent, history_key in {
                "Aggressive": ("Aggressive Analyst", "aggressive_history"),
                "Conservative": (
                    "Conservative Analyst",
                    "conservative_history",
                ),
                "Neutral": ("Neutral Analyst", "neutral_history"),
            }.values():
                history = risk.get(history_key)
                if (
                    isinstance(history, str)
                    and history.strip()
                    and state.statuses.get(agent) != "completed"
                ):
                    # As with research, accumulated resumed state still passes
                    # through an observable active step before completion.
                    self._set_agent_status(
                        loop, run_id, state, agent, "in_progress"
                    )
            if risk.get("judge_decision"):
                self._set_agent_status(
                    loop, run_id, state, "Portfolio Manager", "in_progress"
                )
                if self._emit_report(
                    loop,
                    run_id,
                    state,
                    "final_trade_decision",
                    REPORTS["final_trade_decision"][1],
                    final_decision,
                ):
                    for agent in (*RISK_TEAM, "Portfolio Manager"):
                        self._set_agent_status(
                            loop, run_id, state, agent, "completed"
                        )
            else:
                if speaker in risk_speakers:
                    source, response_key = risk_speakers[speaker]
                    self._set_agent_status(
                        loop, run_id, state, source, "in_progress"
                    )
                    self._emit_debate_response(
                        loop,
                        run_id,
                        state,
                        phase="risk",
                        source=source,
                        count=risk.get("count", "unknown"),
                        content=risk.get(response_key),
                    )

    def _execute_sync(self, run_id: UUID, loop: asyncio.AbstractEventLoop) -> None:
        run = self.store.get_run(run_id)
        if not run:
            return
        self.store.transition(run_id, status="running")
        self._notify(loop)
        states = dict(run.agent_statuses)
        accumulator = RunAccumulator(statuses=states)
        terminal_persisted = False
        try:
            from cli.utils import detect_asset_type
            from tradingagents.graph.analyst_execution import (
                build_analyst_execution_plan,
            )
            from tradingagents.graph.trading_graph import TradingAgentsGraph

            config = self._build_config(run)
            asset_type = detect_asset_type(run.ticker)
            plan = build_analyst_execution_plan(run.analysts)
            accumulator.analyst_steps = tuple(
                (spec.agent_node, spec.report_key, REPORTS[spec.report_key][1])
                for spec in plan.specs
            )
            self._sync_analyst_statuses(loop, run_id, accumulator)
            graph = TradingAgentsGraph(selected_analysts=run.analysts, config=config)
            graph.ticker = run.ticker
            checkpoint_cleanup = None
            if config.get("checkpoint_enabled"):
                checkpoint_cleanup = CheckpointCleanup(
                    run_id=run_id,
                    data_cache_dir=str(config["data_cache_dir"]),
                    ticker=run.ticker,
                    trade_date=str(run.analysis_date),
                    signature=graph._run_signature(asset_type),
                )
                if not self._reconcile_checkpoint_cleanups(checkpoint_cleanup):
                    raise RuntimeError(
                        "A completed checkpoint is still pending cleanup"
                    )
            graph._resolve_pending_entries(run.ticker)
            past_context = graph.memory_log.get_past_context(
                run.ticker, as_of=graph._memory_as_of(run.analysis_date)
            )
            context = graph.resolve_instrument_context(run.ticker, asset_type)
            init = graph.propagator.create_initial_state(
                run.ticker,
                str(run.analysis_date),
                asset_type=asset_type,
                past_context=past_context,
                instrument_context=context,
            )
            args = graph.propagator.get_graph_args()
            try:
                checkpoint = graph.begin_checkpoint(
                    run.ticker, str(run.analysis_date), asset_type
                )
                if checkpoint:
                    args.setdefault("config", {}).setdefault("configurable", {})[
                        "thread_id"
                    ] = checkpoint
                for chunk in graph.graph.stream(graph.checkpoint_input(init), **args):
                    self._consume_chunk(run_id, chunk, accumulator, loop)

                final = accumulator.final_state
                final_decision = final["final_trade_decision"]
                graph.curr_state = final
                safe_final = self._safe_state(final)
                graph._log_state(str(run.analysis_date), safe_final)
                graph.memory_log.store_decision(
                    ticker=run.ticker,
                    trade_date=str(run.analysis_date),
                    final_trade_decision=final_decision,
                )
                signal = self._normalize_signal(graph.process_signal(final_decision))

                # Reconcile every final report independently of the status fields
                # that normally accompany its node. This keeps the adapter robust
                # to a resumed stream's first value or a future delta-mode change.
                for key, (_, title) in REPORTS.items():
                    self._emit_report(
                        loop, run_id, accumulator, key, title, final.get(key)
                    )

                for agent in states:
                    self._set_agent_status(
                        loop, run_id, accumulator, agent, "completed"
                    )
                self._event(
                    loop,
                    run_id,
                    "signal",
                    {"signal": signal},
                    reports=dict(accumulator.reports),
                    agent_statuses=dict(states),
                    signal=signal,
                    final_state=safe_final,
                )

                # Completion is durable before checkpoint deletion. A database
                # failure therefore retains resumable graph state; after this call
                # succeeds, cleanup can no longer turn the run back into failed.
                self.store.complete_run(
                    run_id, checkpoint_cleanup=checkpoint_cleanup
                )
                terminal_persisted = True
                try:
                    self._notify(loop)
                except Exception:  # persisted cursors still make polling/reconnect safe
                    log.exception(
                        "Could not notify listeners for completed run %s", run_id
                    )
            finally:
                graph.end_checkpoint()
            if checkpoint_cleanup is not None:
                self._retry_checkpoint_cleanup(checkpoint_cleanup)
        except Exception as exc:
            if terminal_persisted:
                log.exception("Post-completion cleanup failed for %s", run_id)
                return
            message = f"Analysis failed: {type(exc).__name__}"
            states = {
                agent: "error" if status == "in_progress" else status
                for agent, status in states.items()
            }
            self.store.fail_run(
                run_id,
                error_message=message,
                agent_statuses=states,
            )
            self._notify(loop)

    @staticmethod
    def _normalize_signal(value: Any) -> str:
        signal = str(value).upper()
        if signal not in {
            "BUY",
            "OVERWEIGHT",
            "HOLD",
            "UNDERWEIGHT",
            "SELL",
            "REVIEW",
        }:
            return "REVIEW"
        return signal

    @staticmethod
    def _safe_state(value: dict[str, Any]) -> dict[str, Any]:
        allowed = {key: value[key] for key in REPORTS if key in value}
        for key in (
            "company_of_interest",
            "asset_type",
            "trade_date",
            "investment_debate_state",
            "risk_debate_state",
        ):
            if key in value:
                allowed[key] = json.loads(json.dumps(value[key], default=str))
        return allowed
