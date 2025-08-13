from pydantic import BaseModel
from typing import Optional, Dict, Any

class CreateJob(BaseModel):
    p: int
    progress_stride: Optional[int] = None  # 0/None => auto (~1%)

class JobStatus(BaseModel):
    id: str
    p: int
    status: str                 # queued | running | done | error
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
