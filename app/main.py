from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.api import health
from app.api.v1 import auth, videos
from app.api.middleware import LoggingAndMetricsMiddleware, update_system_metrics
from app.infrastructure.config import settings
from app.infrastructure.logging import configure_logging
from app.infrastructure.otel import init_tracer, instrument_fastapi_app

# 1. Configure logging immediately
configure_logging()

# 2. Init OpenTelemetry Tracer
init_tracer()

# 3. Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Scalable Video Generation Platform around LTX Video",
    version="1.0.0",
)

# 4. Add middleware
app.add_middleware(LoggingAndMetricsMiddleware)

# 5. Register routers
app.include_router(health.router)
app.include_router(auth.router, prefix="/v1")
app.include_router(videos.router, prefix="/v1")

# 6. Instrument app with OpenTelemetry
instrument_fastapi_app(app)


# 7. Mount static file serving for local storage provider
if settings.STORAGE_PROVIDER_TYPE.lower() == "local":
    import os

    os.makedirs(settings.STORAGE_LOCAL_PATH, exist_ok=True)
    app.mount(
        "/static", StaticFiles(directory=settings.STORAGE_LOCAL_PATH), name="static"
    )


@app.get("/metrics")
def get_metrics():
    """Endpoint scraped by Prometheus to retrieve system metrics."""
    update_system_metrics()
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
