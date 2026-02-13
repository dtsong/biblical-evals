"""Health check endpoints.

`/api/v1/health` is a lightweight liveness check.
`/api/v1/health/ready` performs deeper readiness checks (DB + env prerequisites).
"""

from __future__ import annotations

import os
import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.loaders.config_loader import load_app_config

router = APIRouter(prefix="/api/v1/health", tags=["health"])


def _env_present(name: str) -> bool:
    value = os.getenv(name)
    return value is not None and value.strip() != ""


def _google_key_present() -> bool:
    # Canonical key name is GOOGLE_AI_API_KEY, but keep legacy compatibility.
    return _env_present("GOOGLE_AI_API_KEY") or _env_present("GOOGLE_API_KEY")


def _provider_key_present(env_name: str) -> bool:
    if env_name in {"GOOGLE_AI_API_KEY", "GOOGLE_API_KEY"}:
        return _google_key_present()
    return _env_present(env_name)


@router.get("")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "version": "0.0.1"}


@router.get("/ready")
async def readiness_check(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JSONResponse:
    """Deep readiness check for deployments and monitoring.

    Returns 200 for healthy/degraded and 503 for unhealthy.
    """

    commit = os.getenv("COMMIT_SHA") or "unknown"
    version = "0.0.1"

    checks: dict[str, Any] = {}
    overall = "healthy"

    # --- Database ---
    db_start = time.perf_counter()
    try:
        await db.execute(text("SELECT 1"))
        db_latency_ms = int((time.perf_counter() - db_start) * 1000)
        checks["database"] = {"status": "ok", "latency_ms": db_latency_ms}
    except Exception as e:
        db_latency_ms = int((time.perf_counter() - db_start) * 1000)
        checks["database"] = {
            "status": "error",
            "latency_ms": db_latency_ms,
            "error": str(e),
        }
        overall = "unhealthy"

    # --- Auth prerequisites ---
    auth_ok = _env_present("NEXTAUTH_SECRET")
    checks["auth"] = {
        "status": "ok" if auth_ok else "missing",
        "required": ["NEXTAUTH_SECRET"],
    }
    if overall != "unhealthy" and not auth_ok:
        overall = "degraded"

    # --- LLM API key prerequisites (presence only) ---
    config = load_app_config()
    envs_by_provider: dict[str, set[str]] = {}
    for m in config.models:
        envs_by_provider.setdefault(m.provider, set()).add(m.api_key_env)

    providers_ok: list[str] = []
    providers_missing: list[str] = []
    missing_env_vars: list[str] = []

    for provider, env_names in sorted(envs_by_provider.items()):
        ok = any(_provider_key_present(env_name) for env_name in env_names)
        if ok:
            providers_ok.append(provider)
        else:
            providers_missing.append(provider)
            missing_env_vars.extend(sorted(env_names))

    llm_ok = len(providers_missing) == 0
    checks["llm_keys"] = {
        "status": "ok" if llm_ok else "missing",
        "providers": providers_ok,
        "missing_providers": providers_missing,
        "missing_env_vars": sorted(set(missing_env_vars)),
    }
    if overall != "unhealthy" and not llm_ok:
        overall = "degraded"

    payload = {
        "status": overall,
        "checks": checks,
        "version": version,
        "commit": commit,
        "commit_sha": commit,
    }

    status_code = 200 if overall in {"healthy", "degraded"} else 503
    return JSONResponse(payload, status_code=status_code)
