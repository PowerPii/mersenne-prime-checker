from fastapi import APIRouter, HTTPException, Request
from uuid import uuid4
from ..schema.models import CreateJob
from ..services.ll_runner import submit_ll

router = APIRouter()

@router.post("")
async def create_job(req: Request, body: CreateJob):
    p = int(body.p)
    if p < 2:
        raise HTTPException(400, detail="p must be >= 2")
    job_id = uuid4().hex
    await submit_ll(req.app, job_id, p, body.progress_stride)
    return {"id": job_id}

@router.get("/{job_id}")
async def get_job(req: Request, job_id: str):
    job = req.app.state.jobs.get(job_id)
    if not job:
        raise HTTPException(404, detail="job not found")
    return job
