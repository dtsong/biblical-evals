"""FastAPI application entry point."""

import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.config_routes import router as config_router
from src.api.evaluations import router as evaluations_router
from src.api.health import router as health_router
from src.api.questions import router as questions_router
from src.api.reports import router as reports_router
from src.api.responses import router as responses_router
from src.api.reviews import router as reviews_router
from src.config import get_settings

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown."""
    if settings.nextauth_secret:
        logger.info("NextAuth.js JWT authentication enabled")
    else:
        logger.warning(
            "NEXTAUTH_SECRET not configured - auth endpoints will fail"
        )
    yield


app = FastAPI(
    title="Biblical Evals API",
    description=(
        "Framework for evaluating LLM responses to "
        "biblical and theological questions"
    ),
    version="0.0.1",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Include routers
app.include_router(health_router)
app.include_router(questions_router)
app.include_router(evaluations_router)
app.include_router(responses_router)
app.include_router(reviews_router)
app.include_router(reports_router)
app.include_router(config_router)
