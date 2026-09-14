import asyncio
import json
import sys
import threading
from datetime import UTC, datetime
from types import ModuleType, SimpleNamespace
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, ChatMessage, HumanMessage, ToolMessage

from backend.models import AnalysisCreate
from backend.services.runner import AnalysisRunner, RunAccumulator
from backend.services.store import CheckpointCleanup


def request(analysts: list[str] | None = None) -> AnalysisCreate:
    return AnalysisCreate(
        ticker="AAPL",
        analysis_date=datetime.now(UTC).date(),
        analysts=analysts or ["market"],
        llm_provider="openai",
        quick_think_llm="gpt-5.6-luna",
        deep_think_llm="gpt-5.6",
        research_depth=2,
    )


def install_fake_upstream(
    monkeypatch,
    chunks,
    *,
    failure: str | None = None,
    resume: bool = False,
):
    calls: list[tuple] = []
    checkpoint_state = {"step": 99, "fail_clear": failure == "clear"}
    holder: dict[str, object] = {"checkpoint_state": checkpoint_state}

    def fail_at(stage: str) -> None:
        if failure == stage:
            raise RuntimeError(f"{stage} secret=do-not-leak")

    class MemoryLog:
        def get_past_context(self, ticker, *, as_of=None):
            calls.append(("past_context", ticker, as_of))
            return "prior decision context"

        def store_decision(self, **kwargs):
            calls.append(("memory", kwargs))
            fail_at("memory")

    class Graph:
        def __init__(self, **kwargs):
            calls.append(("init", kwargs))
            holder["graph"] = self
            self.curr_state = None
            self.ticker = None
            self.memory_log = MemoryLog()
            self.propagator = SimpleNamespace(
                create_initial_state=self.create_initial_state,
                get_graph_args=self.get_graph_args,
            )
            self.graph = SimpleNamespace(stream=self.stream)

        def _resolve_pending_entries(self, ticker):
            calls.append(("resolve_pending", ticker))

        def _memory_as_of(self, trade_date):
            calls.append(("memory_as_of", str(trade_date)))
            return str(trade_date)

        def create_initial_state(self, *args, **kwargs):
            calls.append(("initial_state", args, kwargs))
            return {"seed": 1}

        def get_graph_args(self):
            calls.append(("graph_args",))
            return {"config": {"recursion_limit": 100}}

        def stream(self, graph_input, **kwargs):
            calls.append(("stream", graph_input, kwargs))
            yield from chunks
            fail_at("stream")

        def resolve_instrument_context(self, *args):
            calls.append(("instrument_context", args))
            return "AAPL — Apple Inc."

        def begin_checkpoint(self, *args):
            calls.append(("begin", args))
            fail_at("begin")
            return "checkpoint-thread"

        def checkpoint_input(self, state):
            calls.append(("checkpoint_input", state))
            return None if resume else state

        def end_checkpoint(self):
            calls.append(("end",))

        def _run_signature(self, asset_type):
            calls.append(("signature", asset_type))
            return f"analysts=market|asset={asset_type}"

        def _log_state(self, trade_date, state):
            calls.append(("log", trade_date, state))
            json.dumps(state)
            fail_at("log")

        def process_signal(self, decision):
            calls.append(("signal", decision))
            fail_at("signal")
            return "Buy"

    defaults = ModuleType("tradingagents.default_config")
    defaults.DEFAULT_CONFIG = {
        "from_default": True,
        "checkpoint_enabled": True,
        "data_cache_dir": "/fake/cache",
    }
    analyst_execution = ModuleType("tradingagents.graph.analyst_execution")
    analyst_specs = {
        "market": ("Market Analyst", "market_report"),
        "social": ("Sentiment Analyst", "sentiment_report"),
        "news": ("News Analyst", "news_report"),
        "fundamentals": ("Fundamentals Analyst", "fundamentals_report"),
    }
    analyst_execution.build_analyst_execution_plan = lambda selected: SimpleNamespace(
        specs=[
            SimpleNamespace(
                key=key,
                agent_node=analyst_specs[key][0],
                report_key=analyst_specs[key][1],
            )
            for key in selected
        ]
    )
    graph_module = ModuleType("tradingagents.graph.trading_graph")
    graph_module.TradingAgentsGraph = Graph
    checkpointer_module = ModuleType("tradingagents.graph.checkpointer")

    def clear_checkpoint(*args):
        calls.append(("clear", args))
        if checkpoint_state["fail_clear"]:
            raise RuntimeError("clear checkpoint unavailable")
        checkpoint_state["step"] = None

    def checkpoint_step(*args):
        calls.append(("checkpoint_step", args))
        return checkpoint_state["step"]

    checkpointer_module.clear_checkpoint = clear_checkpoint
    checkpointer_module.checkpoint_step = checkpoint_step
    cli_utils = ModuleType("cli.utils")
    cli_utils.detect_asset_type = lambda _: "stock"
    monkeypatch.setitem(sys.modules, "tradingagents.default_config", defaults)
    monkeypatch.setitem(
        sys.modules, "tradingagents.graph.analyst_execution", analyst_execution
    )
    monkeypatch.setitem(sys.modules, "tradingagents.graph.trading_graph", graph_module)
    monkeypatch.setitem(
        sys.modules, "tradingagents.graph.checkpointer", checkpointer_module
    )
    monkeypatch.setitem(sys.modules, "cli.utils", cli_utils)
    return calls, holder


def execute(store, monkeypatch, chunks, **fake_options):
    calls, holder = install_fake_upstream(monkeypatch, chunks, **fake_options)
    run = store.create_run(request(), "stock")
    complete_run = store.complete_run

    def complete_with_trace(run_id, **kwargs):
        calls.append(("complete", run_id, kwargs))
        return complete_run(run_id, **kwargs)

    monkeypatch.setattr(store, "complete_run", complete_with_trace)
    finish_cleanup = store.finish_checkpoint_cleanup

    def finish_with_trace(run_id):
        calls.append(("finish_cleanup", run_id))
        return finish_cleanup(run_id)

    monkeypatch.setattr(store, "finish_checkpoint_cleanup", finish_with_trace)
    runner = AnalysisRunner(store)
    monkeypatch.setattr(runner, "_notify", lambda _: None)
    loop = asyncio.new_event_loop()
    runner._execute_sync(run.id, loop)
    loop.close()
    return run, calls, holder


def test_fake_graph_stream_mirrors_bookkeeping_and_checkpoint_order(
    store, monkeypatch
):
    message = SimpleNamespace(
        id="same",
        content={"text": "safe message"},
        tool_calls=[{"name": "lookup", "args": {"x": {1, 2}}}],
    )
    raw_marker = SimpleNamespace(label="not-json")
    chunks = [
        {
            "messages": [message, message],
            "market_report": "Market",
            "company_of_interest": "AAPL",
            "trade_date": "2026-09-14",
            "investment_debate_state": {"custom": raw_marker},
            "risk_debate_state": {},
            "final_trade_decision": "**Rating**: Buy",
        }
    ]
    run, calls, holder = execute(store, monkeypatch, chunks, resume=True)

    finished = store.get_run(run.id)
    events = store.events_after(run.id, 0)
    graph = holder["graph"]
    names = [call[0] for call in calls]

    assert finished.status == "completed" and finished.signal == "BUY"
    assert [event.seq for event in events] == list(range(1, len(events) + 1))
    assert [event.type for event in events].count("message") == 1
    assert finished.reports["market_report"] == "Market"
    assert graph.ticker == "AAPL"
    assert graph.curr_state is not None
    assert graph.curr_state["messages"][0] is message

    initial_call = next(call for call in calls if call[0] == "initial_state")
    assert initial_call[2]["past_context"] == "prior decision context"
    stream_call = next(call for call in calls if call[0] == "stream")
    assert stream_call[1] is None
    assert stream_call[2]["config"]["configurable"]["thread_id"] == (
        "checkpoint-thread"
    )

    logged = next(call for call in calls if call[0] == "log")[2]
    assert "messages" not in logged
    assert logged["investment_debate_state"]["custom"] == (
        "namespace(label='not-json')"
    )
    assert next(call for call in calls if call[0] == "memory")[1] == {
        "ticker": "AAPL",
        "trade_date": str(run.analysis_date),
        "final_trade_decision": "**Rating**: Buy",
    }
    assert names.index("log") < names.index("memory") < names.index("signal")
    assert names.index("signal") < names.index("complete") < names.index("end")
    assert names.index("end") < names.index("clear") < names.index("checkpoint_step")
    assert names.index("checkpoint_step") < names.index("finish_cleanup")
    marker = next(call for call in calls if call[0] == "complete")[2][
        "checkpoint_cleanup"
    ]
    assert marker.run_id == run.id
    assert marker.data_cache_dir == "/fake/cache"
    assert marker.ticker == "AAPL"
    assert marker.trade_date == str(run.analysis_date)
    assert marker.signature == "analysts=market|asset=stock"
    assert store.list_checkpoint_cleanups() == []
    assert events[-1].type == "complete"
    assert events[-1].data["run"]["last_event_seq"] == events[-1].seq


def test_runner_emits_exact_pipeline_and_distinct_debate_progress(
    store, monkeypatch
):
    research_bull = {
        "count": 1,
        "current_response": "Bull Analyst: upside",
        "bull_history": "Bull Analyst: upside",
        "bear_history": "",
        "judge_decision": "",
    }
    research_bear = {
        "count": 2,
        "current_response": "Bear Analyst: downside",
        "bull_history": "Bull Analyst: upside",
        "bear_history": "Bear Analyst: downside",
        "judge_decision": "",
    }
    research_judge = {
        **research_bear,
        "current_response": "Research decision",
        "judge_decision": "Research decision",
    }
    risk_aggressive = {
        "count": 1,
        "latest_speaker": "Aggressive",
        "current_aggressive_response": "Aggressive Analyst: upside",
        "current_conservative_response": "",
        "current_neutral_response": "",
        "aggressive_history": "Aggressive Analyst: upside",
        "conservative_history": "",
        "neutral_history": "",
        "judge_decision": "",
    }
    risk_conservative = {
        **risk_aggressive,
        "count": 2,
        "latest_speaker": "Conservative",
        "current_conservative_response": "Conservative Analyst: caution",
        "conservative_history": "Conservative Analyst: caution",
    }
    risk_neutral = {
        **risk_conservative,
        "count": 3,
        "latest_speaker": "Neutral",
        "current_neutral_response": "Neutral Analyst: balance",
        "neutral_history": "Neutral Analyst: balance",
    }
    risk_judge = {
        **risk_neutral,
        "latest_speaker": "Judge",
        "judge_decision": "**Rating**: Hold",
    }
    chunks = [
        {"market_report": "Market"},
        {"news_report": "News"},
        {"investment_debate_state": research_bull},
        {"investment_debate_state": research_bull},
        {"investment_debate_state": research_bear},
        {
            "investment_debate_state": research_judge,
            "investment_plan": "Research decision",
        },
        {"trader_investment_plan": "Trading plan"},
        {"risk_debate_state": risk_aggressive},
        {"risk_debate_state": risk_conservative},
        {"risk_debate_state": risk_neutral},
        {
            "risk_debate_state": risk_judge,
            "final_trade_decision": "**Rating**: Hold",
        },
        {
            "investment_debate_state": research_judge,
            "investment_plan": "Research decision",
            "trader_investment_plan": "Trading plan",
            "risk_debate_state": risk_judge,
            "final_trade_decision": "**Rating**: Hold",
        },
    ]
    calls, _ = install_fake_upstream(monkeypatch, chunks)
    run = store.create_run(request(["market", "news"]), "stock")
    runner = AnalysisRunner(store)
    monkeypatch.setattr(runner, "_notify", lambda _: None)
    loop = asyncio.new_event_loop()
    runner._execute_sync(run.id, loop)
    loop.close()

    events = store.events_after(run.id, 0)
    transitions = [
        (event.data["agent"], event.data["status"])
        for event in events
        if event.type == "agent_status"
    ]
    assert transitions == [
        ("Market Analyst", "in_progress"),
        ("Market Analyst", "completed"),
        ("News Analyst", "in_progress"),
        ("News Analyst", "completed"),
        ("Bull Researcher", "in_progress"),
        ("Bear Researcher", "in_progress"),
        ("Research Manager", "in_progress"),
        ("Bull Researcher", "completed"),
        ("Bear Researcher", "completed"),
        ("Research Manager", "completed"),
        ("Trader", "in_progress"),
        ("Trader", "completed"),
        ("Aggressive Analyst", "in_progress"),
        ("Conservative Analyst", "in_progress"),
        ("Neutral Analyst", "in_progress"),
        ("Portfolio Manager", "in_progress"),
        ("Aggressive Analyst", "completed"),
        ("Conservative Analyst", "completed"),
        ("Neutral Analyst", "completed"),
        ("Portfolio Manager", "completed"),
    ]
    debate = [
        event
        for event in events
        if event.type == "message" and event.data.get("stage")
    ]
    assert [event.data["source"] for event in debate] == [
        "Bull Researcher",
        "Bear Researcher",
        "Aggressive Analyst",
        "Conservative Analyst",
        "Neutral Analyst",
    ]
    assert len({event.data["messageId"] for event in debate}) == len(debate)
    status_events = [event for event in events if event.type == "agent_status"]
    for message_event in debate:
        source = message_event.data["source"]
        assert any(
            status_event.seq < message_event.seq
            and status_event.data == {
                "agent": source,
                "team": status_event.data["team"],
                "status": "in_progress",
            }
            for status_event in status_events
        )
        digest = message_event.data["messageId"].rsplit(":", 1)[-1]
        assert len(digest) == 16
        int(digest, 16)
    reports = [event.data["key"] for event in events if event.type == "report"]
    assert reports == [
        "market_report",
        "news_report",
        "investment_plan",
        "trader_investment_plan",
        "final_trade_decision",
    ]
    assert store.get_run(run.id).reports["investment_plan"] == "Research decision"
    assert [call[0] for call in calls].count("clear") == 1


@pytest.mark.parametrize("failure", ["begin", "stream", "log", "memory", "signal"])
def test_failure_retains_checkpoint_and_always_ends(store, monkeypatch, failure):
    chunks = [
        {
            "market_report": "Market",
            "final_trade_decision": "**Rating**: Buy",
        }
    ]
    run, calls, _ = execute(store, monkeypatch, chunks, failure=failure)
    finished = store.get_run(run.id)
    errors = [
        event for event in store.events_after(run.id, 0) if event.type == "error"
    ]
    names = [call[0] for call in calls]

    assert finished.status == "failed"
    assert "do-not-leak" not in finished.error_message
    assert errors[-1].data["code"] == "ANALYSIS_FAILED"
    assert "end" in names
    assert "clear" not in names
    assert "error" in finished.agent_statuses.values()


def test_missing_final_decision_is_failure_not_review(store, monkeypatch):
    run, calls, _ = execute(
        store, monkeypatch, [{"market_report": "Market without final decision"}]
    )
    finished = store.get_run(run.id)
    names = [call[0] for call in calls]

    assert finished.status == "failed"
    assert finished.signal is None
    assert "signal" not in names and "clear" not in names
    assert "end" in names


def test_complete_persistence_failure_retains_checkpoint(store, monkeypatch):
    calls, _ = install_fake_upstream(
        monkeypatch,
        [{"market_report": "Market", "final_trade_decision": "**Rating**: Buy"}],
    )
    run = store.create_run(request(), "stock")

    def fail_completion(_run_id, **_kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(store, "complete_run", fail_completion)
    runner = AnalysisRunner(store)
    monkeypatch.setattr(runner, "_notify", lambda _: None)
    loop = asyncio.new_event_loop()
    runner._execute_sync(run.id, loop)
    loop.close()

    names = [call[0] for call in calls]
    finished = store.get_run(run.id)
    assert finished.status == "failed"
    assert "clear" not in names
    assert "end" in names
    assert not any(status == "error" for status in finished.agent_statuses.values())


def test_checkpoint_clear_failure_does_not_regress_durable_completion(
    store, monkeypatch, caplog
):
    run, calls, holder = execute(
        store,
        monkeypatch,
        [{"market_report": "Market", "final_trade_decision": "**Rating**: Buy"}],
        failure="clear",
    )
    events = store.events_after(run.id, 0)
    names = [call[0] for call in calls]

    assert store.get_run(run.id).status == "completed"
    assert names.index("complete") < names.index("end") < names.index("clear")
    assert names.count("clear") == 3
    assert events[-1].type == "complete"
    assert not any(event.type == "error" for event in events)
    assert len(store.list_checkpoint_cleanups()) == 1
    assert "Checkpoint cleanup remains pending" in caplog.text

    holder["checkpoint_state"]["fail_clear"] = False
    recovery = AnalysisRunner(store)
    assert recovery._reconcile_checkpoint_cleanups()
    assert store.list_checkpoint_cleanups() == []


def test_failure_marks_all_and_only_in_progress_agents_error(store, monkeypatch):
    chunks = [
        {"market_report": "Market"},
        {
            "investment_debate_state": {
                "count": 1,
                "current_response": "Bull Analyst: upside",
                "bull_history": "Bull Analyst: upside",
                "bear_history": "",
                "judge_decision": "",
            }
        },
    ]
    run, _, _ = execute(store, monkeypatch, chunks, failure="stream")
    statuses = store.get_run(run.id).agent_statuses

    assert statuses["Market Analyst"] == "completed"
    assert {
        agent for agent, status in statuses.items() if status == "error"
    } == {"Bull Researcher", "Bear Researcher", "Research Manager"}
    assert statuses["Trader"] == "pending"
    assert statuses["Aggressive Analyst"] == "pending"


def test_post_run_failure_never_regresses_completed_agents(store, monkeypatch):
    chunks = [
        {
            "market_report": "Market",
            "investment_debate_state": {
                "count": 2,
                "current_response": "Research decision",
                "bull_history": "Bull Analyst: upside",
                "bear_history": "Bear Analyst: downside",
                "judge_decision": "Research decision",
            },
            "investment_plan": "Research decision",
            "trader_investment_plan": "Trading plan",
            "risk_debate_state": {
                "count": 3,
                "latest_speaker": "Judge",
                "aggressive_history": "Aggressive Analyst: upside",
                "conservative_history": "Conservative Analyst: caution",
                "neutral_history": "Neutral Analyst: balance",
                "judge_decision": "**Rating**: Hold",
            },
            "final_trade_decision": "**Rating**: Hold",
        }
    ]
    run, calls, _ = execute(store, monkeypatch, chunks, failure="log")
    statuses = store.get_run(run.id).agent_statuses

    assert store.get_run(run.id).status == "failed"
    assert set(statuses.values()) == {"completed"}
    assert "clear" not in [call[0] for call in calls]


def test_consume_chunk_bounds_and_json_safely_projects_messages_and_tools(
    store, monkeypatch
):
    run = store.create_run(request(), "stock")
    runner = AnalysisRunner(store)
    monkeypatch.setattr(runner, "_notify", lambda _: None)
    oversized = SimpleNamespace(
        id="large",
        content="x" * 9000,
        tool_calls=[{"name": "tool", "args": {"payload": "y" * 4000}}],
    )
    loop = asyncio.new_event_loop()
    runner._consume_chunk(run.id, {"messages": [oversized]}, RunAccumulator(), loop)
    loop.close()
    events = store.events_after(run.id, 0)
    assert events[-2].data["content"] == "x" * 8192
    assert len(str(events[-1].data["arguments"])) <= 2048


def test_real_langchain_messages_match_cli_classification_and_extraction(
    store, monkeypatch
):
    run = store.create_run(request(), "stock")
    runner = AnalysisRunner(store)
    monkeypatch.setattr(runner, "_notify", lambda _: None)
    messages = [
        HumanMessage(id="user", content="  inspect AAPL  "),
        HumanMessage(id="control", content=" Continue "),
        ToolMessage(
            id="data",
            content=[{"type": "text", "text": "  market data  "}],
            tool_call_id="call-1",
        ),
        AIMessage(
            id="agent",
            content=[{"type": "text", "text": "agent finding"}, " tail "],
        ),
        ChatMessage(id="system", role="critic", content="fallback note"),
        AIMessage(id="bounded", content="x" * 9000),
    ]
    loop = asyncio.new_event_loop()
    runner._consume_chunk(run.id, {"messages": messages}, RunAccumulator(), loop)
    loop.close()

    projected = [
        event.data
        for event in store.events_after(run.id, 0)
        if event.type == "message"
    ]
    assert [(item["category"], item["content"]) for item in projected[:-1]] == [
        ("User", "inspect AAPL"),
        ("Control", "Continue"),
        ("Data", "market data"),
        ("Agent", "agent finding tail"),
        ("System", "fallback note"),
    ]
    assert projected[-1]["category"] == "Agent"
    assert projected[-1]["content"] == "x" * 8192
    assert AnalysisRunner._extract_content_string({"text": " dict text "}) == (
        "dict text"
    )
    assert AnalysisRunner._extract_content_string(
        [{"type": "text", "text": "first"}, " second ", {"ignored": True}]
    ) == "first second"
    assert AnalysisRunner._extract_content_string("[]") is None


def test_debate_activity_is_distinct_and_bounded(store, monkeypatch):
    run = store.create_run(request(), "stock")
    runner = AnalysisRunner(store)
    monkeypatch.setattr(runner, "_notify", lambda _: None)
    state = RunAccumulator(
        statuses=dict(run.agent_statuses),
        analyst_steps=(("Market Analyst", "market_report", "Market analysis"),),
    )
    response = "Bull Analyst: " + "x" * 9000
    chunk = {
        "investment_debate_state": {
            "count": 1,
            "current_response": response,
            "bull_history": response,
            "bear_history": "",
            "judge_decision": "",
        }
    }
    loop = asyncio.new_event_loop()
    runner._consume_chunk(run.id, chunk, state, loop)
    runner._consume_chunk(run.id, chunk, state, loop)
    loop.close()

    debate = [
        event
        for event in store.events_after(run.id, 0)
        if event.type == "message" and event.data.get("stage") == "Research debate"
    ]
    assert len(debate) == 1
    assert len(debate[0].data["content"]) == 8192


def test_cumulative_debate_state_orders_status_before_activity_and_skips_judge(
    store, monkeypatch
):
    run = store.create_run(request(), "stock")
    runner = AnalysisRunner(store)
    monkeypatch.setattr(runner, "_notify", lambda _: None)
    state = RunAccumulator(statuses=dict(run.agent_statuses))
    research = {
        "count": 2,
        "current_response": "Bear Analyst: cumulative downside",
        "bull_history": "Bull Analyst: cumulative upside",
        "bear_history": "Bear Analyst: cumulative downside",
        "judge_decision": "",
    }
    risk = {
        "count": 3,
        "latest_speaker": "Neutral",
        "current_aggressive_response": "Aggressive Analyst: upside",
        "current_conservative_response": "Conservative Analyst: caution",
        "current_neutral_response": "Neutral Analyst: balance",
        "aggressive_history": "Aggressive Analyst: upside",
        "conservative_history": "Conservative Analyst: caution",
        "neutral_history": "Neutral Analyst: balance",
        "judge_decision": "",
    }
    loop = asyncio.new_event_loop()
    runner._consume_chunk(run.id, {"investment_debate_state": research}, state, loop)
    runner._consume_chunk(run.id, {"investment_debate_state": research}, state, loop)
    revised = {**research, "current_response": "Bear Analyst: revised downside"}
    runner._consume_chunk(run.id, {"investment_debate_state": revised}, state, loop)
    runner._consume_chunk(run.id, {"risk_debate_state": risk}, state, loop)
    judge = {
        **research,
        "current_response": "Bull Analyst: must not be projected",
        "judge_decision": "Research judgment",
    }
    runner._consume_chunk(
        run.id,
        {"investment_debate_state": judge, "investment_plan": "Research judgment"},
        state,
        loop,
    )
    loop.close()

    events = store.events_after(run.id, 0)
    debate = [
        event
        for event in events
        if event.type == "message" and event.data.get("stage")
    ]
    assert [event.data["source"] for event in debate] == [
        "Bear Researcher",
        "Bear Researcher",
        "Neutral Analyst",
    ]
    assert "must not be projected" not in " ".join(
        event.data["content"] for event in debate
    )
    assert len({event.data["messageId"] for event in debate}) == 3

    research_message = debate[0]
    for agent in ("Bull Researcher", "Bear Researcher", "Research Manager"):
        assert any(
            event.type == "agent_status"
            and event.data["agent"] == agent
            and event.data["status"] == "in_progress"
            and event.seq < research_message.seq
            for event in events
        )
    risk_message = debate[-1]
    for agent in ("Aggressive Analyst", "Conservative Analyst", "Neutral Analyst"):
        assert any(
            event.type == "agent_status"
            and event.data["agent"] == agent
            and event.data["status"] == "in_progress"
            and event.seq < risk_message.seq
            for event in events
        )


def test_resumed_final_value_preserves_active_steps_before_team_completion(
    store, monkeypatch
):
    run = store.create_run(request(), "stock")
    runner = AnalysisRunner(store)
    monkeypatch.setattr(runner, "_notify", lambda _: None)
    state = RunAccumulator(
        statuses=dict(run.agent_statuses),
        analyst_steps=(("Market Analyst", "market_report", "Market analysis"),),
    )
    chunk = {
        "market_report": "Market",
        "investment_debate_state": {
            "count": 2,
            "current_response": "Research judgment",
            "bull_history": "Bull Analyst: upside",
            "bear_history": "Bear Analyst: downside",
            "judge_decision": "Research judgment",
        },
        "investment_plan": "Research judgment",
        "trader_investment_plan": "Trading plan",
        "risk_debate_state": {
            "count": 3,
            "latest_speaker": "Judge",
            "aggressive_history": "Aggressive Analyst: upside",
            "conservative_history": "Conservative Analyst: caution",
            "neutral_history": "Neutral Analyst: balance",
            "judge_decision": "Portfolio judgment",
        },
        "final_trade_decision": "Portfolio judgment",
    }

    loop = asyncio.new_event_loop()
    runner._consume_chunk(run.id, chunk, state, loop)
    loop.close()

    transitions = [
        (event.data["agent"], event.data["status"])
        for event in store.events_after(run.id, 0)
        if event.type == "agent_status"
    ]
    for agent in (
        "Bull Researcher",
        "Bear Researcher",
        "Research Manager",
        "Aggressive Analyst",
        "Conservative Analyst",
        "Neutral Analyst",
        "Portfolio Manager",
    ):
        assert (agent, "in_progress") in transitions
        assert (agent, "completed") in transitions
        assert transitions.index((agent, "in_progress")) < transitions.index(
            (agent, "completed")
        )


@pytest.mark.asyncio
async def test_wait_for_events_closes_check_subscribe_interleaving(
    store, monkeypatch
):
    run = store.create_run(request(), "stock")
    runner = AnalysisRunner(store)
    loop = asyncio.get_running_loop()
    checked = threading.Event()
    publish_done = threading.Event()
    original_get_run = store.get_run

    def paused_get_run(run_id):
        stale_snapshot = original_get_run(run_id)
        checked.set()
        assert publish_done.wait(timeout=1)
        return stale_snapshot

    monkeypatch.setattr(store, "get_run", paused_get_run)

    def publish_between_check_and_wait():
        assert checked.wait(timeout=1)
        store.record_event(run.id, "message", {"content": "committed in gap"})
        runner._notify(loop)
        publish_done.set()

    publisher = threading.Thread(target=publish_between_check_and_wait)
    publisher.start()
    try:
        await asyncio.wait_for(
            runner.wait_for_events(run.id, after=run.last_event_seq, timeout=1),
            timeout=0.5,
        )
    finally:
        publish_done.set()
        publisher.join(timeout=1)
    assert not publisher.is_alive()


@pytest.mark.asyncio
async def test_start_reconciles_crash_marker_before_worker(store, monkeypatch):
    calls, _ = install_fake_upstream(monkeypatch, [])
    completed = store.create_run(request(), "stock")
    marker = CheckpointCleanup(
        run_id=completed.id,
        data_cache_dir="/fake/cache",
        ticker="AAPL",
        trade_date=str(completed.analysis_date),
        signature="analysts=market|asset=stock",
    )
    store.complete_run(completed.id, checkpoint_cleanup=marker)
    runner = AnalysisRunner(store)
    worker_release = asyncio.Event()

    async def observed_worker():
        calls.append(("worker_started",))
        await worker_release.wait()

    monkeypatch.setattr(runner, "_worker_loop", observed_worker)
    await runner.start()
    await asyncio.sleep(0)
    try:
        names = [call[0] for call in calls]
        assert names.index("clear") < names.index("checkpoint_step")
        assert names.index("checkpoint_step") < names.index("worker_started")
        assert store.list_checkpoint_cleanups() == []
    finally:
        worker_release.set()
        await runner.stop()


def test_matching_stale_end_marker_blocks_stream_when_cleanup_remains(
    store, monkeypatch
):
    calls, _ = install_fake_upstream(monkeypatch, [], failure="clear")
    completed = store.create_run(request(), "stock")
    marker = CheckpointCleanup(
        run_id=completed.id,
        data_cache_dir="/fake/cache",
        ticker="AAPL",
        trade_date=str(completed.analysis_date),
        signature="analysts=market|asset=stock",
    )
    store.complete_run(completed.id, checkpoint_cleanup=marker)
    queued = store.create_run(request(), "stock")
    runner = AnalysisRunner(store)
    monkeypatch.setattr(runner, "_notify", lambda _: None)
    loop = asyncio.new_event_loop()
    runner._execute_sync(queued.id, loop)
    loop.close()

    names = [call[0] for call in calls]
    assert store.get_run(queued.id).status == "failed"
    assert "begin" not in names
    assert "stream" not in names
    pending = store.list_checkpoint_cleanups()
    assert [cleanup.run_id for cleanup in pending] == [completed.id]
    assert names.count("clear") == 3


@pytest.mark.asyncio
async def test_worker_executes_fifo_without_overlap(store, monkeypatch):
    runner = AnalysisRunner(store)
    first_id, second_id = uuid4(), uuid4()
    first_started = threading.Event()
    release_first = threading.Event()
    lock = threading.Lock()
    order = []
    active = 0
    max_active = 0

    def fake_execute(run_id, _loop):
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
            order.append(run_id)
        try:
            if run_id == first_id:
                first_started.set()
                assert release_first.wait(timeout=1)
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(runner, "_execute_sync", fake_execute)
    await runner.start()
    try:
        await runner.enqueue(first_id)
        await runner.enqueue(second_id)
        assert await asyncio.to_thread(first_started.wait, 1)
        await asyncio.sleep(0.02)
        assert order == [first_id]
        release_first.set()
        await asyncio.wait_for(runner.queue.join(), timeout=1)
    finally:
        release_first.set()
        await runner.stop()

    assert order == [first_id, second_id]
    assert max_active == 1
