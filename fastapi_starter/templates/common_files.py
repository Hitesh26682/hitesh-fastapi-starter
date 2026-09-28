"""Common helper and utility templates for FastAPI Starter."""

def get_common_files() -> dict[str, str]:
    common_response_py = '''from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

# Standard HTTP Status Codes
HSC_200 = 200
HSC_201 = 201
HEC_400 = 400
HEC_401 = 401
HEC_403 = 403
HEC_404 = 404
HEC_429 = 429
HEC_500 = 500
HEC_503 = 503

# Standard Messages
HEM_INTERNAL_SERVER_ERROR = "Something went wrong. Please try again."
HEM_UNAUTHORIZED = "Your session has expired. Please login again."
HSM_SUCCESS = "success"
HEM_ERROR = "error"


def is_db_success(res: dict | None) -> bool:
    """Check if database query/function response is successful."""
    if not res or not isinstance(res, dict):
        return False
    if res.get("success") is False or res.get("status") in ("fail", "error"):
        return False
    return True


def db_error_message(res: dict | None, fallback: str = "Operation failed") -> str:
    """Extract human-readable error message from response dict."""
    if not isinstance(res, dict):
        return fallback
    return str(res.get("message") or res.get("msg") or fallback)


def successResponse(status_code: int = HSC_200, msg: str = "success", data=None):
    if data is None:
        data = {}

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "success",
            "message": msg,
            "data": jsonable_encoder(data),
        },
    )


def errorResponse(status_code: int = HEC_400, msg: str = "error", data=None):
    if data is None:
        data = {}

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "fail",
            "message": msg,
            "data": jsonable_encoder(data),
        },
    )
'''

    comman_function_py = '''import contextvars
import hashlib
import hmac
import json
import logging
import os
import re
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from concurrent_log_handler import ConcurrentTimedRotatingFileHandler
import bcrypt
import jwt
import pyotp
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, field_validator

from common.common_response import (
    HEC_400,
    HEC_401,
    HEM_UNAUTHORIZED,
    HSC_200,
    errorResponse,
    successResponse,
)
from config.config import settings
from shared.db import db

security = HTTPBearer()

client_ip_var = contextvars.ContextVar("client_ip", default="-")


class IPFilter(logging.Filter):
    def filter(self, record):
        record.client_ip = client_ip_var.get()
        record.display_name = normalize_logger_display_name(record.name, record.levelno)
        return True


def normalize_logger_display_name(name: str, levelno: int) -> str:
    if name == "uvicorn.error" and levelno < logging.ERROR:
        return "uvicorn"
    return name


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        if not hasattr(record, "display_name"):
            record.display_name = normalize_logger_display_name(record.name, record.levelno)
        client_ip = getattr(record, "client_ip", "-")
        level_color = {
            logging.DEBUG: "\\x1b[35m",
            logging.INFO: "\\x1b[32m",
            logging.WARNING: "\\x1b[33m",
            logging.ERROR: "\\x1b[31m",
            logging.CRITICAL: "\\x1b[41m\\x1b[37m",
        }.get(record.levelno, "\\x1b[37m")
        white = "\\x1b[37m"
        yellow = "\\x1b[33m"
        reset = "\\x1b[0m"
        log_fmt = (
            f"{level_color}%(asctime)s{reset} - {yellow}[{client_ip}]{reset} - "
            f"{white}[%(display_name)s]{reset} - {level_color}%(levelname)s - %(message)s"
        )
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", getattr(settings, "LOG_RETENTION_DAYS", 10)))
LOG_LEVEL = os.getenv("LOG_LEVEL", getattr(settings, "LOG_LEVEL", "INFO")).upper()
FILE_LOG_FORMAT = "%(asctime)s - [%(client_ip)s] - [%(display_name)s] - %(levelname)s - %(message)s"

try:
    os.makedirs(LOG_DIR, exist_ok=True)
except PermissionError:
    import tempfile
    LOG_DIR = os.path.join(tempfile.gettempdir(), "app-logs")
    os.makedirs(LOG_DIR, exist_ok=True)

UVICORN_LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {
        "uvicorn": {"handlers": [], "level": LOG_LEVEL, "propagate": True},
        "uvicorn.error": {"handlers": [], "level": LOG_LEVEL, "propagate": True},
        "uvicorn.access": {"handlers": [], "level": LOG_LEVEL, "propagate": True},
        "fastapi": {"handlers": [], "level": LOG_LEVEL, "propagate": True},
        "httpx": {"handlers": [], "level": "WARNING", "propagate": True},
        "asyncio": {"handlers": [], "level": "WARNING", "propagate": True},
    },
}


def setup_logger(name: str):
    root_logger = logging.getLogger()
    log_level = getattr(logging, LOG_LEVEL, logging.INFO)

    if not hasattr(root_logger, "_custom_handlers_set"):
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColoredFormatter())
        console_handler.addFilter(IPFilter())
        root_logger.addHandler(console_handler)

        try:
            log_dir = Path(LOG_DIR)
            log_dir.mkdir(exist_ok=True)
            file_handler = ConcurrentTimedRotatingFileHandler(
                filename=str(log_dir / "app.log"),
                when="midnight",
                interval=1,
                backupCount=LOG_RETENTION_DAYS,
                encoding="utf-8",
            )
            file_handler.suffix = "%Y-%m-%d"
            file_handler.setFormatter(logging.Formatter(FILE_LOG_FORMAT))
            file_handler.addFilter(IPFilter())
            root_logger.addHandler(file_handler)
        except Exception as e:
            sys.stderr.write(f"Error setting up file logging: {e}\\n")

        root_logger.setLevel(log_level)
        root_logger._custom_handlers_set = True

    logger_instance = logging.getLogger(name)
    logger_instance.setLevel(log_level)
    logger_instance.propagate = True

    if not any(isinstance(f, IPFilter) for f in logger_instance.filters):
        logger_instance.addFilter(IPFilter())

    return logger_instance


logger = setup_logger("app")
_active_logger = None


def set_active_logger(logger_instance):
    global _active_logger
    _active_logger = logger_instance


def get_active_logger():
    global _active_logger
    return _active_logger or logger


class SecurityBaseModel(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def validate_security(cls, v):
        return validate_json_security(v)


def validate_json_security(data):
    """Recursively block HTML/script injection in request payloads."""
    if isinstance(data, dict):
        for k, v in data.items():
            validate_json_security(k)
            validate_json_security(v)
    elif isinstance(data, list):
        for item in data:
            validate_json_security(item)
    elif isinstance(data, str):
        if re.search(r"<[^>]*[a-zA-Z]+[^>]*>", data):
            raise ValueError("Malicious code (HTML/Script) detected in input")
        if re.search(r"javascript\\s*:", data, re.IGNORECASE):
            raise ValueError("Javascript execution context detected in input")
    return data


def _get_peppered_password(password: str) -> bytes:
    secret = settings.SECRET_KEY.encode("utf-8")
    return hmac.new(secret, password.encode("utf-8"), hashlib.sha256).hexdigest().encode("utf-8")


def hash_password(password: str) -> str:
    pwd_bytes = _get_peppered_password(password)
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_byte_enc = _get_peppered_password(plain_password)
    hashed_password_byte_enc = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_byte_enc, hashed_password_byte_enc)


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def create_admin_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.ADMIN_JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_admin_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.ADMIN_JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def generate_temp_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_temp_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def verify_2fa_code(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code)


async def resolve_current_user(token: str) -> dict:
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=HEC_401,
            detail="Invalid or expired access token. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = payload.get("sub")
    user_id = payload.get("user_id")
    if not email or user_id is None:
        raise HTTPException(
            status_code=HEC_401,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "user_id": user_id,
        "email": email,
        "role": payload.get("role", "user"),
        **payload,
    }


async def get_current_user(auth: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    return await resolve_current_user(auth.credentials)


async def get_current_admin(auth: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = auth.credentials
    payload = decode_admin_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=HEC_401,
            detail=HEM_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = payload.get("sub")
    admin_id = payload.get("admin_id") or payload.get("id")
    if not email or admin_id is None:
        raise HTTPException(
            status_code=HEC_401,
            detail="Invalid admin token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "admin_id": admin_id,
        "email": email,
        "role": payload.get("role", "admin"),
        **payload,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database pool (if configured)...")
    try:
        await db.connect()
    except Exception as exc:
        logger.warning(f"Database connection note: {exc}")
    yield
    logger.info("Closing database pool...")
    try:
        await db.disconnect()
    except Exception:
        pass


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    if errors:
        msg = errors[0].get("msg", "Validation error")
        field = errors[0]["loc"][-1]
        full_msg = f"Invalid {field}: {msg}"
    else:
        full_msg = "Validation error"
    logger.warning("Validation error %s %s: %s", request.method, request.url.path, full_msg)
    return errorResponse(HEC_400, full_msg)


async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return errorResponse(exc.status_code, exc.detail)


async def global_exception_handler(request: Request, exc: Exception):
    client_ip = request.headers.get("X-Client-IP") or (request.client.host if request.client else "-")
    logger.error("Unhandled exception %s %s [IP=%s]: %s", request.method, request.url.path, client_ip, exc, exc_info=True)
    return errorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal Server Error")
'''

    redis_client_py = '''import os
import redis.asyncio as redis
from common.comman_function import get_active_logger
from config.config import settings

REDIS_URL = os.getenv("REDIS_URL", settings.REDIS_URL)
logger = get_active_logger()


class RedisClient:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        return cls._instance


async def get_redis_client():
    return RedisClient.get_instance()


async def check_cache(key: str):
    client = await get_redis_client()
    try:
        return await client.get(key)
    except Exception as e:
        logger.error("Redis get error for key=%s: %s", key, e)
        return None


async def set_cache(key: str, value: str, ttl: int | None = None):
    client = await get_redis_client()
    try:
        await client.setex(key, ttl if ttl is not None else settings.CACHE_TTL, value)
    except Exception as e:
        logger.error("Redis set error for key=%s: %s", key, e)


async def destroy_cache(key: str):
    client = await get_redis_client()
    try:
        await client.delete(key)
    except Exception as e:
        logger.error("Redis delete error for key=%s: %s", key, e)


async def destroy_cache_pattern(pattern: str):
    """Delete all keys matching a Redis glob pattern."""
    client = await get_redis_client()
    try:
        async for key in client.scan_iter(match=pattern):
            await client.delete(key)
    except Exception as e:
        logger.error("Redis pattern delete error for pattern=%s: %s", pattern, e)


async def publish_message(channel: str, message: str):
    client = await get_redis_client()
    try:
        await client.publish(channel, message)
    except Exception as e:
        logger.error("Redis publish error for channel=%s: %s", channel, e)
'''

    cache_py = '''"""Redis cache helpers and invalidation patterns."""

from __future__ import annotations
import json
from typing import Any
from fastapi.encoders import jsonable_encoder
from common.common_response import HSC_200, successResponse
from common.redis_client import check_cache, destroy_cache, destroy_cache_pattern, set_cache
from config.config import settings


def user_cache_key(user_id: int | str) -> str:
    return f"user:profile:{user_id}"


def admin_cache_key(admin_id: int | str) -> str:
    return f"admin:profile:{admin_id}"


async def cache_get(key: str) -> dict | None:
    raw = await check_cache(key)
    if not raw:
        return None
    try:
        payload = json.loads(raw)
        if isinstance(payload, dict):
            return payload
    except Exception:
        return None
    return None


async def cache_set(key: str, message: str, data: Any, ttl: int | None = None) -> None:
    payload = {
        "message": message,
        "data": jsonable_encoder(data),
    }
    await set_cache(key, json.dumps(payload), ttl=ttl or settings.CACHE_TTL)


async def from_cache(key: str):
    hit = await cache_get(key)
    if not hit:
        return None
    return successResponse(HSC_200, hit.get("message") or "OK", hit.get("data"))


async def invalidate(*keys: str) -> None:
    for key in keys:
        if key:
            await destroy_cache(key)


async def invalidate_pattern(pattern: str) -> None:
    await destroy_cache_pattern(pattern)
'''

    rate_limit_py = '''import inspect
import os
from functools import wraps
from fastapi import Depends, HTTPException, Request

from common.comman_function import get_active_logger
from common.common_response import HEC_429, errorResponse
from common.redis_client import get_redis_client

ENABLE_RATE_LIMIT = os.getenv("ENABLE_RATE_LIMIT", "True").lower() == "true"
logger = get_active_logger()


def client_ip_from_request(request: Request) -> str:
    forwarded = request.headers.get("X-Client-IP") or request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip() or "-"
    return request.client.host if request.client else "-"


async def enforce_rate_limit(request: Request, *, limit: int, window: int, scope: str | None = None) -> None:
    if not ENABLE_RATE_LIMIT:
        return

    client_ip = client_ip_from_request(request)
    path = scope or request.url.path
    key = f"rate_limit:{client_ip}:{path}"

    try:
        redis = await get_redis_client()
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window)
        if count > limit:
            logger.warning("Rate limit hit ip=%s path=%s count=%s/%s window=%ss", client_ip, path, count, limit, window)
            raise HTTPException(
                status_code=HEC_429,
                detail="Too many requests. Please try again later.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Rate limit skipped for %s %s: %s", request.method, path, exc)


def rate_limit_dep(limit: int, window: int, scope: str | None = None):
    async def _dependency(request: Request) -> None:
        await enforce_rate_limit(request, limit=limit, window=window, scope=scope)
    return Depends(_dependency)


def rate_limit(limit: int, window: int):
    """Endpoint decorator enforcing rate limits before execution."""
    def decorator(func):
        original_has_request = "request" in inspect.signature(func).parameters

        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Request | None = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            call_kwargs = kwargs
            if not original_has_request and "request" in kwargs:
                call_kwargs = {k: v for k, v in kwargs.items() if k != "request"}

            if ENABLE_RATE_LIMIT and request is not None:
                try:
                    await enforce_rate_limit(request, limit=limit, window=window)
                except HTTPException as exc:
                    return errorResponse(exc.status_code, exc.detail)

            return await func(*args, **call_kwargs)

        sig = inspect.signature(func)
        if not original_has_request:
            params = [
                inspect.Parameter("request", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Request),
                *sig.parameters.values(),
            ]
            wrapper.__signature__ = sig.replace(parameters=params)
        else:
            wrapper.__signature__ = sig

        return wrapper

    return decorator
'''

    security_py = '''import os
import re
from typing import Any
from fastapi import Header, UploadFile
from common.common_response import HEC_400, errorResponse

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


def valid_image_size(content_length: int = Header(None, alias="Content-Length")):
    max_size = 500 * 1024
    if content_length and content_length > max_size:
        return errorResponse(HEC_400, "Image size must be less than 500 KB.")


def validate_image_file(file: UploadFile, max_file_size: int = 500 * 1024):
    if not file or not file.filename:
        return {"status_code": HEC_400, "message": "No file uploaded or empty filename"}

    ext = os.path.splitext(file.filename)[1].lower()
    if not ext or ext not in ALLOWED_IMAGE_EXTENSIONS:
        return {"status_code": HEC_400, "message": f"Invalid file extension: {ext}. Only image files are allowed."}

    if file.content_type not in ALLOWED_IMAGE_MIME_TYPES:
        return {"status_code": HEC_400, "message": f"Invalid file type: {file.content_type}."}

    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > max_file_size:
        return {"status_code": HEC_400, "message": f"File size must be less than {int(max_file_size / 1024)} KB."}

    return True


def sanitize_html(text: str) -> str:
    if not isinstance(text, str):
        return text
    text = re.sub(r"<script.*?>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]*>", "", text)
    return text.strip()


def sanitize_data(data: Any) -> Any:
    """Recursively sanitizes input strings to strip unsafe HTML tags."""
    if isinstance(data, dict):
        return {k: sanitize_data(v) for k, v in data.items()}
    if isinstance(data, list):
        return [sanitize_data(item) for item in data]
    if isinstance(data, str):
        return sanitize_html(data)
    return data
'''

    db_functions_py = '''"""Generic database query and procedure execution wrappers."""

from __future__ import annotations
import traceback
from common.comman_function import get_active_logger
from common.common_response import (
    HEC_500,
    HEM_INTERNAL_SERVER_ERROR,
    HSC_200,
    errorResponse,
    successResponse,
)
from shared.db import db

logger = get_active_logger()


async def db_call(query: str, *args):
    """Generic query executor returning fetched rows."""
    try:
        return await db.fetch(query, *args)
    except Exception as exc:
        logger.error(f"Database error executing query: {exc}")
        return None


async def run_db_function(function_name: str, **kwargs):
    """Generic PostgreSQL stored procedure caller."""
    try:
        res = await db.call_function(function_name, **kwargs)
        return successResponse(HSC_200, "Operation completed", res)
    except Exception as exc:
        traceback.print_exc()
        logger.error(f"Error calling database function {function_name}: {exc}")
        return errorResponse(HEC_500, HEM_INTERNAL_SERVER_ERROR)
'''

    health_py = '''"""Health checks for gateway, microservices, and redis."""

from __future__ import annotations
import asyncio
import os
import httpx

from common.common_response import HEC_503, HSC_200, errorResponse, successResponse
from common.redis_client import get_redis_client
from config.config import settings


def _service_urls() -> dict[str, str]:
    return {
        "auth": os.getenv("AUTH_SERVICE_URL", settings.AUTH_SERVICE_URL),
        "user": os.getenv("USER_SERVICE_URL", settings.USER_SERVICE_URL),
        "admin": os.getenv("ADMIN_SERVICE_URL", settings.ADMIN_SERVICE_URL),
    }


async def _ping_http_service(client: httpx.AsyncClient, name: str, base_url: str) -> dict:
    last_error = "unreachable"
    for path in ("/openapi.json", "/"):
        try:
            response = await client.get(f"{base_url.rstrip('/')}{path}")
            if response.status_code < 500:
                return {"service": name, "status": "ok"}
            last_error = f"HTTP {response.status_code}"
        except httpx.RequestError as exc:
            last_error = str(exc)
    return {"service": name, "status": "not working", "error": last_error}


async def _ping_redis() -> dict:
    try:
        client = await get_redis_client()
        if await client.ping():
            return {"service": "redis", "status": "ok"}
    except Exception as exc:
        return {"service": "redis", "status": "not working", "error": str(exc)}
    return {"service": "redis", "status": "not working", "error": "ping failed"}


async def check_all_services() -> dict:
    services = _service_urls()
    timeout = httpx.Timeout(3.0, connect=2.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        http_tasks = [_ping_http_service(client, name, url) for name, url in services.items()]
        http_results = await asyncio.gather(*http_tasks)

    redis_result = await _ping_redis()
    results = {item["service"]: item for item in http_results}
    results["redis"] = redis_result
    results["gateway"] = {"service": "gateway", "status": "ok"}

    unhealthy = [name for name, item in results.items() if item.get("status") != "ok"]
    all_healthy = len(unhealthy) == 0

    summary = {
        "all_healthy": all_healthy,
        "services": results,
    }

    if all_healthy:
        return successResponse(HSC_200, "All services are running", summary)

    return errorResponse(HEC_503, f"Services not working: {', '.join(unhealthy)}", summary)
'''

    metrics_py = '''"""Lightweight in-process metrics for gateway observability."""

from __future__ import annotations
import time
from collections import defaultdict
from threading import Lock

_lock = Lock()
_counters: dict[str, float] = defaultdict(float)
_gauges: dict[str, float] = defaultdict(float)
_started = time.time()


def incr(name: str, value: float = 1.0) -> None:
    with _lock:
        _counters[name] += value


def set_gauge(name: str, value: float) -> None:
    with _lock:
        _gauges[name] = value


def observe_ms(name: str, ms: float) -> None:
    with _lock:
        _counters[f"{name}_count"] += 1
        _counters[f"{name}_sum_ms"] += ms


def snapshot() -> dict:
    with _lock:
        return {
            "uptime_seconds": round(time.time() - _started, 1),
            "counters": dict(_counters),
            "gauges": dict(_gauges),
        }


def render_prometheus() -> str:
    lines = []
    with _lock:
        lines.append(f"# TYPE process_uptime_seconds gauge")
        lines.append(f"process_uptime_seconds {round(time.time() - _started, 1)}")
        for name, val in _counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {val}")
        for name, val in _gauges.items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {val}")
    return "\\n".join(lines) + "\\n"
'''

    return {
        "common/__init__.py": "",
        "common/common_response.py": common_response_py,
        "common/comman_function.py": comman_function_py,
        "common/redis_client.py": redis_client_py,
        "common/cache.py": cache_py,
        "common/rate_limit.py": rate_limit_py,
        "common/security.py": security_py,
        "common/db_functions.py": db_functions_py,
        "common/health.py": health_py,
        "common/metrics.py": metrics_py,
    }
