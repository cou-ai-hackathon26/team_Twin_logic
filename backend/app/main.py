"""FastAPI application entry point.

    uvicorn app.main:app --port 8000

If ``frontend/dist`` exists, it is served at / so the whole app runs on one
local port.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from .api.auth_routes import router as auth_router
from .api.tts_routes import router as tts_router
from .api.routes import router
from .api.admin_routes import router as admin_router
from .api.practice_routes import student as practice_student_router
from .api.practice_routes import teacher as practice_teacher_router
from .config import BACKEND_DIR, get_settings
from .db import SessionLocal, init_db
from .models import Passage
from .seed.demo import seed_demo
from .services.readings import requeue_unfinished
from .speech import registry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("porabondhu")

SEED_FILE = Path(__file__).resolve().parent / "seed" / "passages.json"
# T01-T12: written to practise NCTB textbook lessons (see docs/CURRICULUM_ALIGNMENT.md)
TEXTBOOK_FILE = SEED_FILE.with_name("textbook_passages.json")
FRONTEND_DIST = BACKEND_DIR.parent / "frontend" / "dist"


def seed_passages() -> int:
    db = SessionLocal()
    try:
        existing = set(db.scalars(select(Passage.code)).all())
        added = 0
        seeds = [p for f in (SEED_FILE, TEXTBOOK_FILE) if f.exists() for p in json.loads(f.read_text(encoding="utf-8"))]
        for p in seeds:
            if p["code"] not in existing:
                db.add(Passage(code=p["code"], title=p["title"], grade=p["grade"], text=p["text"],
                               language=p.get("language", "bn")))
                added += 1
        db.commit()
        return added
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    n = seed_passages()
    if n:
        log.info("seeded %d passages", n)
    if get_settings().seed_demo:
        demo = seed_demo()
        if demo:
            log.info("seeded demo accounts: %s", demo)
    q = requeue_unfinished()
    if q:
        log.info("re-queued %d unfinished readings", q)
    if get_settings().preload_models:
        threading.Thread(target=registry.get_ctc, daemon=True).start()
    threading.Thread(target=_audio_janitor, daemon=True, name="pb-audio-janitor").start()
    yield


def _audio_janitor() -> None:
    """Delete expired recordings at start-up and then every 6 hours."""
    from .services.readings import purge_old_audio

    while True:
        try:
            n = purge_old_audio()
            if n:
                log.info("deleted %d recordings older than %d days", n, get_settings().audio_retention_days)
        except Exception:  # noqa: BLE001
            log.exception("audio clean-up failed")
        time.sleep(6 * 3600)


app = FastAPI(title="PoraBondhu AI", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def same_origin_writes(request, call_next):
    """CSRF guard: a browser request that changes data must come from this site (or an allowed
    dev origin). Matters most when cookies are SameSite=None (e.g. inside a Hugging Face iframe)."""
    from urllib.parse import urlsplit

    from fastapi.responses import JSONResponse

    origin = request.headers.get("origin")
    if origin and request.method in ("POST", "PUT", "PATCH", "DELETE") and request.url.path.startswith("/api/"):
        host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
        allowed = {o.strip() for o in get_settings().cors_origins.split(",") if o.strip()}
        if urlsplit(origin).netloc != host and origin not in allowed:
            return JSONResponse({"detail": "Cross-site request blocked"}, status_code=403)
    return await call_next(request)


def _route_group(path: str) -> str:
    """/api/readings/17/marks/3 -> /api/readings (keeps metric labels few and free of ids)."""
    parts = [p for p in path.split("/") if p][:2]
    return "/" + "/".join(parts) if parts and parts[0] == "api" else "/static"


@app.middleware("http")
async def http_metrics(request, call_next):
    if not get_settings().metrics_enabled or request.url.path == "/metrics":
        return await call_next(request)
    from . import metrics

    t0 = time.perf_counter()
    response = await call_next(request)
    metrics.observe("pb_http_request_seconds", time.perf_counter() - t0)
    metrics.inc("pb_http_requests_total", method=request.method, route=_route_group(request.url.path),
                status=f"{response.status_code // 100}xx")
    return response


@app.get("/metrics", include_in_schema=False)
def prometheus_metrics():
    """Prometheus scrape endpoint; 404 unless PB_METRICS_ENABLED=true (off on the hosted demo)."""
    from fastapi import HTTPException
    from fastapi.responses import PlainTextResponse

    from . import metrics
    from .services.readings import queue_state

    if not get_settings().metrics_enabled:
        raise HTTPException(404, "Not found")
    st = queue_state()
    metrics.gauge_set("pb_workers", st["workers"])
    metrics.gauge_set("pb_queue_limit", st["limit"])
    return PlainTextResponse(metrics.render(), media_type="text/plain; version=0.0.4")


app.include_router(auth_router)
app.include_router(router)
app.include_router(tts_router)
app.include_router(practice_teacher_router)
app.include_router(practice_student_router)
app.include_router(admin_router)

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        root = FRONTEND_DIST.resolve()
        f = (FRONTEND_DIST / path).resolve()
        if path and f.is_file() and f.is_relative_to(root):
            return FileResponse(f)
        return FileResponse(FRONTEND_DIST / "index.html")
