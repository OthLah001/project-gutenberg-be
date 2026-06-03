from django.conf import settings

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    DEFAULT_TRACES_EXPORT_PATH,
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_initialized = False


def _traces_endpoint(base_endpoint: str) -> str:
    endpoint = base_endpoint.rstrip("/")
    if endpoint.endswith(DEFAULT_TRACES_EXPORT_PATH):
        return endpoint
    return f"{endpoint}/{DEFAULT_TRACES_EXPORT_PATH}"


def setup_otel() -> None:
    global _initialized
    if _initialized:
        return

    resource = Resource.create({"service.name": "django-app"})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    otlp_exporter = OTLPSpanExporter(
        endpoint=_traces_endpoint(settings.OTEL_EXPORTER_OTLP_ENDPOINT),
        headers={
            "Authorization": f"Basic {settings.OTEL_EXPORTER_OTLP_TOKEN}",
        },
    )
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    _initialized = True
