"""Root configuration and gateway templates for FastAPI Starter."""

def get_root_files(project_name: str) -> dict[str, str]:
    db_name = project_name.lower().replace("-", "_")

    env_example = f'''# ================================================================
# {project_name.upper()} Environment Configuration
# ================================================================

# Database Configuration (PostgreSQL with asyncpg)
DATABASE_URL=postgresql://postgres:password@localhost:5432/{db_name}_db
DB_POOL_MIN=5
DB_POOL_MAX=20

# JWT & Application Security Keys (Change these in production!)
SECRET_KEY=change_this_to_a_secure_app_secret_key_in_production
JWT_SECRET_KEY=change_this_to_a_secure_jwt_secret_in_production
ADMIN_JWT_SECRET_KEY=change_this_to_a_secure_admin_jwt_secret_in_production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Redis & Caching
REDIS_URL=redis://127.0.0.1:6379/0
REDIS_PORT=6379
CACHE_TTL=60

# Rate Limiting
ENABLE_RATE_LIMIT=true
GATEWAY_RATE_LIMIT=120
GATEWAY_RATE_WINDOW=60

# Developer Options
ENABLE_TEMP_DEV_TOKEN=true
TEMP_DEV_TOKEN_PASSWORD=Dev@12345

# Logging
LOG_LEVEL=INFO
LOG_RETENTION_DAYS=10

# Gateway + Microservices Ports
GATEWAY_PORT=7060
AUTH_PORT=7001
USER_PORT=7002
ADMIN_PORT=7004

# Service URLs (for Gateway proxy)
AUTH_SERVICE_URL=http://127.0.0.1:7001
USER_SERVICE_URL=http://127.0.0.1:7002
ADMIN_SERVICE_URL=http://127.0.0.1:7004

# Workers
GATEWAY_WORKERS=1
SERVICE_WORKERS=2
'''

    dockerignore = '''# Git
.git
.gitignore

# Python
venv/
.venv/
env/
__pycache__/
**/__pycache__/
*.py[cod]
*.egg-info/
.mypy_cache/
.ruff_cache/
.pytest_cache/
.coverage
htmlcov/

# Secrets & local runtime
.env
.env.*
!.env.example
/logs/
*.log
/redis-data/
dump.rdb
*.pid

# IDE
.idea/
.vscode/
.DS_Store
'''

    dockerfile = f'''FROM python:3.11-slim

WORKDIR /app

# System dependencies + Redis
RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    libc6-dev \\
    redis-server \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

COPY requirement.txt .
RUN pip install --no-cache-dir -r requirement.txt

COPY . .

ENV PYTHONUNBUFFERED=1 \\
    WORKERS=1 \\
    REDIS_URL=redis://127.0.0.1:6379/0 \\
    AUTH_SERVICE_URL=http://127.0.0.1:7001 \\
    USER_SERVICE_URL=http://127.0.0.1:7002 \\
    ADMIN_SERVICE_URL=http://127.0.0.1:7004 \\
    GATEWAY_PORT=7060 \\
    AUTH_PORT=7001 \\
    USER_PORT=7002 \\
    ADMIN_PORT=7004

EXPOSE 7060 7001 7002 7004 6379

CMD ["python", "run_internal_services.py"]
'''

    requirements_txt = '''fastapi>=0.110.0,<1.0.0
uvicorn[standard]>=0.28.0
pydantic[email]>=2.6.0
python-dotenv>=1.0.0
asyncpg>=0.29.0
redis>=5.0.0
PyJWT>=2.8.0
bcrypt>=4.1.0
pyotp>=2.9.0
httpx>=0.27.0
loguru>=0.7.2
concurrent-log-handler>=0.9.24
python-multipart>=0.0.9
cryptography>=42.0.0
'''

    run_internal_services_py = '''"""
Internal services orchestrator.
Starts Redis (if needed) + Auth + User + Admin services + Gateway in one process.

Usage:
    python run_internal_services.py
"""

import os
import signal
import socket
import subprocess
import sys
import time

from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0")
os.environ.setdefault("AUTH_SERVICE_URL", "http://127.0.0.1:7001")
os.environ.setdefault("USER_SERVICE_URL", "http://127.0.0.1:7002")
os.environ.setdefault("ADMIN_SERVICE_URL", "http://127.0.0.1:7004")

GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", "7060"))
AUTH_PORT = int(os.getenv("AUTH_PORT", "7001"))
USER_PORT = int(os.getenv("USER_PORT", "7002"))
ADMIN_PORT = int(os.getenv("ADMIN_PORT", "7004"))
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

SERVICE_WORKERS = os.getenv("SERVICE_WORKERS", os.getenv("WORKERS", "2"))
GATEWAY_WORKERS = os.getenv("GATEWAY_WORKERS", "1")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REDIS_DATA_DIR = os.getenv("REDIS_DATA_DIR", os.path.join(BASE_DIR, "redis-data"))

services = [
    {
        "name": "redis",
        "type": "command",
        "cmd": [
            "redis-server",
            "--port",
            str(REDIS_PORT),
            "--daemonize",
            "no",
            "--bind",
            "127.0.0.1",
            "--protected-mode",
            "no",
            "--dir",
            REDIS_DATA_DIR,
            "--pidfile",
            os.path.join(REDIS_DATA_DIR, "redis.pid"),
            "--logfile",
            "",
            "--save",
            "",
        ],
    },
    {"name": "auth", "port": AUTH_PORT, "module": "app.auth.auth_main"},
    {"name": "user", "port": USER_PORT, "module": "app.user.user_main"},
    {"name": "admin", "port": ADMIN_PORT, "module": "app.admin.admin_main"},
    {"name": "gateway", "port": GATEWAY_PORT, "module": "main"},
]

processes: list[tuple[str, subprocess.Popen]] = []


def _redis_ready(host: str = "127.0.0.1", port: int = REDIS_PORT) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5) as sock:
            sock.sendall(b"PING\\r\\n")
            return sock.recv(16).startswith(b"+PONG")
    except OSError:
        return False


def _wait_redis(proc: subprocess.Popen | None, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:
            raise RuntimeError(f"redis-server exited early (code={proc.returncode})")
        if _redis_ready():
            print(f"Redis is ready on 127.0.0.1:{REDIS_PORT}")
            return
        time.sleep(0.2)
    raise RuntimeError(f"Redis failed to start on 127.0.0.1:{REDIS_PORT}")


def start_services():
    print("=" * 60)
    print("Starting all microservices & API Gateway...")
    print(f"Gateway: {GATEWAY_PORT} | Auth: {AUTH_PORT} | User: {USER_PORT} | Admin: {ADMIN_PORT}")
    print("=" * 60)

    os.makedirs(REDIS_DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)

    for service in services:
        if service.get("type") == "command":
            if _redis_ready():
                print(f"[OK] Using existing Redis on 127.0.0.1:{REDIS_PORT}")
                continue
            print(f"Starting {service['name']}...")
            try:
                p = subprocess.Popen(service["cmd"], cwd=BASE_DIR)
                processes.append((service["name"], p))
                _wait_redis(p)
            except FileNotFoundError:
                print(f"[WARNING] redis-server executable not found. Ensure Redis is running on port {REDIS_PORT}.")
            continue

        workers = GATEWAY_WORKERS if service["name"] == "gateway" else SERVICE_WORKERS
        print(f"Starting {service['name']} service on port {service['port']} (workers={workers})...")
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            f"{service['module']}:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(service["port"]),
            "--workers",
            str(workers),
        ]
        p = subprocess.Popen(cmd, cwd=BASE_DIR)
        processes.append((service["name"], p))
        time.sleep(0.3)

    print("\\n" + "=" * 60)
    print(f"🚀 Swagger Docs available at: http://127.0.0.1:{GATEWAY_PORT}/docs")
    print(f"🏥 Health Check endpoint:    http://127.0.0.1:{GATEWAY_PORT}/health")
    print(f"📊 Observability Metrics:    http://127.0.0.1:{GATEWAY_PORT}/metrics")
    print("=" * 60)
    print("All services are running. Press Ctrl+C to terminate.")


def stop_services():
    print("\\nTerminating all services...")
    for name, p in reversed(processes):
        if p.poll() is None:
            print(f"Stopping {name} (pid={p.pid})...")
            p.terminate()

    deadline = time.time() + 6
    for name, p in processes:
        try:
            p.wait(timeout=max(0.1, deadline - time.time()))
        except subprocess.TimeoutExpired:
            print(f"Force killing {name} (pid={p.pid})...")
            p.kill()


def _handle_signal(_signum, _frame):
    stop_services()
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    try:
        start_services()
        while True:
            for name, p in processes:
                code = p.poll()
                if code is not None:
                    print(f"\\nService '{name}' exited with code {code}. Shutting down.")
                    stop_services()
                    sys.exit(code or 1)
            time.sleep(1)
    except KeyboardInterrupt:
        stop_services()
    except Exception as exc:
        print(f"\\nStartup failure: {exc}", file=sys.stderr)
        stop_services()
        sys.exit(1)
'''

    customized_log_py = '''import json
import logging
import sys
from pathlib import Path
from loguru import logger


class InterceptHandler(logging.Handler):
    loglevel_mapping = {
        50: "CRITICAL",
        40: "ERROR",
        30: "WARNING",
        20: "INFO",
        10: "DEBUG",
        0: "NOTSET",
    }

    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except AttributeError:
            level = self.loglevel_mapping.get(record.levelno, "INFO")

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        log = logger.bind(request_id="app")
        log.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


class CustomizeLogger:
    @classmethod
    def make_logger(cls, config_path: Path):
        config = cls.load_logging_config(config_path)
        logging_config = (config or {}).get("logger", {})

        return cls.customize_logging(
            logging_config.get("path", "logs/app.log"),
            level=logging_config.get("level", "INFO"),
            retention=logging_config.get("retention", "10 days"),
            rotation=logging_config.get("rotation", "1 day"),
            format=logging_config.get("format", "{time} | {level} | {message}"),
        )

    @classmethod
    def customize_logging(cls, filepath: str, level: str, rotation: str, retention: str, format: str):
        log_path = Path(filepath)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.remove()
        logger.add(sys.stdout, enqueue=True, backtrace=True, level=level.upper(), format=format)
        logger.add(str(filepath), rotation=rotation, retention=retention, enqueue=True, backtrace=True, level=level.upper(), format=format)

        logging.basicConfig(handlers=[InterceptHandler()], level=0)
        logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
        for _log in ["uvicorn", "uvicorn.error", "fastapi"]:
            _logger = logging.getLogger(_log)
            _logger.handlers = [InterceptHandler()]

        return logger.bind(request_id=None, method=None)

    @classmethod
    def load_logging_config(cls, config_path):
        try:
            with open(config_path) as config_file:
                return json.load(config_file)
        except Exception:
            return {}
'''

    main_py = f'''import copy
import os
import pathlib
import time

import httpx
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from common.comman_function import (
    lifespan,
    set_active_logger,
    setup_logger,
    UVICORN_LOG_CONFIG,
)
from common.health import check_all_services
from common import metrics as metrics_mod
from config.config import settings
from middleware.rate_limit import GatewayRateLimitMiddleware
from middleware.security import SafetyMiddleware, SecurityHeadersMiddleware

logger = setup_logger("gateway")
set_active_logger(logger)
module_path = str(pathlib.Path(__file__).parent.absolute())

SERVICE_PREFIXES = ("auth", "user", "admin")
HTTP_METHODS = frozenset({{"get", "post", "put", "delete", "patch", "options", "head", "trace"}})


def _service_urls() -> dict[str, str]:
    return {{
        "auth": os.getenv("AUTH_SERVICE_URL", settings.AUTH_SERVICE_URL),
        "user": os.getenv("USER_SERVICE_URL", settings.USER_SERVICE_URL),
        "admin": os.getenv("ADMIN_SERVICE_URL", settings.ADMIN_SERVICE_URL),
    }}


def _has_service_paths(paths: dict, prefix: str) -> bool:
    return any(path.startswith(f"/{{prefix}}/") or path == f"/{{prefix}}" for path in paths)


def _has_all_service_paths(paths: dict) -> bool:
    return all(_has_service_paths(paths, prefix) for prefix in SERVICE_PREFIXES)


def _merge_service_openapi(openapi_schema: dict, services: dict[str, str]) -> dict:
    """Fetch each microservice schema and merge under /{{prefix}}/... paths."""
    merged_paths = dict(openapi_schema.get("paths", {{}}))
    components = openapi_schema.setdefault("components", {{}})
    components.setdefault("schemas", {{}})
    components.setdefault("securitySchemes", {{}})

    for prefix, url in services.items():
        try:
            response = httpx.get(f"{{url.rstrip('/')}}/openapi.json", timeout=5.0)
            if response.status_code != 200:
                continue

            service_schema = response.json()
            service_paths = service_schema.get("paths", {{}})
            if not service_paths:
                continue

            for path, methods in service_paths.items():
                gateway_path = f"/{{prefix}}{{path}}"
                path_item = copy.deepcopy(methods)
                for method, operation in path_item.items():
                    if method in HTTP_METHODS and isinstance(operation, dict) and "operationId" in operation:
                        operation["operationId"] = f"{{prefix}}_{{operation['operationId']}}"
                merged_paths[gateway_path] = path_item

            service_components = service_schema.get("components", {{}})
            for schema_name, schema_content in service_components.get("schemas", {{}}).items():
                components["schemas"][schema_name] = schema_content
            for scheme_name, scheme_content in service_components.get("securitySchemes", {{}}).items():
                components["securitySchemes"][scheme_name] = scheme_content
        except Exception as exc:
            logger.warning("Could not fetch OpenAPI schema for {{}}: {{}}", prefix, exc)

    openapi_schema["paths"] = merged_paths
    return openapi_schema


def create_app() -> FastAPI:
    app = FastAPI(
        title="{project_name} API Gateway",
        description="Production-ready FastAPI Microservices Gateway",
        debug=False,
        lifespan=lifespan,
    )
    app.logger = logger

    services = _service_urls()
    client = httpx.AsyncClient(timeout=60.0)

    @app.on_event("shutdown")
    async def shutdown_event():
        await client.aclose()

    async def proxy(service_url: str, path: str, request: Request):
        base = service_url.rstrip("/")
        url = f"{{base}}/{{path}}" if path else f"{{base}}/"

        headers = dict(request.headers)
        headers.pop("host", None)
        headers.pop("content-length", None)
        headers["X-Client-IP"] = request.client.host if request.client else "-"

        t0 = time.perf_counter()
        try:
            req_body = await request.body()
            response = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                params=request.query_params,
                content=req_body,
            )

            res_headers = dict(response.headers)
            res_headers.pop("content-encoding", None)
            res_headers.pop("content-length", None)

            ms = (time.perf_counter() - t0) * 1000
            metrics_mod.incr("http_proxy_requests")
            metrics_mod.observe_ms("http_proxy", ms)

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=res_headers,
            )
        except httpx.RequestError as exc:
            metrics_mod.incr("http_proxy_errors")
            logger.error("Proxy failure {{}} {{}} -> {{}}: {{}}", request.method, request.url.path, url, exc)
            return Response(content=f"Service unavailable: {{exc}}", status_code=503)

    @app.get("/live", tags=["Health"])
    async def live():
        """Liveness check."""
        return {{"status": True, "message": "alive"}}

    @app.get("/ready", tags=["Health"])
    async def ready():
        """Readiness check (microservices + database + redis)."""
        return await check_all_services()

    @app.get("/health", tags=["Health"])
    async def health():
        """Full health check status."""
        return await check_all_services()

    @app.get("/metrics", tags=["Observability"])
    async def metrics():
        """Prometheus text format metrics."""
        return Response(content=metrics_mod.render_prometheus(), media_type="text/plain; version=0.0.4")

    # Dynamic reverse proxies for microservices
    @app.api_route("/auth/{{path:path}}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"], include_in_schema=False)
    async def auth_proxy(path: str, request: Request):
        return await proxy(services["auth"], path, request)

    @app.api_route("/user/{{path:path}}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"], include_in_schema=False)
    async def user_proxy(path: str, request: Request):
        return await proxy(services["user"], path, request)

    @app.api_route("/admin/{{path:path}}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"], include_in_schema=False)
    async def admin_proxy(path: str, request: Request):
        return await proxy(services["admin"], path, request)

    def custom_openapi():
        cached = app.openapi_schema
        if cached and _has_all_service_paths(cached.get("paths", {{}})):
            return cached

        openapi_schema = get_openapi(
            title="{project_name} API Gateway",
            version="1.0.0",
            description="Aggregated microservices documentation",
            routes=app.routes,
        )
        openapi_schema = _merge_service_openapi(openapi_schema, services)
        if _has_all_service_paths(openapi_schema.get("paths", {{}})):
            app.openapi_schema = openapi_schema
        return openapi_schema

    app.openapi = custom_openapi
    return app


app = create_app()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SafetyMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GatewayRateLimitMiddleware)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        port=settings.GATEWAY_PORT,
        host="0.0.0.0",
        workers=settings.GATEWAY_WORKERS,
        log_config=UVICORN_LOG_CONFIG,
    )
'''

    readme_md = f'''# 🚀 {project_name}

A modular, production-ready FastAPI microservices architecture with an API Gateway, Redis caching, rate limiting, and security middleware.

---

## 🏛 Architecture Overview

```
                      +-------------------+
                      |   Client / Web    |
                      +---------+---------+
                                |
                                v
               +----------------------------------+
               |    API Gateway (Port {settings.GATEWAY_PORT if 'settings' in dir() else 7060})        |
               |  - Reverse Proxy (auth/user/admin)|
               |  - Aggregated OpenAPI Swagger /docs|
               |  - Gateway Rate Limit Middleware |
               |  - Safety & Security Headers     |
               |  - Health & Metrics Endpoints    |
               +----------------+-----------------+
                                |
        +-----------------------+-----------------------+
        |                       |                       |
        v                       v                       v
+---------------+       +---------------+       +---------------+
| Auth Service  |       | User Service  |       | Admin Service |
| (Port 7001)   |       | (Port 7002)   |       | (Port 7004)   |
+-------+-------+       +-------+-------+       +-------+-------+
        |                       |                       |
        +-----------------------+-----------------------+
                                |
                +---------------+---------------+
                |                               |
                v                               v
        +---------------+               +---------------+
        |  PostgreSQL   |               |     Redis     |
        |  (asyncpg)    |               | (Cache/Limits)|
        +---------------+               +---------------+
```

---

## 📁 Project Structure

```
{project_name}/
├── app/
│   ├── auth/              # Authentication service (register, otp, login, logout)
│   ├── user/              # User service (profile, details, settings)
│   └── admin/             # Admin service (dashboard, user management, 2FA)
├── common/                # Shared utilities
│   ├── comman_function.py # Logger, JWT helpers, password hashing (bcrypt+pepper)
│   ├── common_response.py # Standardized success/error JSON response handlers
│   ├── redis_client.py    # Async Redis connection pool & cache primitives
│   ├── cache.py           # Cache key builders, invalidation, cached_db_call
│   ├── rate_limit.py      # Decorator & FastAPI dependency for rate limits
│   ├── security.py        # Input sanitization, file validations
│   ├── db_functions.py    # PostgreSQL stored procedure runners
│   ├── health.py          # Central health check logic
│   └── metrics.py         # Prometheus metrics tracking
├── config/                # Environment settings & log configuration
├── middleware/            # Rate limiting & security middlewares
├── shared/                # asyncpg database connection & pool
├── Dockerfile             # Multi-service container specification
├── docker-compose.yml     # (Optional)
├── requirement.txt        # Python package dependencies
├── run_internal_services.py # Local multi-service orchestrator
└── main.py                # Central API Gateway & OpenAPI aggregator
```

---

## ⚡ Quickstart

### 1. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
pip install -r requirement.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your PostgreSQL credentials
```

### 3. Run Everything in One Command
```bash
python run_internal_services.py
```
This automatically starts:
- Redis server
- Auth service on `http://127.0.0.1:7001`
- User service on `http://127.0.0.1:7002`
- Admin service on `http://127.0.0.1:7004`
- Gateway on `http://127.0.0.1:7060`

### 4. Interactive API Documentation
Open your browser to:
👉 **`http://127.0.0.1:7060/docs`**

---

## 🐳 Docker Deployment

Build and run all services in a single container:

```bash
docker build -t {project_name.lower()} .
docker run --rm -p 7060:7060 --env-file .env {project_name.lower()}
```

---

## 🛡 Security Features Included

- **Bcrypt + Secret Pepper Password Hashing**: Passwords are HMAC-hashed before bcrypt salting.
- **Payload Sanitization**: Automatic recursive stripping of malicious `<script>` or javascript execution patterns.
- **Security Headers**: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Strict-Transport-Security`, `X-XSS-Protection`.
- **Redis Rate Limiting**: Distributed fixed-window counters per IP and endpoint.
- **Cache Invalidation**: Automatic cache busting on user and admin profile mutations.
'''

    return {
        ".env.example": env_example,
        ".dockerignore": dockerignore,
        "Dockerfile": dockerfile,
        "requirement.txt": requirements_txt,
        "run_internal_services.py": run_internal_services_py,
        "customized_log.py": customized_log_py,
        "main.py": main_py,
        "README.md": readme_md,
    }
