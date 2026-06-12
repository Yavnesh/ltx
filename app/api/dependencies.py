import time
from uuid import UUID
import redis
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.infrastructure.config import settings
from app.infrastructure.database import get_db
from app.infrastructure.models import User
from app.infrastructure.security import verify_token
from app.services.user_service import UserService

logger = structlog.get_logger()

# Security scheme
security = HTTPBearer()

# Redis connection for Rate Limiter
try:
    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception as e:
    logger.error("Failed to connect to Redis for Rate Limiting", error=str(e))
    redis_client = None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    user_id_str = verify_token(token)
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_service = UserService(db)
    user = user_service.get_user_by_id(UUID(user_id_str))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def check_rate_limit(user: User = Depends(get_current_user)) -> None:
    """Enforce a rate limit of 100 requests/hour/user using a Redis sliding window."""
    if not redis_client:
        # Fail open if Redis is down, but log warning
        logger.warning("Redis client unavailable; skipping rate limit check")
        return

    user_key = f"rate_limit:{user.id}"
    now = time.time()
    one_hour_ago = now - 3600

    try:
        pipeline = redis_client.pipeline()
        # Remove requests older than 1 hour
        pipeline.zremrangebyscore(user_key, 0, one_hour_ago)
        # Add current request timestamp
        pipeline.zadd(user_key, {str(now): now})
        # Get total requests in the window
        pipeline.zcard(user_key)
        # Set expiration on key to clean up inactive users after 1 hour
        pipeline.expire(user_key, 3600)

        _, _, request_count, _ = pipeline.execute()

        # Enforce rate limit (100 requests / hour)
        if request_count > 100:
            logger.warning("Rate limit exceeded for user", user_id=str(user.id), count=request_count)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Maximum 100 requests per hour.",
            )

    except HTTPException:
        raise
    except Exception as e:
        # Fail open, log error
        logger.error("Error running rate limiter", error=str(e))
        return
