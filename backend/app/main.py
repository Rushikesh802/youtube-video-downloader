from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_v1_router
from app.config import settings
from app.core.exceptions import AppException
from app.core.logging import logger
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan lifecycle events."""
    logger.info("Initializing YouTube Video Downloader API service...")
    # In development mode, auto-create tables if not existing
    if settings.ENVIRONMENT in ("development", "test"):
        try:
            await init_db()
            logger.info("Database tables initialized successfully.")
        except Exception as e:
            logger.error("Failed to initialize database tables: %s", e)

    yield

    logger.info("Shutting down YouTube Video Downloader API service...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler for domain AppExceptions
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail},
        headers=exc.headers,
    )


# System healthcheck endpoint
@app.get("/healthz", tags=["System"], summary="System health check")
async def health_check() -> dict:
    return {
        "status": "ok",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


# Root greeting endpoint
@app.get("/", tags=["System"], include_in_schema=False)
async def root() -> dict:
    return {
        "message": "Welcome to YouTube & Authorized Media Downloader API",
        "docs": f"{settings.API_V1_PREFIX}/docs",
    }


# Register API v1 routes
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)
