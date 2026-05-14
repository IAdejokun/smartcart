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


def _configure_app_logging() -> None:
    uvicorn_logger = logging.getLogger("uvicorn")
    app_logger = logging.getLogger("app")
    app_logger.handlers = uvicorn_logger.handlers or []
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False


_configure_app_logging()
log = logging.getLogger("app.main")


async def _trainer_cadence_loop() -> None:
    from app.ml.trainer import maybe_trigger_training, _TRAINING_CADENCE_SECONDS
    while True:
        await asyncio.sleep(_TRAINING_CADENCE_SECONDS)
        try:
            maybe_trigger_training("cadence")
        except Exception:
            log.exception("Cadence trainer fire failed")


def _auto_seed_if_empty() -> None:
    """Seed the catalogue on first boot if the products table is empty.

    Runs synchronously during startup — this is intentional. We want the
    catalogue to be available before traffic is routed to this instance.
    Render will wait up to 5 minutes for the service to bind its port;
    seeding takes 5–10 minutes, so we start the server first and seed
    in the background via a thread.
    """
    from sqlalchemy import func, select
    from app.models.product import Product

    db = SessionLocal()
    try:
        count = db.scalar(select(func.count()).select_from(Product)) or 0
        if count > 0:
            log.info("Catalogue already seeded (%d products) — skipping auto-seed", count)
            return
        log.info("Empty catalogue detected — starting auto-seed in background thread")
    finally:
        db.close()

    # Run in a thread so the server starts accepting requests while seeding
    import threading
    def _seed_thread():
        try:
            from scripts.seed_amazon_catalogue import seed
            seed()
            # Re-initialise policy server after seeding so it picks up the products
            db2 = SessionLocal()
            try:
                get_policy_server().initialise(db2)
                log.info("Policy server re-initialised after seed")
            finally:
                db2.close()
        except Exception:
            log.exception("Auto-seed failed")

    t = threading.Thread(target=_seed_thread, daemon=True, name="auto-seeder")
    t.start()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    log.info("Starting %s in %s mode", settings.app_name, settings.environment)

    # Auto-seed runs in a background thread — server starts before seed completes.
    # Recommendations will fall back to empty-catalogue behaviour (no products)
    # for the first 5–10 minutes of a fresh deployment.
    _auto_seed_if_empty()

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
        docs_url=None if is_prod else "/docs",
        redoc_url=None if is_prod else "/redoc",
        openapi_url=None if is_prod else "/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Authorization", "Content-Type"],
    )

    if is_prod:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=[
                "*.onrender.com",
                "smartcart-ai-api.onrender.com",
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