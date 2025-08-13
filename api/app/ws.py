# api/app/ws.py
import asyncio
from typing import Set

from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

router = APIRouter()

# --- helpers ---------------------------------------------------------------


def _get_job_queue(app, job_id: str) -> asyncio.Queue:
    """
    Per-job single queue (legacy). Producers should push dicts and end with None.
    """
    if not hasattr(app.state, "queues"):
        app.state.queues = {}
    return app.state.queues.setdefault(job_id, asyncio.Queue(maxsize=1024))


def _subscribe_block(app, block_id: int) -> asyncio.Queue:
    """
    Pub-sub: one queue per subscriber. Producers should broadcast to all queues
    in app.state.block_topics[block_id], and finish by sending a None sentinel
    to each queue.
    """
    if not hasattr(app.state, "block_topics"):
        app.state.block_topics = {}  # type: ignore[attr-defined]
    subs: Set[asyncio.Queue] = app.state.block_topics.setdefault(block_id, set())  # type: ignore[attr-defined]
    q: asyncio.Queue = asyncio.Queue(maxsize=512)
    subs.add(q)
    return q


def _unsubscribe_block(app, block_id: int, q: asyncio.Queue) -> None:
    subs: Set[asyncio.Queue] = app.state.block_topics.get(block_id, set())  # type: ignore[attr-defined]
    subs.discard(q)


# --- WebSocket endpoints ---------------------------------------------------


@router.websocket("/jobs/{job_id}")
async def ws_job(websocket: WebSocket, job_id: str):
    """
    Stream per-job progress messages until a None sentinel arrives.
    """
    await websocket.accept()
    q = _get_job_queue(websocket.app, job_id)

    try:
        while True:
            msg = await q.get()
            if msg is None:
                # graceful end initiated by producer
                try:
                    await websocket.close(code=1000)
                except RuntimeError:
                    pass
                break
            await websocket.send_json(msg)
    except WebSocketDisconnect:
        # client navigated away; just stop
        return


@router.websocket("/blocks/{block_id}")
async def ws_block(websocket: WebSocket, block_id: int):
    """
    Subscribe to a block's pub-sub topic. Each subscriber gets its own queue.
    Producers broadcast dict messages to all queues and finally send a None
    sentinel to each queue to close all subscribers.
    """
    await websocket.accept()
    block_id = int(block_id)
    q = _subscribe_block(websocket.app, block_id)

    try:
        while True:
            msg = await q.get()
            if msg is None:
                # final sentinel → close once
                try:
                    await websocket.close(code=1000)
                except RuntimeError:
                    pass
                break
            await websocket.send_json(msg)
    except WebSocketDisconnect:
        # client closed; nothing else to do
        return
    finally:
        _unsubscribe_block(websocket.app, block_id, q)
