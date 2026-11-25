"""FastAPI app: REST API under /api, built React UI served at /."""
import os
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import api_batches, api_report, api_review, api_settings, api_tests, db, grade, ingest, jobs, pipeline  # noqa: F401
from .cloud import CloudRefusal
from .provider_keys import MissingProviderKeys, PoolLimited

DIST = db.ROOT / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app):
    db.init()
    worker = jobs.Worker()
    worker.start()
    app.state.worker = worker
    ingest.resume_watchers()
    yield
    ingest.stop_all()
    worker.stopping.set()
    worker.join(timeout=10)


app = FastAPI(title="Paper Scanner", lifespan=lifespan)


@app.exception_handler(PoolLimited)
async def pool_limited(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=429, headers={"Retry-After": str(exc.seconds)})


@app.exception_handler(CloudRefusal)
async def provider_failure(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=502)


@app.exception_handler(MissingProviderKeys)
async def missing_keys(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=503)

for r in (api_tests, api_batches, api_review, api_settings, api_report):
    app.include_router(r.router, prefix="/api")

# The API has no login: it trusts whoever can reach it, which must be this computer only.
# Host allowlist stops DNS rebinding; the Origin check stops other websites from writing (CSRF).
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "::1", "testserver",
                 *filter(None, os.environ.get("SCANNER_ALLOWED_HOSTS", "").split(","))]


@app.middleware("http")
async def same_origin_writes(request, call_next):
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if request.headers.get("sec-fetch-site") == "cross-site" or (
                origin is not None and urlparse(origin).netloc != request.headers.get("host")):
            return JSONResponse({"detail": "Blocked: this request came from another website."}, status_code=403)
    return await call_next(request)


app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)  # added last = runs first


@app.get("/api/health")
def health():
    with db.connect() as c:
        counts = {r["status"]: r["n"] for r in c.execute("SELECT status, COUNT(*) n FROM job GROUP BY status")}
    return {"ok": True, "jobs": counts}



# ---------- SPA (must stay last) ----------

@app.get("/{path:path}", include_in_schema=False)
def spa(path: str):
    if path.startswith("api/"):
        raise HTTPException(404)
    f = (DIST / path).resolve()
    if path and f.is_file() and DIST.resolve() in f.parents:
        return FileResponse(f)
    return FileResponse(DIST / "index.html")
