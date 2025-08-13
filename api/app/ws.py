# api/app/ws.py
from __future__ import annotations
import os
import asyncio
import time
import logging
from typing import Any, Dict, Set, cast
from urllib.parse import urlparse
from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketState

log = logging.getLogger("ws")
router = APIRouter()

DEFAULT_ALLOWED = {
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://0.0.0.0:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://0.0.0.0:5173",
    "https://localhost:3000",
    "https://127.0.0.1:3000",
    "https://localhost:5173",
    "https://127.0.0.1:5173",
}
_env = os.getenv("WS_ALLOWED_ORIGINS", "").strip()
ALLOWED_WS_ORIGINS: Set[str] = (
    {"*"}
    if _env == "*"
    else {x.strip() for x in _env.split(",") if x.strip()} or DEFAULT_ALLOWED
)

STRICT = os.getenv("WS_ORIGIN_STRICT", "0").lower() in ("1", "true", "yes")
DISABLE = os.getenv("WS_DISABLE_ORIGIN_CHECK", "").lower() in ("1", "true", "yes")

QueueT = asyncio.Queue[dict[str, Any] | None]


def _ensure_ws_state(app):
    s = app.state
    if not hasattr(s, "block_topics"):
        s.block_topics = {}
    if not hasattr(s, "job_topics"):
        s.job_topics = {}
    if not hasattr(s, "block_cancel"):
        s.block_cancel = set()
    return (
        cast(Dict[int, Set[QueueT]], s.block_topics),
        cast(Dict[str, Set[QueueT]], s.job_topics),
        cast(Set[int], s.block_cancel),
    )


def _topic_add(m: Dict[Any, Set[QueueT]], k: Any, q: QueueT):
    m.setdefault(k, set()).add(q)


def _topic_discard(m: Dict[Any, Set[QueueT]], k: Any, q: QueueT):
    s = m.get(k)
    if s:
        s.discard(q)
        if not s:
            m.pop(k, None)


def _origin_allowed(ws: WebSocket) -> bool:
    if DISABLE:
        log.info("WS origin check disabled")
        return True
    origin = ws.headers.get("origin")
    log.info(
        "WS handshake origin=%r allowed=%r strict=%r",
        origin,
        ALLOWED_WS_ORIGINS,
        STRICT,
    )
    if "*" in ALLOWED_WS_ORIGINS:
        return True
    if not origin:
        return not STRICT
    if origin in ALLOWED_WS_ORIGINS:
        return True
    if not STRICT:
        try:
            u = urlparse(origin)
            if u.scheme in ("http", "https") and u.hostname in {
                "localhost",
                "127.0.0.1",
                "0.0.0.0",
            }:
                return True
        except Exception:
            pass
    return False


async def _serve_queue(ws: WebSocket, q: QueueT) -> None:
    ping = asyncio.create_task(_pinger(ws))
    try:
        while True:
            msg = await q.get()
            if msg is None:
                break
            await ws.send_json(msg)
    except WebSocketDisconnect:
        log.info("WS client disconnected")
    except Exception:
        log.exception("WS stream crashed")
    finally:
        ping.cancel()
        if ws.application_state != WebSocketState.DISCONNECTED:
            try:
                await ws.close(code=1000)
            except RuntimeError:
                pass
        log.info("WS closed cleanly")


async def _pinger(ws: WebSocket):
    try:
        while True:
            await asyncio.sleep(25)
            await ws.send_json({"type": "ping", "t": time.time()})
    except Exception:
        pass


@router.websocket("/ws/blocks/{block_id}")
async def ws_block(ws: WebSocket, block_id: int):
    if not _origin_allowed(ws):
        log.warning("WS origin rejected for blocks/%s", block_id)
        await ws.close(code=1008)
        return
    await ws.accept()
    log.info("WS accepted blocks/%s from %r", block_id, ws.headers.get("origin"))
    block_topics, _, _ = _ensure_ws_state(ws.app)
    q: QueueT = asyncio.Queue(maxsize=256)
    _topic_add(block_topics, int(block_id), q)
    try:
        await _serve_queue(ws, q)
    finally:
        _topic_discard(block_topics, int(block_id), q)


@router.websocket("/ws/jobs/{job_id}")
async def ws_job(ws: WebSocket, job_id: str):
    if not _origin_allowed(ws):
        log.warning("WS origin rejected for jobs/%s", job_id)
        await ws.close(code=1008)
        return
    await ws.accept()
    log.info("WS accepted jobs/%s from %r", job_id, ws.headers.get("origin"))
    _, job_topics, _ = _ensure_ws_state(ws.app)
    q: QueueT = asyncio.Queue(maxsize=256)
    _topic_add(job_topics, job_id, q)
    try:
        await _serve_queue(ws, q)
    finally:
        _topic_discard(job_topics, job_id, q)
