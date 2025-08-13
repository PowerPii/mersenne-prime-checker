import asyncio, pathlib, sys
root = pathlib.Path(__file__).resolve().parents[3]  # repo root
p = root / "build" / "bindings" / "python"
if p.exists() and str(p) not in sys.path:
    sys.path.append(str(p))
import llcore # type: ignore

from typing import Optional

async def submit_ll(app, job_id: str, p: int, progress_stride):
    loop = asyncio.get_running_loop()
    q: asyncio.Queue = asyncio.Queue(maxsize=1024)
    app.state.queues[job_id] = q
    app.state.jobs[job_id] = {"id": job_id, "p": p, "status": "queued", "result": None, "error": None}

    stride = 0 if (progress_stride is None) else int(progress_stride)

    def cb(iter_idx: int, digest_bytes: bytes):
        pct = int((iter_idx + 1) * 100 / max(1, p - 2))
        item = {"iteration": int(iter_idx), "pct": pct, "digest": digest_bytes.hex()}
        # thread-safe handoff from worker thread to asyncio loop
        loop.call_soon_threadsafe(q.put_nowait, item)

    def work():
        app.state.jobs[job_id]["status"] = "running"
        res = llcore.ll_test(int(p), progress_stride=stride, callback=cb)
        app.state.jobs[job_id]["result"] = res
        app.state.jobs[job_id]["status"] = "done"
        return res

    fut = loop.run_in_executor(app.state.executor, work)

    async def finalize():
        try:
            await fut
        except Exception as e:
            app.state.jobs[job_id]["status"] = "error"
            app.state.jobs[job_id]["error"] = str(e)
        finally:
            loop.call_soon_threadsafe(q.put_nowait, None)  # sentinel to close WS

    loop.create_task(finalize())