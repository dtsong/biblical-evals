"""Configuration API endpoints."""

from fastapi import APIRouter

from src.dependencies.auth import CurrentUser
from src.loaders.config_loader import load_app_config

router = APIRouter(prefix="/api/v1/config", tags=["config"])


@router.get("/perspectives")
async def get_perspectives(user: CurrentUser) -> dict:
    """Get available theological perspectives."""
    config = load_app_config()
    return {"perspectives": [p.model_dump() for p in config.perspectives]}


@router.get("/dimensions")
async def get_dimensions(user: CurrentUser) -> dict:
    """Get available scoring dimensions."""
    config = load_app_config()
    return {"dimensions": [d.model_dump() for d in config.dimensions]}
