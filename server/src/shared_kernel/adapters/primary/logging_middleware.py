import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from shared_kernel.adapters.primary.request_context import request_id_var

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path == "/health" or request.url.path == "/api/health":
            return await call_next(request)

        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        token = request_id_var.set(request_id)

        try:
            start = time.perf_counter()
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start) * 1000

            if duration_ms > 500:
                logger.warning(
                    "slow request",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "status": response.status_code,
                        "duration_ms": round(duration_ms),
                    },
                )
            else:
                logger.info(
                    "request completed",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "status": response.status_code,
                        "duration_ms": round(duration_ms),
                    },
                )
            return response
        finally:
            request_id_var.reset(token)
