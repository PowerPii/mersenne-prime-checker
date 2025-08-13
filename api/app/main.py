# api/app/main.py
from fastapi import FastAPI
from concurrent.futures import ThreadPoolExecutor
from .routes import jobs, digits, blocks, primes
from .ws import router as ws_router 
from . import db
from fastapi.middleware.cors import CORSMiddleware

def create_app() -> FastAPI:
    app = FastAPI(title="Mersenne Lab API")
    app.state.executor = ThreadPoolExecutor(max_workers=1)
    app.state.jobs = {}
    app.state.queues = {}
    app.state.block_queues = {}
    app.state.block_cancel = set()  
    app.state.block_topics = {}

    app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
    app.include_router(digits.router, prefix="/digits", tags=["digits"])
    app.include_router(blocks.router, prefix="/blocks", tags=["blocks"])
    app.include_router(primes.router, prefix="/primes", tags=["primes"])
    app.include_router(ws_router, prefix="/ws", tags=["ws"])
    
    @app.on_event("startup")
    def _open_db():
        app.state.db = db.connect()

    @app.on_event("shutdown")
    def _shutdown():
        app.state.executor.shutdown(wait=False, cancel_futures=True)
        try: app.state.db.close()
        except: pass

    return app

app = create_app()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
