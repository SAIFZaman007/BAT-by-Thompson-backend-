import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
    Create tables on first boot (dev convenience).
    Wrapped so a DB hiccup at startup does not crash the worker process —
    the server stays up and /api/health reports the real state instead.

    Production: replace with `alembic upgrade head` in your deploy pipeline.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅  Database tables verified / created.")
    except Exception as exc:                          # noqa: BLE001
        logger.error("❌  DB init failed (server still starting): %s", exc)


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():

    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}
    except Exception as exc:                         
        logger.warning("Health check: DB unreachable — %s", exc)
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": str(exc)},
        )