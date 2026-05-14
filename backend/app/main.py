"""FastAPI application entry point."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.config import settings
from app.database import SessionLocal
from app.ml.policy_server import get_policy_server
from app.routers import auth, cart, products, recommendations, telemetry


# Configure logging once at module load. Render captures stdout, so we log to stdout.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


async def _trainer_cadence_loop() -> None:
    from app.ml.trainer import maybe_trigger_training, _TRAINING_CADENCE_SECONDS
    while True:
        await asyncio.sleep(_TRAINING_CADENCE_SECONDS)
        try:
            maybe_trigger_training("cadence")
        except Exception:
            log.exception("Cadence trainer fire failed")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    log.info("Starting %s in %s mode", settings.app_name, settings.environment)

    if settings.drl_inference_enabled:
        db = SessionLocal()
        try:
            get_policy_server().initialise(db)
        finally:
            db.close()
    else:
        log.warning("DRL inference DISABLED")

    cadence_task = asyncio.create_task(_trainer_cadence_loop())
    log.info("Trainer cadence loop started")

    yield

    cadence_task.cancel()
    try:
        await cadence_task
    except asyncio.CancelledError:
        pass
    log.info("Shutting down")


def create_app() -> FastAPI:
    is_prod = settings.environment == "production"

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        # Hide /docs and /redoc in production. Public API docs are a free
        # enumeration map for attackers. The OpenAPI spec is still
        # generated internally; we just don't serve the UI.
        docs_url=None if is_prod else "/docs",
        redoc_url=None if is_prod else "/redoc",
        openapi_url=None if is_prod else "/openapi.json",
        lifespan=lifespan,
    )

    # CORS — explicit allowlist, no wildcards in prod
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Trusted host — defends against Host header injection.
    # In production we only accept requests on our render domain.
    if is_prod:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=[
                "*.onrender.com",       # Render's domain (your service runs at smartcart.onrender.com)
                "smartcart-api.onrender.com",  # Replace with your actual Render service hostname
            ],
        )

    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(products.router, prefix="/api/v1")
    app.include_router(cart.router, prefix="/api/v1")
    app.include_router(recommendations.router, prefix="/api/v1")
    app.include_router(telemetry.router, prefix="/api/v1")

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    return app


app = create_app()