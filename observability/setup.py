from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

from observability.otel import setup_otel, setup_otel_logs

_instrumented = False


def setup_observability() -> None:
    global _instrumented
    if _instrumented:
        return

    DjangoInstrumentor().instrument()
    CeleryInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    Psycopg2Instrumentor().instrument()
    _instrumented = True


def bootstrap_observability() -> None:
    from config import settings

    if settings.OTEL_ENABLE_TRACING:
        setup_otel()
        setup_otel_logs()
        setup_observability()
