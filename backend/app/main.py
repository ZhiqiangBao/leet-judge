from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse

from .admin_register import app as admin_register_app
from .api.admin import router as admin_router
from .api.auth import router as auth_router
from .api.duels import router as duels_router
from .api.problems import router as problems_router
from .config import (
    ADMIN_REGISTER_HOST,
    ADMIN_REGISTER_PORT,
    COOKIE_NAME,
    FRONTEND_DIST,
    HOST,
    PORT,
    ensure_dirs,
    secret_key,
)
from .db import Base, engine
from .judge.queue import spawn_worker, stop_worker
from .models import Duel, ProblemPublish  # noqa: F401
from .services.problems import ProblemError, bank


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_dirs()
    Base.metadata.create_all(bind=engine)
    try:
        if not bank.list():
            bank.reload()
    except ProblemError:
        bank.reload()
    config = uvicorn.Config(
        admin_register_app,
        host=ADMIN_REGISTER_HOST,
        port=ADMIN_REGISTER_PORT,
        log_level="info",
        access_log=True,
    )
    admin_server = uvicorn.Server(config)
    admin_server.install_signal_handlers = False
    admin_task = asyncio.create_task(admin_server.serve())
    while not admin_server.started:
        if admin_task.done():
            await admin_task
        await asyncio.sleep(0.05)
    await spawn_worker()
    yield
    admin_server.should_exit = True
    await admin_task
    await stop_worker()


app = FastAPI(title="Local Leet", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    SessionMiddleware,
    secret_key=secret_key(),
    session_cookie=COOKIE_NAME,
    same_site="lax",
    https_only=False,
    max_age=60 * 60 * 24 * 14,
)
app.include_router(auth_router)
app.include_router(problems_router)
app.include_router(duels_router)
app.include_router(admin_router)


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "problems": len(bank.list()),
        "admin_register": f"http://{ADMIN_REGISTER_HOST}:{ADMIN_REGISTER_PORT}/",
    }


if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa(request: Request, full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        file_path = FRONTEND_DIST / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        index = FRONTEND_DIST / "index.html"
        if index.is_file():
            return FileResponse(index, headers={"Cache-Control": "no-cache"})
        return JSONResponse({"detail": "frontend not built"}, status_code=404)


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host=HOST, port=PORT, app_dir=str(Path(__file__).resolve().parents[1]))
