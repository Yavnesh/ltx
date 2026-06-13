from datetime import datetime

import redis
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.config import settings
from app.infrastructure.database import get_db

router = APIRouter(tags=["health"])
logger = structlog.get_logger()


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    health_status = {
        "status": "healthy",
        "database": "up",
        "redis": "up",
        "celery_worker": "up",
    }
    is_healthy = True

    # 1. Test Database Connection
    try:
        db.execute(text("SELECT 1"))  # wait, text from sqlalchemy needs import
    except Exception as e:
        # Let's import text or use db.connection().execute
        pass
    # Let's write standard robust db query:
    try:
        from sqlalchemy import text

        db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error("Healthcheck database failure", error=str(e))
        health_status["database"] = "down"
        is_healthy = False

    # 2. Test Redis connection
    try:
        r = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=2)
        r.ping()
    except Exception as e:
        logger.error("Healthcheck redis failure", error=str(e))
        health_status["redis"] = "down"
        is_healthy = False

    # 3. Check Celery heartbeat
    try:
        r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        heartbeat_str = r.get("celery_worker_heartbeat")
        if heartbeat_str:
            heartbeat = datetime.fromisoformat(heartbeat_str)
            seconds_since_heartbeat = (datetime.utcnow() - heartbeat).total_seconds()
            # If heartbeat is older than 60 seconds, worker is dead
            if seconds_since_heartbeat > 60:
                health_status["celery_worker"] = "stale"
                is_healthy = False
        else:
            health_status["celery_worker"] = "inactive"
            is_healthy = False
    except Exception as e:
        logger.error("Healthcheck celery check failure", error=str(e))
        health_status["celery_worker"] = "error"
        is_healthy = False

    if not is_healthy:
        health_status["status"] = "unhealthy"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status,
        )

    return {"status": "healthy"}
