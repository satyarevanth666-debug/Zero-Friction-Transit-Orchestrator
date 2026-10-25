"""Main FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api.health import router as health_router
from app.config import settings
from app.logging import configure_logging, logger
from app.middleware.rate_limit import limiter
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context for startup validation and shutdown cleanup."""
    configure_logging(settings.APP_ENV)
    logger.info(
        "Application starting up",
        env=settings.APP_ENV,
        timezone=settings.TIMEZONE,
        llm_enabled=settings.LLM_ENABLED,
    )

    # Security check: JWT_SECRET must be 32+ characters in production
    if settings.is_production and len(settings.JWT_SECRET) < 32:
        logger.critical("Fatal: JWT_SECRET must be at least 32 characters in production.")
        raise RuntimeError("JWT_SECRET must be at least 32 characters in production.")

    yield
    logger.info("Application shutting down")


def create_app() -> FastAPI:
    """Create and configure FastAPI application instance."""
    app = FastAPI(
        title="Zero-Friction Transit Orchestrator",
        description="Unified multi-modal transit planning API for India with honest data quality guarantees.",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    # State & Rate Limiter
    app.state.limiter = limiter

    @app.get("/")
    def root():
        return {
            "name": "Zero-Friction Transit Orchestrator API",
            "status": "online",
            "version": "0.1.0",
            "health": "/api/health",
            "docs": "/api/docs",
            "message": "Zero-Friction Transit API is live. Use the frontend web app or POST /api/plan/sync to search journeys.",
        }

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "message": "Too many requests. Please slow down and try again shortly.",
                "request_id": getattr(request.state, "request_id", "unknown"),
            },
        )

    # Middlewares (Execution order: outer to inner)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "Content-Disposition"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIdMiddleware)

    # Include API Routers under /api
    from app.api.plan import router as plan_router
    app.include_router(health_router, prefix="/api")
    app.include_router(plan_router, prefix="/api")

    return app


app = create_app()
