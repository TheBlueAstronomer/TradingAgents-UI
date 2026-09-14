---
agent: devin-local
session: plain-text
created: 2026-09-14T08:42:03Z
---
# TradingAgents-UI: Web Interface for TradingAgents Framework

Build a separate Next.js + FastAPI UI project that uses TradingAgents as an untouched git submodule, providing a web-based alternative to the CLI with real-time agent streaming, report viewing, and analysis history.

## Architecture Overview

```
TradingAgents-UI/
├── tradingagents-core/          # Git submodule -> TauricResearch/TradingAgents
├── backend/                     # FastAPI Python server (thin wrapper)
│   ├── main.py                  # FastAPI app entry point
│   ├── api/
│   │   ├── analysis.py          # POST /api/analysis (start run), GET /api/analysis/:id
│   │   ├── config.py            # GET/POST /api/config (LLM providers, defaults)
│   │   ├── history.py           # GET /api/history (past runs)
│   │   └── ws.py                # WebSocket /ws/analysis/:id (live streaming)
│   ├── services/
│   │   ├── runner.py            # Wraps TradingAgentsGraph - imports from submodule
│   │   └── store.py             # SQLite store for analysis runs & results
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                    # Next.js 14 app
│   ├── src/
│   │   ├── app/                 # App router pages
│   │   │   ├── page.tsx         # Dashboard / new analysis
│   │   │   ├── analysis/[id]/   # Live analysis view + report
│   │   │   └── history/         # Past analysis runs
│   │   ├── components/
│   │   │   ├── AnalysisForm.tsx       # Config form (ticker, date, analysts, LLM)
│   │   │   ├── AgentProgress.tsx      # Real-time agent status panel
│   │   │   ├── ReportViewer.tsx       # Markdown report display
│   │   │   ├── AnalysisHistory.tsx    # Table of past runs
│   │   │   └── SignalBadge.tsx        # Buy/Hold/Sell signal display
│   │   ├── hooks/
│   │   │   └── useAnalysisStream.ts   # WebSocket hook for live updates
│   │   └── lib/
│   │       └── api.ts                 # API client functions
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml           # Run both services together
├── .gitmodules                  # Submodule config
├── update-upstream.sh           # Helper script to pull latest TradingAgents
├── .env.example                 # API keys template
└── README.md
```

## How It Works (No Modifications to TradingAgents)

The key insight is that TradingAgents already has a clean Python API:

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = {**DEFAULT_CONFIG, "llm_provider": "openai", ...}
graph = TradingAgentsGraph(selected_analysts=["market", "news"], config=config)
final_state, signal = graph.propagate("AAPL", "2025-01-15")
```

The backend simply imports this from the submodule (added to `PYTHONPATH`). For streaming, it uses `graph.graph.stream()` which yields per-node chunks - the same mechanism the CLI uses for its Rich live display.

## Implementation Steps

### Phase 1: Project Setup & Submodule
1. **Initialize git repo** in `TradingAgents-UI/`
2. **Add TradingAgents as git submodule**: `git submodule add https://github.com/TauricResearch/TradingAgents.git tradingagents-core`
3. **Create `update-upstream.sh`** helper script:
   ```bash
   #!/bin/bash
   git submodule update --remote tradingagents-core
   pip install -e ./tradingagents-core
   echo "Updated to: $(cd tradingagents-core && git log --oneline -1)"
   ```
4. **Create `.env.example`** with required API keys (OPENAI_API_KEY, etc.)

### Phase 2: FastAPI Backend
5. **Create `backend/requirements.txt`** with FastAPI, uvicorn, websockets, sqlite dependencies
6. **Create `backend/services/runner.py`**: Thin wrapper around `TradingAgentsGraph`
   - `start_analysis(ticker, date, analysts, config)` -> spawns background task, returns run_id
   - `stream_analysis(run_id)` -> async generator yielding agent messages via `graph.stream()`
   - No TradingAgents code is modified - just imported and called
7. **Create `backend/services/store.py`**: SQLite-backed storage
   - Store analysis runs (id, ticker, date, status, config, created_at)
   - Store results (reports, signal, final_state JSON)
8. **Create `backend/api/analysis.py`**: REST endpoints
   - `POST /api/analysis` - Start new analysis run
   - `GET /api/analysis/{id}` - Get run status and results
9. **Create `backend/api/ws.py`**: WebSocket endpoint
   - `/ws/analysis/{id}` - Stream real-time agent progress (node transitions, messages, reports as they complete)
10. **Create `backend/api/config.py`**: Configuration endpoints
    - `GET /api/config/providers` - Available LLM providers
    - `GET /api/config/analysts` - Available analyst types
11. **Create `backend/api/history.py`**: History endpoints
    - `GET /api/history` - List past runs with pagination/filtering
12. **Create `backend/main.py`**: FastAPI app with CORS, routers, startup

### Phase 3: Next.js Frontend
13. **Initialize Next.js 14 project** with TypeScript, Tailwind CSS, shadcn/ui
14. **Create `frontend/src/lib/api.ts`**: API client for backend
15. **Create `frontend/src/hooks/useAnalysisStream.ts`**: WebSocket hook
    - Connects to `/ws/analysis/{id}`
    - Returns reactive state: agent statuses, messages, reports, signal
16. **Create `frontend/src/components/AnalysisForm.tsx`**: Config form
    - Ticker input with validation
    - Date picker
    - Analyst team selection (checkboxes: market, social, news, fundamentals)
    - LLM provider selection
    - Research depth (debate rounds)
17. **Create `frontend/src/components/AgentProgress.tsx`**: Live progress
    - Visual agent pipeline (Analysts -> Research -> Trading -> Risk -> PM)
    - Per-agent status indicators (waiting/running/complete)
    - Streaming message feed (like the CLI's Rich panel, but in the browser)
18. **Create `frontend/src/components/ReportViewer.tsx`**: Report display
    - Tabbed view: Market | Sentiment | News | Fundamentals | Investment Plan | Final Decision
    - Markdown rendering with syntax highlighting
19. **Create `frontend/src/components/SignalBadge.tsx`**: Signal display
    - Color-coded badge: Buy (green), Overweight, Hold (yellow), Underweight, Sell (red)
20. **Create `frontend/src/components/AnalysisHistory.tsx`**: History table
    - Sortable/filterable table of past runs
    - Click to view full report
21. **Create pages**:
    - `app/page.tsx` - Dashboard with AnalysisForm + recent runs
    - `app/analysis/[id]/page.tsx` - Live analysis view (progress -> report)
    - `app/history/page.tsx` - Full history browser

### Phase 4: Integration & DevX
22. **Create `docker-compose.yml`** for running both services
23. **Create root `README.md`** with setup instructions
24. **Create `.gitignore`** for the project

## Files to Modify
- None in `tradingagents-core/` (submodule stays untouched)
- All new files in `backend/` and `frontend/`

## Key Design Decisions

### Why FastAPI wrapping TradingAgents (not modifying it)?
- `TradingAgentsGraph` is already a well-structured Python class with `propagate()` and streaming support
- The FastAPI backend just does: `sys.path.insert(0, './tradingagents-core')` then `from tradingagents.graph.trading_graph import TradingAgentsGraph`
- When you update the submodule, the backend automatically uses the new code

### Why WebSocket for streaming?
- TradingAgents analysis takes minutes. The CLI uses `graph.stream()` to show real-time progress
- WebSocket lets us push each agent's output to the browser as it happens
- The WebSocket handler iterates over `graph.stream()` and pushes JSON messages

### Why SQLite for storage?
- TradingAgents already writes JSON logs to disk. We just need a lightweight index for the UI
- No external database to manage - keeps setup simple
- Can be swapped for PostgreSQL later if needed

## Verification
- [ ] `git submodule update --init` pulls TradingAgents successfully
- [ ] `cd tradingagents-core && pip install -e .` installs the package
- [ ] Backend starts: `uvicorn backend.main:app --reload`
- [ ] Frontend starts: `cd frontend && npm run dev`
- [ ] Can submit analysis via the form and see live agent progress
- [ ] Reports render correctly after analysis completes
- [ ] History page shows past runs
- [ ] `update-upstream.sh` pulls latest TradingAgents without breaking the UI

## Risks/Considerations
- **TradingAgents breaking changes**: Upstream may change the `TradingAgentsGraph` API. The submodule pin lets you test before upgrading.
- **Long-running analysis**: Runs take 2-10+ minutes. Need proper background task management (asyncio tasks or a simple queue).
- **API key management**: Keys are shared between the backend's `.env` and TradingAgents' dotenv loading. Single `.env` at project root works.
- **PYTHONPATH setup**: The submodule path must be on Python's path. Handled in backend startup or via pip install -e.
