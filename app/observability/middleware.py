import logging
from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging import request_id_context
from app.observability.metrics import HTTP_LATENCY, HTTP_REQUESTS

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        token = request_id_context.set(request_id)
        started = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            elapsed = perf_counter() - started
            route = request.scope.get("route")
            path = getattr(route, "path", request.url.path)
            HTTP_REQUESTS.labels(request.method, str(status_code)).inc()
            HTTP_LATENCY.labels(request.method, path).observe(elapsed)
            logger.info(
                "request_completed",
                extra={"event": "http_request", "status": status_code},
            )
            request_id_context.reset(token)
