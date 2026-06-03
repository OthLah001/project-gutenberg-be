import logging
from opentelemetry.trace import get_current_span


class OpenTelemetryContextFilter(logging.Filter):
    def filter(self, record):
        span = get_current_span()
        ctx = span.get_span_context()

        if ctx and ctx.is_valid:
            record.trace_id = format(ctx.trace_id, "032x")
            record.span_id = format(ctx.span_id, "016x")
        else:
            record.trace_id = None
            record.span_id = None

        return True