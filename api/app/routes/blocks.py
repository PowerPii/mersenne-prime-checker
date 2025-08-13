# api/app/routes/blocks.py
from __future__ import annotations

import asyncio
from typing import List
from fastapi import APIRouter, Request
from .._llcore import llcore
from .. import db as dao

router = APIRouter()


# ---- helpers ---------------------------------------------------------------


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


def _broadcast_sync(app, block_id: int, msg):
    """Broadcast a dict message to all subscriber queues for this block."""
    for q in list(app.state.block_topics.get(block_id, set())):
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            pass


# ---- REST endpoints --------------------------------------------------------


@router.get("")
def list_blocks(req: Request, limit: int = 6):
    """List the first N blocks, lazily seeding any missing ones."""
    conn = req.app.state.db
    rows = dao.block_list(conn, limit=limit)

    # lazily seed missing contiguous IDs [0, limit)
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
    """
    app = req.app
    conn = app.state.db
    block_id = int(block_id)
    concurrency = max(1, int(concurrency))

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
        # let subscribers know it’s already complete
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
        # close all subscribers
        for q in list(app.state.block_topics.get(block_id, set())):
            try:
                q.put_nowait(None)
            except asyncio.QueueFull:
                pass
        return {"scheduled": 0, "message": "already complete"}

    workq: asyncio.Queue[int] = asyncio.Queue()
    for p in todo:
        workq.put_nowait(p)

    loop = asyncio.get_running_loop()
    sem = asyncio.Semaphore(concurrency)

    async def worker():
        while True:
            try:
                p = await workq.get()
            except asyncio.CancelledError:
                break
            try:
                # check cancel before starting a new exponent
                if block_id in app.state.block_cancel:
                    # drain remaining items so workq.join() can complete
                    while not workq.empty():
                        try:
                            workq.get_nowait()
                            workq.task_done()
                        except Exception:
                            break
                    break

                def run_one():
                    try:
                        dao.exponent_start(conn, p)

                        total = max(0, p - 2)

                        def cb(iter_idx: int, _digest: bytes):
                            pct = (
                                100
                                if total == 0
                                else int(((iter_idx + 1) * 100) / total)
                            )
                            loop.call_soon_threadsafe(
                                _broadcast_sync,
                                app,
                                block_id,
                                {"block_id": block_id, "p": int(p), "pct": pct},
                            )

                        res = llcore.ll_test(int(p), progress_stride=0, callback=cb)
                        dao.exponent_finish_ok(
                            conn,
                            p,
                            int(res["is_prime"]),
                            int(res["ns_elapsed"]),
                            res["engine_info"],
                        )
                    except Exception as e:
                        dao.exponent_fail(conn, p, str(e))
                        raise

                async with sem:
                    await loop.run_in_executor(app.state.executor, run_one)

                # coverage snapshot after each exponent
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

    # spin workers and a finalizer
    workers = [asyncio.create_task(worker()) for _ in range(concurrency)]

    async def monitor_and_finalize():
        await workq.join()
        if block_id in app.state.block_cancel:
            app.state.block_cancel.discard(block_id)

        b3 = dao.block_get(conn, block_id)
        _broadcast_sync(
            app,
            block_id,
            {
                "block_id": block_id,
                "tested": b3["tested_count"],
                "total": b3["candidate_count"],
                "done": True,
            },
        )
        # send sentinel to all subscribers so sockets close cleanly
        for q in list(app.state.block_topics.get(block_id, set())):
            try:
                q.put_nowait(None)
            except asyncio.QueueFull:
                pass

        for w in workers:
            w.cancel()

    asyncio.create_task(monitor_and_finalize())
    return {"scheduled": len(todo), "block_id": block_id, "concurrency": concurrency}


@router.post("/{block_id}/stop")
async def stop_block(req: Request, block_id: int):
    """Request cooperative cancellation for a block run."""
    req.app.state.block_cancel.add(int(block_id))
    return {"ok": True}
