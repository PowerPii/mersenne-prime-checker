from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Set

from fastapi import APIRouter, Request
from .._llcore import llcore
from .. import db as dao

router = APIRouter()

# ---- helpers ---------------------------------------------------------------


def _ensure_app_state(
    app,
) -> tuple[
    Dict[int, Set[asyncio.Queue]],
    Set[int],
    Dict[int, "asyncio.Queue[int]"],
    Dict[int, Set[asyncio.Task]],
]:
    """
    Make sure we have the state containers we need:
      - block_topics:   block_id -> set[Queue] (for WS broadcasting; queues contain dict or None sentinel)
      - block_cancel:   set of block_ids requested to stop
      - block_workq:    block_id -> work queue of exponents
      - block_tasks:    block_id -> running asyncio tasks for that block
    """
    s = app.state
    if not hasattr(s, "block_topics"):
        s.block_topics = {}  # dict[int, set[Queue]]
    if not hasattr(s, "block_cancel"):
        s.block_cancel = set()  # set[int]
    if not hasattr(s, "block_workq"):
        s.block_workq = {}  # dict[int, asyncio.Queue[int]]
    if not hasattr(s, "block_tasks"):
        s.block_tasks = {}  # dict[int, set[asyncio.Task]]
    return s.block_topics, s.block_cancel, s.block_workq, s.block_tasks


def _broadcast_sync(app, block_id: int, msg: Dict[str, Any]):
    """Broadcast a dict message to all subscriber queues for this block."""
    block_topics, *_ = _ensure_app_state(app)
    for q in list(block_topics.get(int(block_id), set())):
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            pass


def block_bounds(block_id: int) -> tuple[int, int]:
    """Return [start, end_excl) for a 1M-wide block."""
    start = int(block_id) * 1_000_000
    return start, start + 1_000_000


def primes_in_range(a: int, b: int) -> List[int]:
    """Segmented sieve of Eratosthenes: primes in [a, b)."""
    if b <= 2:
        return []
    a = max(a, 2)
    import math

    limit = int(math.isqrt(b)) + 1

    base = [True] * (limit + 1)
    base[0] = base[1] = False
    for i in range(2, int(math.isqrt(limit)) + 1):
        if base[i]:
            step = i
            base[i * i : limit + 1 : step] = [False] * (((limit - i * i) // step) + 1)

    small = [i for i, ok in enumerate(base) if ok]

    size = b - a
    seg = [True] * size
    for p in small:
        start = max(p * p, ((a + p - 1) // p) * p)
        for x in range(start, b, p):
            seg[x - a] = False

    return [a + i for i, ok in enumerate(seg) if ok]


# ---- REST endpoints --------------------------------------------------------


@router.get("")
def list_blocks(req: Request, limit: int = 6):
    """List the first N blocks, lazily seeding any missing ones."""
    conn = req.app.state.db
    rows = dao.block_list(conn, limit=limit)

    if len(rows) < limit:
        existing_ids = {r["id"] for r in rows}
        for bid in range(limit):
            if bid in existing_ids:
                continue
            start, end_excl = block_bounds(bid)
            primes = primes_in_range(start, end_excl)
            dao.block_upsert(conn, bid, start, end_excl, len(primes))
            dao.exponent_seed(conn, bid, primes)
        rows = dao.block_list(conn, limit=limit)

    return [
        {
            "id": r["id"],
            "start": r["start_p"],
            "end_excl": r["end_p_excl"],
            "label": f"{r['id']}–{r['id'] + 1}M",
            "candidate_count": r["candidate_count"],
            "tested_count": r["tested_count"],
            "verified_count": r["verified_count"],
            "status": r["status"],
        }
        for r in rows
    ]


@router.get("/{block_id}")
def get_block(req: Request, block_id: int):
    """Return block metadata plus the list of exponents."""
    block_id = int(block_id)
    conn = req.app.state.db

    b = dao.block_get(conn, block_id)
    if not b:
        start, end_excl = block_bounds(block_id)
        primes = primes_in_range(start, end_excl)
        dao.block_upsert(conn, block_id, start, end_excl, len(primes))
        dao.exponent_seed(conn, block_id, primes)
        b = dao.block_get(conn, block_id)

    exps = dao.exponents_by_block(conn, block_id)
    return {
        "block": {
            "id": b["id"],
            "start": b["start_p"],
            "end_excl": b["end_p_excl"],
            "candidate_count": b["candidate_count"],
            "tested_count": b["tested_count"],
            "verified_count": b["verified_count"],
            "status": b["status"],
        },
        "exponents": [
            {
                "p": r["p"],
                "status": r["status"],
                "is_prime": r["is_prime"],
                "ns_elapsed": r["ns_elapsed"],
                "engine_info": r["engine_info"],
            }
            for r in exps
        ],
    }


@router.post("/{block_id}/start")
async def start_block(req: Request, block_id: int, concurrency: int = 1):
    """
    Start (or resume) testing all unfinished prime exponents in the block.
    Broadcasts per-iteration ({p,pct}) and coverage snapshots ({tested,total}).
    Supports mid-iteration cancel via the llcore callback.
    """
    app = req.app
    conn = app.state.db
    block_id = int(block_id)
    concurrency = max(1, int(concurrency))

    block_topics, block_cancel, block_workq, block_tasks = _ensure_app_state(app)

    # ensure block exists and is seeded
    b = dao.block_get(conn, block_id)
    if not b:
        start, end_excl = block_bounds(block_id)
        primes = primes_in_range(start, end_excl)
        dao.block_upsert(conn, block_id, start, end_excl, len(primes))
        dao.exponent_seed(conn, block_id, primes)
        b = dao.block_get(conn, block_id)

    # worklist of unfinished exponents
    unfinished_rows = dao.exponents_unfinished(conn, block_id)
    todo = [int(r["p"]) for r in unfinished_rows]
    if not todo:
        # notify subscribers already complete
        _broadcast_sync(
            app,
            block_id,
            {
                "block_id": block_id,
                "tested": b["tested_count"],
                "total": b["candidate_count"],
                "done": True,
            },
        )
        # close subscriber sockets gracefully
        for q in list(block_topics.get(block_id, set())):
            try:
                q.put_nowait(None)
            except asyncio.QueueFull:
                pass
        return {"scheduled": 0, "message": "already complete"}

    # create+remember a work queue and task set for this block
    workq: "asyncio.Queue[int]" = asyncio.Queue()
    for p in todo:
        workq.put_nowait(p)
    block_workq[block_id] = workq
    block_tasks.setdefault(block_id, set())

    loop = asyncio.get_running_loop()
    sem = asyncio.Semaphore(concurrency)

    async def worker():
        while True:
            try:
                p = await workq.get()
            except asyncio.CancelledError:
                break
            try:
                # check cancel before scheduling next exponent
                if block_id in block_cancel:
                    # drain remaining items so workq.join() can complete
                    while not workq.empty():
                        try:
                            workq.get_nowait()
                            workq.task_done()
                        except Exception:
                            break
                    break

                def run_one():
                    cancelled_here = False
                    try:
                        dao.exponent_start(conn, p)

                        total_iters = max(0, p - 2)

                        def cb(iter_idx: int, _digest: bytes):
                            nonlocal cancelled_here
                            # cooperative cancel: if requested, raise to abort llcore loop
                            if block_id in block_cancel and not cancelled_here:
                                cancelled_here = True
                                raise RuntimeError("cancelled")
                            pct = (
                                100
                                if total_iters == 0
                                else int(((iter_idx + 1) * 100) / total_iters)
                            )
                            loop.call_soon_threadsafe(
                                _broadcast_sync,
                                app,
                                block_id,
                                {"block_id": block_id, "p": int(p), "pct": pct},
                            )

                        # Use stride=1 so we can react quickly to stop()
                        res = llcore.ll_test(int(p), progress_stride=1, callback=cb)

                        # finished normally
                        dao.exponent_finish_ok(
                            conn,
                            p,
                            int(res["is_prime"]),
                            int(res["ns_elapsed"]),
                            res.get("engine_info"),
                        )
                    except Exception as e:
                        # If this exponent was cancelled mid-run, reset it to queued instead of marking error
                        if str(e).lower().startswith("cancelled") or (
                            block_id in block_cancel
                        ):
                            dao.exponent_reset(
                                conn, p
                            )  # <= requires tiny helper in db.py
                            return
                        # genuine failure
                        dao.exponent_fail(conn, p, str(e))
                        return

                async with sem:
                    # run in threadpool so Python loop stays responsive
                    await loop.run_in_executor(app.state.executor, run_one)

                # coverage snapshot after each exponent (only when not cancelled)
                if block_id not in block_cancel:
                    dao.block_counts_bump(conn, block_id, 1)
                    b2 = dao.block_get(conn, block_id)
                    loop.call_soon_threadsafe(
                        _broadcast_sync,
                        app,
                        block_id,
                        {
                            "block_id": block_id,
                            "last_p": p,
                            "tested": b2["tested_count"],
                            "total": b2["candidate_count"],
                        },
                    )

            finally:
                workq.task_done()

    # spin workers
    workers = [asyncio.create_task(worker()) for _ in range(concurrency)]
    for w in workers:
        block_tasks[block_id].add(w)

    async def monitor_and_finalize():
        try:
            await workq.join()
        finally:
            # finalize / clean up regardless of normal or cancelled exit
            b3 = dao.block_get(conn, block_id)
            _broadcast_sync(
                app,
                block_id,
                {
                    "block_id": block_id,
                    "tested": b3["tested_count"],
                    "total": b3["candidate_count"],
                    "done": True,
                    "stopped": (block_id in block_cancel),
                },
            )
            # tell all subscribers to close
            for q in list(block_topics.get(block_id, set())):
                try:
                    q.put_nowait(None)
                except asyncio.QueueFull:
                    pass

            # cancel any leftover workers (safe even if already finished)
            for w in list(block_tasks.get(block_id, set())):
                w.cancel()
            block_tasks.pop(block_id, None)
            block_workq.pop(block_id, None)
            # clear cancel mark for next time
            if block_id in block_cancel:
                block_cancel.discard(block_id)

    fin = asyncio.create_task(monitor_and_finalize())
    block_tasks[block_id].add(fin)

    return {"scheduled": len(todo), "block_id": block_id, "concurrency": concurrency}


@router.post("/{block_id}/stop")
async def stop_block(req: Request, block_id: int):
    """
    Request cooperative cancellation for a block run.
    - Marks the block as cancelled
    - Drains the queue so the monitor can finish once current exponent aborts
    - Immediately notifies subscribers with a 'stopped' snapshot
    """
    app = req.app
    conn = app.state.db
    block_id = int(block_id)

    block_topics, block_cancel, block_workq, _block_tasks = _ensure_app_state(app)
    block_cancel.add(block_id)

    # Drain work queue (if any) so workq.join() is not blocked by pending items.
    q = block_workq.get(block_id)
    if q is not None:
        while not q.empty():
            try:
                q.get_nowait()
                q.task_done()
            except Exception:
                break

    # Broadcast an immediate 'stopped' snapshot so the UI can react quickly
    b = dao.block_get(conn, block_id)
    if b:
        _broadcast_sync(
            app,
            block_id,
            {
                "block_id": block_id,
                "tested": b["tested_count"],
                "total": b["candidate_count"],
                "stopped": True,
            },
        )

    return {"ok": True, "block_id": block_id}
