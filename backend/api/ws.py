from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["stream"])

TERMINAL_EVENTS = {"complete", "error"}
TERMINAL_STATUSES = {"completed", "failed"}


@router.websocket("/ws/analysis/{run_id}")
async def stream(
    websocket: WebSocket, run_id: UUID, after: int | None = None
) -> None:
    app = websocket.app
    run = app.state.store.get_run(run_id)
    if after is not None and (after < 0 or (run and after > run.last_event_seq)):
        await websocket.close(4400)
        return
    if not run:
        await websocket.close(4404)
        return

    await websocket.accept()
    cursor = after if after is not None else run.last_event_seq
    if after is None:
        await websocket.send_json(
            {
                "run_id": str(run_id),
                "seq": cursor,
                "emitted_at": run.created_at.isoformat(),
                "type": "snapshot",
                "data": {"run": run.model_dump(mode="json")},
            }
        )
        if run.status in TERMINAL_STATUSES:
            await websocket.close(code=1000)
            return

    try:
        while True:
            events = app.state.store.events_after(run_id, cursor)
            for event in events:
                await websocket.send_json(event.model_dump(mode="json"))
                cursor = event.seq
                if event.type in TERMINAL_EVENTS:
                    await websocket.close(code=1000)
                    return

            # This also closes legacy terminal runs that predate persisted
            # complete/error events, provided the client is already caught up.
            latest = app.state.store.get_run(run_id)
            if (
                latest
                and latest.status in TERMINAL_STATUSES
                and cursor >= latest.last_event_seq
            ):
                await websocket.close(code=1000)
                return
            await app.state.runner.wait_for_events(run_id, cursor)
    except WebSocketDisconnect:
        return
