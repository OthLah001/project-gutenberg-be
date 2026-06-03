import logging
from opentelemetry import trace


logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class OTelExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)

        except Exception as exc:
            span = trace.get_current_span()

            # Mark span as error
            if span:
                span.record_exception(exc)
                span.set_status(trace.Status(trace.StatusCode.ERROR))

            # Log exception with trace correlation
            logger.exception("Unhandled exception in request")

            raise