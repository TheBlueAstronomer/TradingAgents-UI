import re
from datetime import date, datetime, timezone
from typing import Any, Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator, model_validator

AnalystKey = Literal["market", "social", "news", "fundamentals"]
AssetType = Literal["stock", "crypto"]
RunStatus = Literal["queued", "running", "completed", "failed"]
AgentStatus = Literal["pending", "in_progress", "completed", "error"]
Signal = Literal["BUY", "OVERWEIGHT", "HOLD", "UNDERWEIGHT", "SELL", "REVIEW"]
ReportKey = Literal["market_report", "sentiment_report", "news_report", "fundamentals_report", "investment_plan", "trader_investment_plan", "final_trade_decision"]
TICKER_RE = re.compile(r"^[A-Z0-9^][A-Z0-9.^=_-]{0,31}$")

class AnalysisCreate(BaseModel):
    ticker: str
    analysis_date: date
    analysts: list[AnalystKey]
    llm_provider: str
    quick_think_llm: str
    deep_think_llm: str
    research_depth: int = Field(ge=1, le=5)
    backend_url: AnyHttpUrl | None = None

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        value = value.strip().upper()
        if not TICKER_RE.fullmatch(value):
            raise ValueError("Ticker must be 1–32 safe market-symbol characters")
        return value

    @field_validator("analysis_date")
    @classmethod
    def no_future_date(cls, value: date) -> date:
        if value > datetime.now(timezone.utc).date():
            raise ValueError("Analysis date cannot be in the future")
        return value

    @field_validator("analysts")
    @classmethod
    def unique_analysts(cls, value: list[AnalystKey]) -> list[AnalystKey]:
        if not value or len(set(value)) != len(value):
            raise ValueError("Select one or more distinct analysts")
        return value

    @model_validator(mode="after")
    def compatible_backend(self) -> "AnalysisCreate":
        if self.llm_provider == "openai_compatible" and self.backend_url is None:
            raise ValueError("backend_url is required for openai_compatible")
        return self

class AnalysisSummary(BaseModel):
    id: UUID; ticker: str; analysis_date: date; asset_type: AssetType; analysts: list[AnalystKey]
    llm_provider: str; research_depth: int; status: RunStatus; signal: Signal | None
    created_at: datetime; started_at: datetime | None; completed_at: datetime | None

class AnalysisDetail(AnalysisSummary):
    quick_think_llm: str; deep_think_llm: str; reports: dict[ReportKey, str] = {}
    agent_statuses: dict[str, AgentStatus] = {}; error_message: str | None = None
    final_state: dict[str, Any] | None = None; last_event_seq: int = 0

class HistoryPage(BaseModel):
    items: list[AnalysisSummary]; total: int; page: int; page_size: int
class ModelOption(BaseModel): label: str; value: str
class ProviderOption(BaseModel):
    id: str; label: str; quick_models: list[ModelOption]; deep_models: list[ModelOption]
    allows_custom_model: bool; requires_backend_url: bool; default_quick_model: str; default_deep_model: str
class AnalystOption(BaseModel):
    id: AnalystKey; label: str; description: str; selected_by_default: bool
class ApiErrorDetail(BaseModel): code: str; message: str; field: str | None = None
class ApiError(BaseModel): detail: ApiErrorDetail
class StreamEvent(BaseModel):
    run_id: UUID; seq: int; emitted_at: datetime
    type: Literal["snapshot", "status", "agent_status", "message", "tool_call", "report", "signal", "complete", "error"]
    data: dict[str, Any]
