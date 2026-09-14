from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from backend.models import AnalysisCreate, AnalysisDetail, AnalysisSummary
from backend.services.store import AnalysisStore

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


def store(request: Request) -> AnalysisStore:
    return request.app.state.store


def invalid_model(field: str) -> HTTPException:
    return HTTPException(
        422,
        {
            "code": "INVALID_MODEL",
            "message": "Model is incompatible with provider",
            "field": field,
        },
    )


def validate_catalog(input: AnalysisCreate) -> None:
    from tradingagents.llm_clients.model_catalog import MODEL_OPTIONS

    options = MODEL_OPTIONS.get(input.llm_provider.lower())
    if not options:
        raise HTTPException(
            422,
            {
                "code": "INVALID_PROVIDER",
                "message": "Unknown LLM provider",
                "field": "llm_provider",
            },
        )
    for field, mode in (("quick_think_llm", "quick"), ("deep_think_llm", "deep")):
        value = getattr(input, field)
        known = {item[1] for item in options[mode]}
        # `custom` is a UI choice, never a valid upstream model identifier.
        # Whitespace is rejected instead of silently altering a selected ID.
        if value != value.strip() or value == "custom":
            raise invalid_model(field)
        if value in known:
            continue
        if "custom" not in known or not value or len(value) > 128:
            raise invalid_model(field)
    if input.llm_provider == "openai_compatible" and input.backend_url is None:
        raise HTTPException(
            422,
            {
                "code": "BACKEND_URL_REQUIRED",
                "message": "Backend URL is required",
                "field": "backend_url",
            },
        )


@router.post("", response_model=AnalysisSummary, status_code=status.HTTP_202_ACCEPTED)
async def create(input: AnalysisCreate, request: Request) -> AnalysisSummary:
    validate_catalog(input)
    from cli.utils import detect_asset_type

    run = store(request).create_run(input, detect_asset_type(input.ticker))
    await request.app.state.runner.enqueue(run.id)
    return AnalysisStore._summary(run)


@router.get("/{run_id}", response_model=AnalysisDetail)
def get(run_id: UUID, request: Request) -> AnalysisDetail:
    run = store(request).get_run(run_id)
    if not run:
        raise HTTPException(
            404, {"code": "RUN_NOT_FOUND", "message": "Analysis run was not found"}
        )
    return run
