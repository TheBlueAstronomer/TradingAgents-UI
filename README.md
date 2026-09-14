# TradingAgents UI

A local browser interface for [TradingAgents](https://github.com/TauricResearch/TradingAgents). The upstream Python project is kept unchanged in the `tradingagents-core` Git submodule, while this repository provides the FastAPI backend and Next.js frontend.

## Prerequisites

- Git with submodule support
- Python 3.10 or newer (Python 3.12 is recommended)
- Node.js 20 or newer with npm
- An API key for the LLM provider you plan to use
- Docker with Docker Compose, if you prefer the container workflow

## First-time setup

Clone the repository with its TradingAgents submodule:

```bash
git clone --recurse-submodules <repository-url>
cd TradingAgents-UI
```

If you already cloned the repository without submodules, initialize it with:

```bash
git submodule update --init --recursive
```

Create and activate a virtual environment, then install the backend, upstream package, and frontend dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ./tradingagents-core
python -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt
npm --prefix frontend ci
```

On Windows, activate the virtual environment with `.venv\Scripts\activate` instead.

## Configure the environment

Create the local environment file:

```bash
cp .env.example .env
```

Before running either workflow, set `DATABASE_PATH`, `CORS_ORIGINS`, and the API key for your selected LLM provider. Do not leave the first two values blank; the following settings work for local development and Docker Compose:

```dotenv
DATABASE_PATH=./data/tradingagents.sqlite3
CORS_ORIGINS=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
OPENAI_API_KEY=your-key-here
```

Use the provider-specific key from `.env.example` instead of `OPENAI_API_KEY` when applicable. Add optional market-data credentials only for the data sources you use. Keep `.env` local; it is ignored by Git and credentials are read only by the backend.

The frontend already defaults to the local backend. If you need different browser-facing endpoints outside Docker, place the `NEXT_PUBLIC_*` values in `frontend/.env.local` before starting Next.js.

## Run locally

Start the backend from the repository root in one terminal:

```bash
source .venv/bin/activate
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Start the frontend in a second terminal:

```bash
npm --prefix frontend run dev
```

Open [http://localhost:3000](http://localhost:3000). The backend health check is available at [http://localhost:8000/health](http://localhost:8000/health), and its API documentation is at [http://localhost:8000/docs](http://localhost:8000/docs).

Press `Ctrl+C` in each terminal to stop the services.

## Run with Docker Compose

Initialize the submodule and create `.env` before building:

```bash
git submodule update --init --recursive
cp .env.example .env
# Edit .env and add the credentials you need.
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000). Application history is persisted in `./data/tradingagents.sqlite3` on the host.

Stop the stack with:

```bash
docker compose down
```

## Verify the installation

With the virtual environment active, run the automated checks from the repository root:

```bash
python -m pytest backend/tests -q
python -m ruff check backend
npm --prefix frontend run test
npm --prefix frontend run lint
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

## Keep TradingAgents up to date

`tradingagents-core` is a Git submodule, so this repository records an exact upstream commit. Updates are deliberate: advance the submodule, test the UI against it, and then commit the new submodule pointer.

The included helper performs the update, reinstalls the editable Python package, and prints the selected upstream commit:

```bash
source .venv/bin/activate
./update-upstream.sh
```

Review and validate the update before recording it:

```bash
git diff --submodule=log -- tradingagents-core
git -C tradingagents-core status --short
python -m pytest backend/tests -q
python -m ruff check backend
npm --prefix frontend run test
npm --prefix frontend run lint
npm --prefix frontend run build
npm --prefix frontend run test:e2e
git add tradingagents-core
git commit -m "chore: update TradingAgents submodule"
```

The helper does not create a commit. If you want to test a specific upstream tag or commit instead of the latest default-branch revision, update it manually:

```bash
git -C tradingagents-core fetch origin
git -C tradingagents-core checkout <tag-or-commit>
python -m pip install -e ./tradingagents-core
```

Then run the same checks and commit the `tradingagents-core` pointer. After pulling a UI commit that updates the pointer, collaborators should synchronize and reinstall it with:

```bash
git submodule update --init --recursive
python -m pip install -e ./tradingagents-core
```
