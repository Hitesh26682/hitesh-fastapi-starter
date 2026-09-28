# 🚀 hitesh-fastapi-starter

**An enterprise-grade CLI tool to scaffold clean, modular, and production-ready FastAPI Microservices with an API Gateway — in just one command.**

[![PyPI Version](https://badge.fury.io/py/hitesh-fastapi-starter.svg)](https://pypi.org/project/hitesh-fastapi-starter/)
[![Downloads](https://static.pepy.tech/badge/hitesh-fastapi-starter)](https://pepy.tech/project/hitesh-fastapi-starter)
[![Monthly Downloads](https://static.pepy.tech/badge/hitesh-fastapi-starter/month)](https://pepy.tech/project/hitesh-fastapi-starter)
[![Python Versions](https://img.shields.io/pypi/pyversions/hitesh-fastapi-starter.svg)](https://pypi.org/project/hitesh-fastapi-starter/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 💥 What's New in v2.0.0 (Major Release)

Version **`2.0.0`** is a complete ground-up redesign of `hitesh-fastapi-starter`. We transitioned from a basic folder layout to a decoupled, high-throughput **Microservices Architecture with an API Gateway**.

### 📊 v1.x vs v2.0.0 Comparison

| Feature | v1.x (Legacy) | v2.0.0 (Current) |
|---|---|---|
| **Architecture** | Simple basic monolithic folder structure | Decoupled Microservices (`auth`, `user`, `admin`) + Central API Gateway |
| **API Documentation** | Basic single-service Swagger | **Dynamic OpenAPI Aggregator**: Merges all microservice schemas into one unified `/docs` |
| **Service Ports** | Single port (8060) | Independent ports: Gateway (`7060`), Auth (`7001`), User (`7002`), Admin (`7004`) |
| **Database** | Placeholder connection file | **`asyncpg` Connection Pool**: Async PostgreSQL pooling + generic procedure/query runner |
| **Caching** | ❌ None | **Redis Caching**: Async Redis client singleton, cache-aside helpers, and domain invalidation |
| **Rate Limiting** | ❌ None | **Redis Sliding Window Limiter**: Decorator, FastAPI dependency, and gateway middleware |
| **Security & Headers** | ❌ Basic | **SafetyMiddleware** (XSS/HTML payload sanitization), **SecurityHeadersMiddleware**, Bcrypt + Secret Pepper |
| **Observability** | Standard log placeholder | **Central Health Checks** (`/health`, `/ready`, `/live`) & **Prometheus Metrics** (`/metrics`) |
| **Process Orchestration**| Manual individual startup | **`run_internal_services.py`**: Boots Redis + microservices + Gateway with graceful termination |
| **Docker Support** | ❌ None | Production-ready multi-service **`Dockerfile`** and **`.dockerignore`** |
| **Code Templates** | Hardcoded strings | Clean, modular template generator with 50+ production-ready files |

---

## 🏛 Architecture Diagram

```
                              +------------------------+
                              |      Web / Client      |
                              +-----------+------------+
                                          |
                                          v
                    +--------------------------------------------+
                    |          API Gateway (Port 7060)           |
                    |  - Central Reverse Proxy                   |
                    |  - Unified OpenAPI / Swagger UI (/docs)    |
                    |  - Gateway Rate Limit Middleware           |
                    |  - Safety & Security Headers Middlewares   |
                    |  - Central Health (/health) & Metrics      |
                    +---------------------+----------------------+
                                          |
        +---------------------------------+---------------------------------+
        |                                 |                                 |
        v                                 v                                 v
+------------------+              +------------------+              +------------------+
|   Auth Service   |              |   User Service   |              |  Admin Service   |
|   (Port 7001)    |              |   (Port 7002)    |              |   (Port 7004)    |
|  - /register     |              |  - /get-user     |              |  - /dashboard    |
|  - /verify-otp   |              |  - /profile      |              |  - /profile      |
|  - /login/logout |              |  - /password     |              |  - /users CRUD   |
+--------+---------+              +--------+---------+              +--------+---------+
         |                                 |                                 |
         +---------------------------------+---------------------------------+
                                           |
                         +-----------------+-----------------+
                         |                                   |
                         v                                   v
             +-----------------------+           +-----------------------+
             |  PostgreSQL Database  |           |     Redis Server      |
             |       (asyncpg)       |           |   (Cache & Limits)    |
             +-----------------------+           +-----------------------+
```

---

## 📦 Installation

Install or upgrade via pip:

```bash
pip install --upgrade hitesh-fastapi-starter
```

Verify the installation:
```bash
fastapi-starter --version
# Output: hitesh-fastapi-starter version 2.0.0
```

---

## 🚀 Quickstart Guide

### Step 1: Scaffold Your Project
Run either command with your desired project name:

```bash
fastapi-starter my-backend
# or
hitesh-fastapi-starter my-backend
```

### Step 2: Set Up Virtual Environment & Dependencies
```bash
cd my-backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate       # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirement.txt
```

### Step 3: Configure Environment Variables
```bash
cp .env.example .env
# Edit .env to set your PostgreSQL credentials and secrets
```

### Step 4: Run All Services
```bash
python run_internal_services.py
```

This single command automatically starts:
- 🟢 **Redis Server** (if not already running)
- 🟢 **Auth Microservice** on `http://127.0.0.1:7001`
- 🟢 **User Microservice** on `http://127.0.0.1:7002`
- 🟢 **Admin Microservice** on `http://127.0.0.1:7004`
- 🟢 **API Gateway** on `http://127.0.0.1:7060`

### Step 5: Explore the Interactive API Documentation
Open your browser and visit:
👉 **`http://127.0.0.1:7060/docs`**

The gateway dynamically collects all endpoints from the underlying microservices into a unified interactive Swagger UI!

---

## 📁 Generated Project Structure

```
my-backend/
├── app/
│   ├── auth/                      # Authentication Microservice
│   │   ├── auth_main.py           # Standalone FastAPI service (Port 7001)
│   │   ├── auth.py                # Registration, OTP verify, Login, Logout logic
│   │   ├── forms/model.py         # Pydantic schemas (RegisterForm, LoginForm, etc.)
│   │   └── routes/auth.py         # APIRouter endpoints
│   ├── user/                      # User Profile Microservice
│   │   ├── user_main.py           # Standalone FastAPI service (Port 7002)
│   │   ├── user.py                # Profile details and dev token helpers
│   │   ├── profile.py             # Profile update and password change logic
│   │   ├── forms/model.py         # Pydantic schemas (EditProfileForm, etc.)
│   │   └── routes/                # User & profile APIRouters
│   └── admin/                     # Admin Management Microservice
│       ├── admin_main.py          # Standalone FastAPI service (Port 7004)
│       ├── admin.py               # Dashboard metrics and profile logic
│       ├── auth.py                # Admin login and 2FA verification
│       ├── users.py               # User listing, view, edit, disable/enable logic
│       ├── forms/model.py         # Admin Pydantic schemas
│       └── routes/                # Admin, auth, and user management APIRouters
├── common/                        # Shared Enterprise Utilities
│   ├── comman_function.py         # Custom logging, JWT helpers, bcrypt+pepper hashing, lifespan
│   ├── common_response.py         # Standardized JSON responses (successResponse / errorResponse)
│   ├── redis_client.py            # Async Redis connection pool singleton
│   ├── cache.py                   # Cache key builders, invalidation, cached_db_call
│   ├── rate_limit.py              # Redis sliding-window decorator & dependency
│   ├── security.py                # Request body XSS/script sanitization and file validator
│   ├── db_functions.py            # PostgreSQL procedure / query execution wrappers
│   ├── health.py                  # Microservices & Redis health check logic
│   └── metrics.py                 # In-process Prometheus metrics renderer
├── config/
│   ├── config.py                  # Pydantic/dotenv settings manager
│   └── logging_config.json        # Loguru file rotation & retention settings
├── middleware/
│   ├── rate_limit.py              # Gateway sliding-window flood protection middleware
│   └── security.py                # SafetyMiddleware & SecurityHeadersMiddleware
├── shared/
│   └── db.py                      # asyncpg database connection pool abstraction
├── Dockerfile                     # Multi-service production Dockerfile
├── .dockerignore                  # Docker build exclusions
├── .env.example                   # Annotated environment configuration template
├── requirement.txt                # Pinned production dependencies
├── run_internal_services.py       # Local service orchestrator with graceful shutdown
└── main.py                        # Central API Gateway & OpenAPI schema merger
```

---

## 🔌 API Endpoints Summary

All routes are served through the **API Gateway** (`http://127.0.0.1:7060`):

### 🩺 Health & Observability
- `GET /health` - Comprehensive status of Gateway, Redis, and all microservices
- `GET /ready` - Readiness probe for container orchestrators (Kubernetes)
- `GET /live` - Liveness probe (process responsive)
- `GET /metrics` - Prometheus text format metrics (request counts, latency)

### 🔐 Auth Service (`/auth/...`)
- `POST /auth/register` - Register a new account
- `POST /auth/verify-otp` - Verify registration OTP
- `POST /auth/login` - Authenticate with email/password
- `POST /auth/logout` - Revoke current user session

### 👤 User Service (`/user/...`)
- `GET /user/get-user` - Fetch authenticated user profile
- `POST /user/profile/update-profile` - Update profile name, phone, country
- `POST /user/profile/change-password` - Change account password
- `POST /user/temp/generate-token` - Local development token generator

### 🛡 Admin Service (`/admin/...`)
- `POST /admin/auth/login` - Admin authentication
- `POST /admin/auth/verify-2fa` - 2FA TOTP validation
- `POST /admin/auth/logout` - Admin session revocation
- `GET /admin/dashboard` - High-level system & user metrics
- `GET /admin/profile` - Current admin profile
- `POST /admin/user/list` - Paginated user listing
- `GET /admin/user/details/{id}` - Full user details
- `POST /admin/user/edit` - Update user details as admin
- `POST /admin/user/disable` - Block user access
- `POST /admin/user/enable` - Re-enable user access

---

## 🐳 Docker Deployment

The scaffolded project includes a unified `Dockerfile` that packages Redis and all microservices into a single isolated container:

```bash
# Build the container image
docker build -t my-fastapi-app .

# Run the container with your environment configuration
docker run --rm -p 7060:7060 --env-file .env my-fastapi-app
```

---

## 🔒 Security Best Practices Built-in

1. **HMAC Pepper + Bcrypt**: Passwords are HMAC-hashed with a server-side secret key before bcrypt salting to guard against database leak brute-force attacks.
2. **Payload Sanitization**: `SafetyMiddleware` recursively strips script tags, HTML injection, and javascript execution contexts from incoming JSON requests.
3. **Security Headers**: Injects `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Strict-Transport-Security`, `X-XSS-Protection`, and `Referrer-Policy`.
4. **Redis Rate Limiting**: Distributed fixed-window rate limiting per IP address prevents credential stuffing and endpoint flooding.

---

## 📄 License

This project is licensed under the terms of the **MIT License**. Free for personal and commercial use.

**Author**: Hitesh Ladumor ([ladumorhitesh2668@gmail.com](mailto:ladumorhitesh2668@gmail.com))  
**GitHub**: [https://github.com/Hitesh26682/hitesh-fastapi-starter](https://github.com/Hitesh26682/hitesh-fastapi-starter)
