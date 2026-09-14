from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import analysis, config, history, ws
from backend.services.runner import AnalysisRunner
from backend.services.store import AnalysisStore
from backend.settings import Settings


def create_app(settings: Settings|None=None,store:AnalysisStore|None=None,runner:AnalysisRunner|None=None) -> FastAPI:
    settings=settings or Settings(); store=store or AnalysisStore(settings.database_path); runner=runner or AnalysisRunner(store)
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        store.initialize(); store.reconcile_interrupted_runs(); await runner.start()
        for run_id in store.list_queued_run_ids(): await runner.enqueue(run_id)
        yield
        await runner.stop()
    app=FastAPI(title="TradingAgents UI",lifespan=lifespan); app.state.store=store; app.state.runner=runner
    app.add_middleware(CORSMiddleware,allow_origins=settings.parsed_cors_origins,allow_origin_regex=settings.parsed_cors_origin_regex,allow_methods=["*"],allow_headers=["*"],allow_credentials=False)
    app.include_router(analysis.router); app.include_router(config.router); app.include_router(history.router); app.include_router(ws.router)
    @app.get("/health")
    def health(): return {"status":"ok"}
    return app
app=create_app()
