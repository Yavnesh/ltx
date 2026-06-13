import time
import uuid

import redis
import structlog
from fastapi import Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware

from app.infrastructure.config import settings
from app.infrastructure.security import verify_token

logger = structlog.get_logger()

# Prometheus Metrics
HTTP_REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests.",
    ["method", "endpoint", "status"],
)

HTTP_REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "endpoint"],
)

CELERY_QUEUE_SIZE = Gauge(
    "celery_queue_size", "Current number of tasks in the Celery queue.", ["queue_name"]
)

CELERY_ACTIVE_WORKERS = Gauge(
    "celery_active_workers_count", "Number of active Celery workers."
)

GPU_UTILIZATION = Gauge("gpu_utilization_ratio", "Mock or real GPU utilization ratio.")


class LoggingAndMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()

        # Generate unique request_id
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        # Try to extract user_id from JWT token for logging
        user_id = "anonymous"
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            extracted_uid = verify_token(token)
            if extracted_uid:
                user_id = extracted_uid

        endpoint = request.url.path

        # Process the request
        response = await call_next(request)

        # Record metrics & logs (except for health and metrics endpoints)
        if endpoint not in ("/metrics", "/health"):
            duration_s = time.perf_counter() - start_time
            duration_ms = int(duration_s * 1000)

            # Record Prometheus Metrics
            HTTP_REQUEST_COUNT.labels(
                method=request.method, endpoint=endpoint, status=response.status_code
            ).inc()

            HTTP_REQUEST_LATENCY.labels(
                method=request.method, endpoint=endpoint
            ).observe(duration_s)

            # Structured Log output as requested
            logger.info(
                "Request processed",
                request_id=request_id,
                user_id=user_id,
                endpoint=endpoint,
                method=request.method,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

        # Inject request ID into response headers
        response.headers["X-Request-ID"] = request_id
        return response


def update_system_metrics():
    """Poll Celery/Redis & GPU details to update Prometheus gauges."""
    # 1. Update queue size
    try:
        r = redis.Redis.from_url(settings.REDIS_URL)
        # Redis lists length for the 'default' queue
        q_len = r.llen("default")
        CELERY_QUEUE_SIZE.labels(queue_name="default").set(q_len)
    except Exception:
        pass

    # 2. Update active workers (mock worker count or fetch from redis heartbeat)
    try:
        r = redis.Redis.from_url(settings.REDIS_URL)
        # If heartbeat in past 60s, worker is active
        heartbeat = r.get("celery_worker_heartbeat")
        if heartbeat:
            # Simple binary check
            CELERY_ACTIVE_WORKERS.set(1)
        else:
            CELERY_ACTIVE_WORKERS.set(0)
    except Exception:
        pass

    # 3. Update GPU utilization (Mock or read via nvidia-smi if available)
    try:
        import torch

        if torch.cuda.is_available():
            # Real GPU utilization approximation (memory used ratio)
            device = torch.cuda.current_device()
            total_mem = torch.cuda.get_device_properties(device).total_memory
            allocated_mem = torch.cuda.memory_allocated(device)
            GPU_UTILIZATION.set(allocated_mem / total_mem if total_mem > 0 else 0.0)
        else:
            GPU_UTILIZATION.set(0.0)
    except Exception:
        GPU_UTILIZATION.set(0.0)
