"""Authentication dependencies for FastAPI endpoints."""

import logging
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.jwt import TokenVerificationError, verify_token
from src.db.database import get_db
from src.db.models import User

logger = logging.getLogger(__name__)


async def get_current_user(
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
        logger.error("Token verification infrastructure error: %s", e)
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

    # Look up user by auth provider ID
    query = select(User).where(User.auth_provider_id == decoded.sub)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    # Fallback lookup by email
    if user is None and decoded.email:
        email_query = select(User).where(
            func.lower(User.email) == decoded.email.lower()
        )
        email_result = await db.execute(email_query)
        user = email_result.scalar_one_or_none()

    # Auto-create user on first login
    if user is None:
        if not decoded.email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email required for account creation",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = User(
            id=uuid4(),
            auth_provider_id=decoded.sub,
            email=decoded.email,
            display_name=decoded.name,
            role="reviewer",
        )
        try:
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info("Created new user: %s", decoded.sub)
        except IntegrityError as e:
            await db.rollback()
            result = await db.execute(query)
            user = result.scalar_one_or_none()
            if user is None and decoded.email:
                email_query = select(User).where(
                    func.lower(User.email) == decoded.email.lower()
                )
                email_result = await db.execute(email_query)
                user = email_result.scalar_one_or_none()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Account creation failed, please try again",
                ) from e

    return user


async def get_current_user_optional(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> User | None:
    """Get the current user if authenticated, None otherwise."""
    if not authorization:
        return None
    return await get_current_user(request, db, authorization)


# Type aliases for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]
