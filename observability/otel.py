from django.conf import settings

from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
    DEFAULT_LOGS_EXPORT_PATH,
    OTLPLogExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    DEFAULT_TRACES_EXPORT_PATH,
    OTLPSpanExporter,
)
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_resource: Resource | None = None
_traces_initialized = False
_logs_initialized = False


def _resource_instance() -> Resource:
    global _resource
    if _resource is None:
        _resource = Resource.create({"service.name": settings.OTEL_SERVICE_NAME})
    return _resource


def _otlp_headers() -> dict[str, str]:
    return {"Authorization": f"Basic {settings.OTEL_EXPORTER_OTLP_TOKEN}"}


def _traces_endpoint(base_endpoint: str) -> str:
    endpoint = base_endpoint.rstrip("/")
    if endpoint.endswith(DEFAULT_TRACES_EXPORT_PATH):
        return endpoint
    return f"{endpoint}/{DEFAULT_TRACES_EXPORT_PATH}"


def _logs_endpoint(base_endpoint: str) -> str:
    endpoint = base_endpoint.rstrip("/")
    if endpoint.endswith(DEFAULT_LOGS_EXPORT_PATH):
        return endpoint
    return f"{endpoint}/{DEFAULT_LOGS_EXPORT_PATH}"


def setup_otel() -> None:
    global _traces_initialized
    if _traces_initialized:
        return

    provider = TracerProvider(resource=_resource_instance())
    trace.set_tracer_provider(provider)

    otlp_exporter = OTLPSpanExporter(
        endpoint=_traces_endpoint(settings.OTEL_EXPORTER_OTLP_ENDPOINT),
        headers=_otlp_headers(),
    )
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    _traces_initialized = True


def setup_otel_logs() -> None:
    global _logs_initialized
    if _logs_initialized:
        return

    provider = LoggerProvider(resource=_resource_instance())
    set_logger_provider(provider)

    otlp_exporter = OTLPLogExporter(
        endpoint=_logs_endpoint(settings.OTEL_EXPORTER_OTLP_ENDPOINT),
        headers=_otlp_headers(),
    )
    provider.add_log_record_processor(BatchLogRecordProcessor(otlp_exporter))
    _logs_initialized = True
