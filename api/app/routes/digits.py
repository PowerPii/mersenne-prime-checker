# api/app/routes/digits.py
import asyncio
import hashlib
import math
import pathlib
from uuid import uuid4
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from .._llcore import llcore

# import compiled extension

root = pathlib.Path(__file__).resolve().parents[3]
router = APIRouter()
ARTIFACT_ROOT = root / "api" / "data" / "artifacts"
ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@router.post("")
async def create_digits(req: Request, body: dict):
    p = int(body.get("p", 0))
    if p < 1:
        raise HTTPException(400, detail="p must be >= 1")

    # safety cap: ~size in decimal digits; adjust as you like
    est_digits = int(p * math.log10(2)) + 1
    MAX_DIGITS = int(5_000_000)  # ≈5MB per million digits + newline
    if est_digits > MAX_DIGITS:
        raise HTTPException(
            413,
            detail=f"Requested decimal artifact is too large ({est_digits} digits).",
        )

    job_id = uuid4().hex
    filename = body.get("filename") or f"M_{p}_decimal.txt"
    out_dir = ARTIFACT_ROOT / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename

    # persist 'queued'
    conn = req.app.state.db
    from .. import db as dao

    dao.job_insert(conn, job_id, kind="digits", p=p, status="queued")

    def work():
        try:
            dao.job_start(conn, job_id)
            meta = llcore.write_mersenne_decimal(p, str(out_path))
            size_bytes = out_path.stat().st_size
            digest = sha256_file(out_path)
            dao.artifact_insert(
                conn,
                job_id,
                filename,
                str(out_path),
                int(meta["digits"]),
                int(size_bytes),
                digest,
            )
            dao.job_finish_ok(conn, job_id, engine=None)
        except Exception as e:
            dao.job_fail(conn, job_id, str(e))
            raise

    asyncio.get_running_loop().run_in_executor(req.app.state.executor, work)
    return {"id": job_id, "p": p, "estimated_digits": est_digits}


@router.get("/{job_id}")
async def get_digits_job(req: Request, job_id: str):
    from .. import db as dao

    conn = req.app.state.db
    j = dao.job_get(conn, job_id)
    if not j:
        raise HTTPException(404, detail="job not found")
    a = dao.artifact_get_by_job(conn, job_id)
    out = dict(j)
    if a:
        out["artifact"] = dict(a)
    return out


@router.get("/{job_id}/download")
async def download_digits(req: Request, job_id: str):
    from .. import db as dao

    conn = req.app.state.db
    a = dao.artifact_get_by_job(conn, job_id)
    if not a:
        raise HTTPException(404, detail="artifact not ready")
    path = Path(a["path"])
    if not path.exists():
        raise HTTPException(404, detail="file missing")
    return FileResponse(str(path), filename=a["filename"], media_type="text/plain")
