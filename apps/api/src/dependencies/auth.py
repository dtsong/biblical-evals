"""Authentication and access-control dependencies for FastAPI endpoints."""

import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.core.jwt import TokenVerificationError, verify_token
from src.db.database import get_db
from src.db.models import User

logger = logging.getLogger(__name__)


def _is_admin_email(email: str | None) -> bool:
    if not email:
        return False
    settings = get_settings()
    return email.lower() in settings.admin_email_set


def _pending_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "ACCESS_PENDING",
            "message": "Account pending approval",
        },
    )


async def get_authenticated_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Get the current authenticated user from JWT token.

    Auto-creates user on first login if email is present.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    try:
        decoded = verify_token(token)
    except TokenVerificationError as e:
        logger.error(
            "Token verification infrastructure error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable",
        ) from e

    if decoded is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    decoded_email = decoded.email.lower() if decoded.email else None

    query = select(User).where(User.auth_provider_id == decoded.sub)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None and decoded_email:
        email_query = select(User).where(func.lower(User.email) == decoded_email)
        email_result = await db.execute(email_query)
        user = email_result.scalar_one_or_none()

    is_admin = _is_admin_email(decoded_email)

    if user is None:
        if not decoded_email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email required for account creation",
                headers={"WWW-Authenticate": "Bearer"},
            )

        now = datetime.now(UTC)
        user = User(
            id=uuid4(),
            auth_provider_id=decoded.sub,
            email=decoded_email,
            display_name=decoded.name,
            role="admin" if is_admin else "reviewer",
            access_status="approved" if is_admin else "not_requested",
            access_reviewed_at=now if is_admin else None,
            access_requested_at=now if is_admin else None,
        )
        try:
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info(
                "Created new user",
                extra={"auth_provider_id": decoded.sub, "email": decoded.email},
            )
        except IntegrityError as e:
            await db.rollback()
            result = await db.execute(query)
            user = result.scalar_one_or_none()
            if user is None and decoded_email:
                email_query = select(User).where(
                    func.lower(User.email) == decoded_email
                )
                email_result = await db.execute(email_query)
                user = email_result.scalar_one_or_none()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Account creation failed, please try again",
                ) from e

    changed = False
    now = datetime.now(UTC)
    current_email = getattr(user, "email", "")
    if decoded_email and current_email.lower() != decoded_email:
        user.email = decoded_email
        changed = True
    if getattr(user, "auth_provider_id", None) != decoded.sub:
        user.auth_provider_id = decoded.sub
        changed = True
    if decoded.name and getattr(user, "display_name", None) != decoded.name:
        user.display_name = decoded.name
        changed = True

    if is_admin and getattr(user, "role", "reviewer") != "admin":
        user.role = "admin"
        changed = True
    if is_admin and getattr(user, "access_status", "not_requested") != "approved":
        user.access_status = "approved"
        user.access_reviewed_at = now
        user.access_reviewed_by = user.id
        changed = True

    if changed:
        await db.commit()
        await db.refresh(user)

    return user


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Get currently authenticated and approved user."""
    user = await get_authenticated_user(request, db, authorization)
    role = getattr(user, "role", "reviewer")
    access_status = getattr(user, "access_status", "approved")
    if role == "admin" or access_status == "approved":
        return user
    raise _pending_error()


async def get_admin_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Get currently authenticated admin user."""
    user = await get_authenticated_user(request, db, authorization)
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ADMIN_REQUIRED",
                "message": "Admin access required",
            },
        )
    return user


async def get_current_user_optional(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> User | None:
    """Get the current user if authenticated, None otherwise."""
    if not authorization:
        return None
    return await get_authenticated_user(request, db, authorization)


# Type aliases for dependency injection
AuthenticatedUser = Annotated[User, Depends(get_authenticated_user)]
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(get_admin_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]
