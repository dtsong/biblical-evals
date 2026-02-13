"""Access request and approval API endpoints."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.db.models import User
from src.dependencies.auth import AdminUser, AuthenticatedUser

router = APIRouter(prefix="/api/v1/access", tags=["access"])


def _serialize_user(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "access_status": user.access_status,
        "is_admin": user.role == "admin",
        "access_requested_at": user.access_requested_at,
        "access_reviewed_at": user.access_reviewed_at,
        "access_reviewed_by": (
            str(user.access_reviewed_by) if user.access_reviewed_by else None
        ),
    }


@router.get("/me")
async def get_my_access_status(user: AuthenticatedUser) -> dict:
    """Return authenticated user's access status."""
    return _serialize_user(user)


@router.post("/request")
async def request_access(
    user: AuthenticatedUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Submit access request for the authenticated user."""
    if user.role == "admin" or user.access_status == "approved":
        return {
            "message": "Already approved",
            "access_status": user.access_status,
        }

    if user.access_status != "pending":
        user.access_status = "pending"
        user.access_requested_at = datetime.now(UTC)
        user.access_reviewed_at = None
        user.access_reviewed_by = None
        await db.commit()
        await db.refresh(user)

    return {
        "message": "Access request submitted",
        "access_status": user.access_status,
    }


@router.get("/requests")
async def list_access_requests(
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    access_status: str = Query(
        default="pending",
        pattern="^(pending|approved|rejected|not_requested|all)$",
    ),
) -> dict:
    """List non-admin users and their access statuses."""
    query = select(User).where(User.role != "admin")
    if access_status != "all":
        query = query.where(User.access_status == access_status)

    query = query.order_by(User.access_requested_at.desc(), User.created_at.desc())
    result = await db.execute(query)
    users = list(result.scalars().all())

    return {
        "requested_by": str(admin.id),
        "users": [_serialize_user(user) for user in users],
    }


@router.post("/requests/{user_id}/approve")
async def approve_access_request(
    user_id: UUID,
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Approve access for a user."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already an admin",
        )

    user.access_status = "approved"
    user.access_reviewed_at = datetime.now(UTC)
    user.access_reviewed_by = admin.id
    await db.commit()
    await db.refresh(user)

    return {
        "message": "User approved",
        "user": _serialize_user(user),
    }


@router.post("/requests/{user_id}/reject")
async def reject_access_request(
    user_id: UUID,
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Reject access for a user."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already an admin",
        )

    user.access_status = "rejected"
    user.access_reviewed_at = datetime.now(UTC)
    user.access_reviewed_by = admin.id
    await db.commit()
    await db.refresh(user)

    return {
        "message": "User rejected",
        "user": _serialize_user(user),
    }
