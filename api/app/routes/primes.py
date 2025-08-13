# api/app/routes/primes.py
import math, pathlib, sys
from fastapi import APIRouter, Request
from .. import db as dao

router = APIRouter()

@router.get("")
def recent_primes(req: Request, limit: int = 12):
    conn = req.app.state.db
    rows = dao.primes_recent(conn, limit)
    out = []
    for r in rows:
        p = int(r["p"])
        # tolerate NULL block_id from older rows; derive from p
        bid = r["block_id"]
        block_id = int(bid) if bid is not None else (p // 1_000_000)
        # decimal digit count of M_p = 2^p - 1
        digits = int(math.floor(p * math.log10(2)) + 1)
        out.append({
            "p": p,
            "block_id": block_id,
            "digits": digits,
            "finished_at": r["finished_at"],
            "engine_info": r["engine_info"],
            "ns_elapsed": r["ns_elapsed"],
        })
    return out

@router.get("/count")
def primes_count(req: Request):
    conn = req.app.state.db
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM exponents WHERE is_prime=1 AND status='done'"
    ).fetchone()
    return {"count": int(row["c"] or 0)}
