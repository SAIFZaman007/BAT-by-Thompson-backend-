import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler
from sqlalchemy import text

from app.api.v1 import admin, auth, contact, kyc, onboarding
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import Base, engine, SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bat.main")
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    docs_url="/api/docs" if settings.environment != "production" else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if settings.environment != "production" else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
api = "/api/v1"
app.include_router(onboarding.router, prefix=api)
app.include_router(kyc.router,        prefix=api)
app.include_router(contact.router,    prefix=api)
app.include_router(auth.router,       prefix=api)
app.include_router(admin.router,      prefix=api)


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup() -> None:
    """
    Create DB tables on first boot (dev convenience).
    Wrapped in try/except so a missing DB does NOT crash the worker process —
    the server stays up and /api/health reports the degraded state instead.

    For production: replace with `alembic upgrade head` in your deploy pipeline.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅  Database tables verified / created.")
    except Exception as exc:                          # noqa: BLE001
        logger.error("❌  DB init failed (server still starting): %s", exc)


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    """
    Liveness + readiness probe.

    Returns:
        200  {"status": "ok",       "db": "ok"}           — fully healthy
        200  {"status": "degraded", "db": "<error msg>"}  — DB unreachable
    """
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:                          
        db_status = str(exc)

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "db": db_status,
    }