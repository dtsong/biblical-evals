"""Configuration API endpoints."""

from fastapi import APIRouter

from src.dependencies.auth import CurrentUser
from src.loaders.config_loader import load_app_config

router = APIRouter(prefix="/api/v1/config", tags=["config"])


@router.get("/models")
async def get_models(user: CurrentUser) -> dict:
    """Get available models with tier and cost metadata."""
    config = load_app_config()
    return {
        "models": [
            {
                "name": m.name,
                "provider": m.provider,
                "tier": m.tier,
                "cost_per_1k_input": m.cost_per_1k_input,
                "cost_per_1k_output": m.cost_per_1k_output,
            }
            for m in config.models
        ]
    }


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
