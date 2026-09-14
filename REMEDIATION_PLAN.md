# Final Review Remediation Plan

## Recorded gaps

1. **Runner parity**
   - The adapter only marks report owners complete; it does not expose the selected-analyst sequence, research debate, trader handoff, risk debate, or portfolio-manager progress.
   - Debate turns are not projected into the activity stream.
   - Successful runs omit upstream `curr_state`, state-log, memory-log, and signal-processing bookkeeping.
   - Checkpoints are cleared before post-run bookkeeping, so a bookkeeping failure can destroy resumability.
   - Conversely, completion followed by unverified best-effort deletion can leave an END checkpoint that replays stale completed output on the next identical run.

2. **Terminal event consistency**
   - Failure currently persists `error` before `status=failed`; the WebSocket closes on `error`, so a client can terminate while its run still says `running`.
   - A connection whose cursor is already caught up to a completed or failed run waits indefinitely.
   - Restart reconciliation marks a run failed without creating a terminal error event.
   - The event condition has a lost-notification race that can delay a committed event until the 20-second timeout.

3. **Backend container packaging**
   - Compose builds from `./backend`, which cannot access `tradingagents-core`.
   - The image copies backend files into `/app` but starts `backend.main:app`, which requires `/app/backend`.
   - The image never installs the pinned TradingAgents submodule.

4. **Verification coverage**
   - Backend tests do not prove FIFO/no-overlap execution, startup queued-run recovery, complete runner progression/bookkeeping, or terminal WebSocket behavior.
   - Frontend stream tests do not cover REST-terminal runs or terminal errors.
   - Browser tests do not actually drive queued → running → completed, the six signal values, sanitized Markdown, or history empty/sort/pagination behavior.
   - Responsive overflow coverage is limited to the dashboard.

The earlier screenshot claim is not a gap: all six required files exist in `.impeccable/review/` and were visually verified.

## Implementation plan

### 1. Make terminal persistence atomic

- Add store operations that commit the run snapshot, `status`, and terminal `complete`/`error` event together.
- Ensure `complete.data.run.last_event_seq` equals the terminal event sequence.
- Commit a checkpoint-cleanup marker with successful completion; close the active checkpoint connection, verify deletion, and retain the marker until cleanup succeeds.
- Retry pending cleanup during startup and before matching queued work so a crash or SQLite lock cannot replay a completed END checkpoint.
- Reconcile interrupted runs through the same failed-terminal operation.
- Re-check the persisted sequence while holding the event condition before waiting.

### 2. Restore runner lifecycle parity

- Emit idempotent agent-status transitions following the pinned CLI ordering.
- Project each distinct research and risk debate response into the bounded activity stream.
- Set the upstream ticker/current state, write the JSON-safe state log, append the memory decision, process the required final decision, and only then clear the checkpoint.
- Keep checkpoint cleanup in `finally`; retain the checkpoint after any stream or post-run failure.

### 3. Close terminal streams deterministically

- Reject invalid future cursors.
- Close immediately after a terminal snapshot or after replay reaches a terminal event.
- Close a caught-up legacy terminal run instead of waiting.
- Seed terminal state from REST in the frontend hook and do not open/reconnect a socket for an already-terminal run.

### 4. Package the backend from the repository root

- Give the backend build the root context and explicit Dockerfile path.
- Copy `/backend` as a package, copy/install the pinned `/tradingagents-core`, and launch Uvicorn as a module.
- Add a root `.dockerignore` that reduces context without excluding either required tree.

### 5. Add deterministic regression coverage

- Backend: exact runner progression/bookkeeping, FIFO/no overlap, lifespan recovery, atomic terminal ordering, terminal snapshot/cursor closure, and event-wait race.
- Frontend unit: already-terminal REST result, terminal error, and reconnect cleanup.
- Playwright: mocked live completion/reconnect, all signals, inert raw HTML, query-aware history empty/sort/pagination/failure, and all three routes at 390/768/1280/1440 px.
- Use only fake upstream modules, temporary SQLite databases, and intercepted browser traffic; never call an LLM or market-data service.

## Completion gate

- Backend tests and Ruff pass.
- Frontend unit tests, lint, and production build pass.
- Playwright passes with deterministic mocks.
- The submodule remains pinned and clean.
- Docker Compose config/build pass when Docker is available; otherwise static packaging checks pass and the unavailable runtime is reported explicitly.
- A fresh read-only review has no remaining findings from this document.

## Implementation status

- [x] Atomic terminal persistence and accurate terminal snapshots
- [x] Durable, verified checkpoint-cleanup reconciliation
- [x] Upstream runner bookkeeping, message classification, and live progress parity
- [x] Deterministic terminal WebSocket and frontend reconnect behavior
- [x] Root-context backend container packaging with pinned submodule installation
- [x] Backend, frontend, browser, responsive, and cleanup-race regressions
- [x] Independent test gate: PASS
- [x] Fresh read-only review: `VERDICT: SHIP`

Final verification: 56 backend tests, 32 frontend unit tests, and 7 Playwright tests pass; Ruff, frontend lint, and the production build pass. Docker is not installed in the current environment, so its executable build was skipped after the static compose/image/import contract passed.
