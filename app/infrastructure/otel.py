import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.infrastructure.config import settings

logger = structlog.get_logger()


def init_tracer():
    if not settings.ENABLE_OTEL:
        logger.info("OpenTelemetry tracing is disabled.")
        return

    logger.info(
        "Initializing OpenTelemetry tracer",
        service_name=settings.OTEL_SERVICE_NAME,
        endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
    )

    # Define Resource
    resource = Resource.create(
        attributes={
            "service.name": settings.OTEL_SERVICE_NAME,
            "compose_service": settings.OTEL_SERVICE_NAME,
        }
    )

    # Define Tracer Provider
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(
        OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)
    )
    provider.add_span_processor(processor)

    # Set Global Tracer Provider
    trace.set_tracer_provider(provider)


def instrument_fastapi_app(app):
    if not settings.ENABLE_OTEL:
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI app instrumented with OpenTelemetry")
    except Exception as e:
        logger.error(
            "Failed to instrument FastAPI app with OpenTelemetry", error=str(e)
        )


def instrument_celery_worker():
    if not settings.ENABLE_OTEL:
        return
    try:
        from opentelemetry.instrumentation.celery import CeleryInstrumentor

        CeleryInstrumentor().instrument()
        logger.info("Celery worker instrumented with OpenTelemetry")
    except Exception as e:
        logger.error(
            "Failed to instrument Celery worker with OpenTelemetry", error=str(e)
        )
