# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Next.js 14 with TypeScript, Tailwind CSS, and shadcn/ui for the frontend; FastAPI and SQLite for the backend; Docker Compose for local orchestration. TradingAgents remains an untouched Git submodule.

## Users

Existing TradingAgents users who want to configure, run, monitor, and revisit market analyses through a browser instead of the CLI.

## Product Purpose

Provide a web-based alternative to the TradingAgents CLI. Users can start analyses, watch agent progress in real time, inspect completed reports and trading signals, and revisit analysis history.

## Positioning

The product wraps the existing TradingAgents Python API without modifying upstream code, preserving compatibility with a pinned submodule while adding a browser workflow and persistent run history.

## Operating Context

Users select a ticker, analysis date, analyst team, LLM provider, and research depth; monitor long-running multi-agent work over a WebSocket stream; review generated reports and the final signal; and browse previous runs. API credentials are supplied through the local environment.

## Capabilities and Constraints

- TradingAgents must remain untouched in `tradingagents-core/`.
- Analyses can run for several minutes and execute in a background task.
- Agent transitions, messages, completed reports, and final signals stream to the browser.
- SQLite indexes run metadata and results without requiring an external database.
- The upstream submodule is pinned and updated deliberately with `update-upstream.sh`.
- No financial-performance, regulatory, or investment-outcome claims may be invented.

## Evidence on Hand

The implementation brief is in `plan.md`. No logo, brand system, testimonials, customer claims, performance benchmarks, or production deployment evidence has been supplied.

## Product Principles

- Preserve upstream TradingAgents code and make integration boundaries explicit.
- Make long-running analysis transparent rather than leaving users at an indeterminate wait state.
- Keep sophisticated configuration legible for users already familiar with TradingAgents.
- Make every completed report and signal easy to retrieve and compare later.
- Prefer a dependable local setup with few external services.

