from ninja import NinjaAPI
import logging
from opentelemetry import trace
from config.ninja_utils.errors import NinjaError


logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class AppNinjaAPI(NinjaAPI):
    """NinjaAPI with shared exception handlers for all app APIs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_exception_handler(Exception, self._handle_exception)
        self.add_exception_handler(NinjaError, self._handle_ninja_error)

    def _handle_exception(self, request, exc: Exception):
        # Handle exceptions just for Logging
        span = trace.get_current_span()
        if span and span.is_recording():
            span.record_exception(exc)
            span.set_status(trace.Status(trace.StatusCode.ERROR))

        # Log exception with trace correlation
        logger.exception("Unhandled API exception")

        raise exc # Fall off to Django's default exception handler

    def _handle_ninja_error(self, request, exc: NinjaError):
        return self.create_response(
            request,
            {"error_name": exc.error_name, "message": exc.message},
            status=exc.status_code,
        )
