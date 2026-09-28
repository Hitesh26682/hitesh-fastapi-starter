"""Middleware templates for FastAPI Starter."""

def get_middleware_files() -> dict[str, str]:
    rate_limit_py = '''"""Gateway request flood protection — Redis sliding counter."""

from __future__ import annotations

import os
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from common.comman_function import get_active_logger
from common import metrics as metrics_mod

logger = get_active_logger()

ENABLE_RATE_LIMIT = os.getenv("ENABLE_RATE_LIMIT", "True").lower() == "true"
DEFAULT_LIMIT = int(os.getenv("GATEWAY_RATE_LIMIT", "120"))
DEFAULT_WINDOW = int(os.getenv("GATEWAY_RATE_WINDOW", "60"))

STRICT_LIMITS: dict[str, tuple[int, int]] = {
    "/user/get-user": (30, 60),
    "/auth/login": (10, 60),
    "/auth/register": (5, 60),
    "/admin/auth/login": (5, 60),
}


class GatewayRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Redis-backed fixed-window limiter at the gateway.
    Falls back to allow-on-Redis-error so API stays up if Redis is temporarily unreachable.
    """

    def __init__(self, app, *, default_limit: int = DEFAULT_LIMIT, default_window: int = DEFAULT_WINDOW):
        super().__init__(app)
        self.default_limit = default_limit
        self.default_window = default_window
        self._last_log: dict[str, float] = {}

    def _client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For") or request.headers.get("X-Client-IP")
        if forwarded:
            return forwarded.split(",")[0].strip() or "-"
        return request.client.host if request.client else "-"

    def _limits_for(self, path: str) -> tuple[int, int]:
        if path in STRICT_LIMITS:
            return STRICT_LIMITS[path]
        for prefix, limits in STRICT_LIMITS.items():
            if path.startswith(prefix):
                return limits
        return self.default_limit, self.default_window

    def _log_throttled(self, key: str, client_ip: str, path: str, limit: int, window: int) -> None:
        now = time.monotonic()
        last = self._last_log.get(key, 0.0)
        if now - last < 5.0:
            return
        self._last_log[key] = now
        logger.warning(
            "Gateway rate limit ip=%s path=%s limit=%s/%ss",
            client_ip,
            path,
            limit,
            window,
        )

    async def _allowed_redis(self, key: str, limit: int, window: int) -> bool:
        from common.redis_client import get_redis_client

        redis = await get_redis_client()
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window)
        return count <= limit

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not ENABLE_RATE_LIMIT or request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        if path in ("/health", "/live", "/ready", "/metrics", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        client_ip = self._client_ip(request)
        limit, window = self._limits_for(path)
        key = f"gw_rate:{client_ip}:{path}"

        try:
            allowed = await self._allowed_redis(key, limit, window)
        except Exception as exc:
            logger.warning("Gateway rate limit Redis error (allowing request): %s", exc)
            allowed = True

        if not allowed:
            self._log_throttled(key, client_ip, path, limit, window)
            metrics_mod.incr("http_rate_limited")
            return JSONResponse(
                status_code=429,
                content={
                    "status": "fail",
                    "code": "TOO_MANY_REQUESTS",
                    "message": "Too many requests. Please try again later.",
                    "data": None,
                },
            )

        return await call_next(request)
'''

    security_py = '''import json
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from common.comman_function import client_ip_var
from common.security import sanitize_data


class SafetyMiddleware(BaseHTTPMiddleware):
    """Sanitize incoming JSON request bodies to prevent XSS/script injection."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = request.headers.get("X-Client-IP") or (request.client.host if request.client else "-")
        token = client_ip_var.set(client_ip)

        try:
            content_type = request.headers.get("content-type", "").lower()
            if request.method in ["POST", "PUT", "PATCH"] and "application/json" in content_type:
                try:
                    body = await request.body()
                    if body:
                        raw_data = json.loads(body)
                        sanitized_data = sanitize_data(raw_data)

                        async def receive():
                            return {"type": "http.request", "body": json.dumps(sanitized_data).encode("utf-8")}

                        request._receive = receive
                except Exception:
                    pass

            return await call_next(request)
        finally:
            client_ip_var.reset(token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforce security headers on all HTTP responses."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
'''

    return {
        "middleware/__init__.py": "",
        "middleware/rate_limit.py": rate_limit_py,
        "middleware/security.py": security_py,
    }
