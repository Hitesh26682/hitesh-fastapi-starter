"""Admin microservice templates for FastAPI Starter (Demo boilerplate)."""

def get_admin_files() -> dict[str, str]:
    admin_main_py = '''import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

from app.admin.routes.admin import admin_router
from app.admin.routes.auth import auth_router
from app.admin.routes.users import user_router
from common.comman_function import (
    custom_http_exception_handler,
    global_exception_handler,
    lifespan,
    set_active_logger,
    setup_logger,
    UVICORN_LOG_CONFIG,
    validation_exception_handler,
)
from config.config import settings
from middleware.security import SafetyMiddleware

logger = setup_logger("admin-service")
set_active_logger(logger)

app = FastAPI(title="Admin Service", lifespan=lifespan)
app.logger = logger
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, custom_http_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)
app.add_middleware(SafetyMiddleware)

app.include_router(admin_router)
app.include_router(auth_router, prefix="/auth")
app.include_router(user_router, prefix="/user")

if __name__ == "__main__":
    uvicorn.run(
        "app.admin.admin_main:app",
        host="0.0.0.0",
        port=settings.ADMIN_PORT,
        workers=settings.SERVICE_WORKERS,
        log_config=UVICORN_LOG_CONFIG,
    )
'''

    model_py = '''from pydantic import EmailStr, Field
from common.comman_function import SecurityBaseModel


class AdminLoginForm(SecurityBaseModel):
    email: EmailStr = Field(..., description="Admin email address")
    password: str = Field(..., description="Admin password")


class Admin2faForm(SecurityBaseModel):
    temp_token: str = Field(..., description="Temporary token received after password verification")
    code: str = Field(..., min_length=6, max_length=6, description="6-digit 2FA code (Demo: 123456)")


class AdminUserListForm(SecurityBaseModel):
    search: str | None = Field(None, description="Search keyword")
    status: str | None = Field(None, description="Status filter")
    limit: int = Field(20, ge=1, le=100, description="Page limit")
    offset: int = Field(0, ge=0, description="Page offset")


class AdminUserEditForm(SecurityBaseModel):
    user_id: int = Field(..., description="Target user ID")
    full_name: str | None = Field(None, description="Updated full name")
    status: str | None = Field(None, description="Account status")


class AdminUserActionForm(SecurityBaseModel):
    user_id: int = Field(..., description="Target user ID")
    reason: str | None = Field(None, description="Reason for action")
'''

    auth_py = '''import traceback
from common.comman_function import (
    create_admin_access_token,
    decode_admin_temp_token,
    generate_admin_temp_token,
    logger,
)
from common.common_response import HEC_400, HEC_500, HEM_INTERNAL_SERVER_ERROR, HSC_200, errorResponse, successResponse


async def admin_login(form, client_ip: str):
    """Demo admin login handler with optional 2FA challenge."""
    try:
        logger.info(f"IP: {client_ip} - Admin login attempt for: {form.email}")

        # Demo admin credentials verification
        demo_admin_id = 1
        access_token = create_admin_access_token({
            "sub": form.email,
            "admin_id": demo_admin_id,
            "role": "admin",
        })

        return successResponse(
            HSC_200,
            "Admin login successful",
            {
                "admin_id": demo_admin_id,
                "email": form.email,
                "access_token": access_token,
                "token_type": "bearer",
            },
        )
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error during admin login: {e}", exc_info=True)
        return errorResponse(HEC_500, HEM_INTERNAL_SERVER_ERROR)


async def verify_2fa(form, client_ip: str):
    """Demo 2FA verification."""
    try:
        if form.code != "123456":
            return errorResponse(HEC_400, "Invalid 2FA code (Demo code is: 123456)")

        demo_admin_id = 1
        access_token = create_admin_access_token({
            "sub": "admin@example.com",
            "admin_id": demo_admin_id,
            "role": "admin",
        })

        return successResponse(
            HSC_200,
            "2FA verified successfully",
            {"admin_id": demo_admin_id, "access_token": access_token, "token_type": "bearer"},
        )
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error during 2FA: {e}", exc_info=True)
        return errorResponse(HEC_500, HEM_INTERNAL_SERVER_ERROR)


async def logout(current_admin: dict):
    """Demo admin logout handler."""
    email = current_admin.get("email") or current_admin.get("sub")
    logger.info(f"Admin logged out: {email}")
    return successResponse(HSC_200, "Admin logout successful")
'''

    admin_py = '''import traceback
from common.comman_function import logger
from common.common_response import HEC_500, HEM_INTERNAL_SERVER_ERROR, HSC_200, errorResponse, successResponse


async def get_profile(current_admin: dict):
    """Demo admin profile."""
    admin_id = current_admin.get("admin_id") or current_admin.get("id")
    email = current_admin.get("email") or current_admin.get("sub")

    demo_profile = {
        "admin_id": admin_id,
        "email": email,
        "role": current_admin.get("role", "admin"),
        "permissions": ["all"],
    }
    return successResponse(HSC_200, "Admin profile fetched successfully", demo_profile)


async def dashboard(current_admin: dict):
    """Demo admin dashboard summary metrics."""
    try:
        demo_metrics = {
            "total_users": 150,
            "active_users": 138,
            "blocked_users": 12,
            "system_uptime": "99.98%",
            "environment": "production",
        }
        return successResponse(HSC_200, "Dashboard metrics fetched successfully", demo_metrics)
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error fetching dashboard: {e}", exc_info=True)
        return errorResponse(HEC_500, HEM_INTERNAL_SERVER_ERROR)


async def get_settings(current_admin: dict):
    """Demo application settings."""
    demo_settings = {
        "maintenance_mode": False,
        "registration_enabled": True,
        "version": "1.0.0",
    }
    return successResponse(HSC_200, "Settings fetched successfully", demo_settings)
'''

    users_py = '''import traceback
from common.comman_function import logger
from common.common_response import HEC_404, HEC_500, HEM_INTERNAL_SERVER_ERROR, HSC_200, errorResponse, successResponse

# Demo in-memory mock dataset
MOCK_USERS = [
    {"user_id": 1, "email": "alice@example.com", "full_name": "Alice Smith", "status": "active"},
    {"user_id": 2, "email": "bob@example.com", "full_name": "Bob Jones", "status": "active"},
    {"user_id": 3, "email": "charlie@example.com", "full_name": "Charlie Brown", "status": "blocked"},
]


async def list_users(form, current_admin: dict):
    """Demo user listing with mock data."""
    logger.info(f"Admin listing users with limit={form.limit}, offset={form.offset}")
    return successResponse(
        HSC_200,
        "Users listed successfully",
        {
            "total": len(MOCK_USERS),
            "users": MOCK_USERS,
        },
    )


async def get_user_details(user_id: int, current_admin: dict):
    """Demo user details fetcher."""
    user = next((u for u in MOCK_USERS if u["user_id"] == user_id), None)
    if not user:
        return errorResponse(HEC_404, f"User with ID {user_id} not found")

    return successResponse(HSC_200, "User details fetched successfully", user)


async def edit_user(form, current_admin: dict):
    """Demo user edit handler."""
    logger.info(f"Admin updated user {form.user_id}")
    return successResponse(HSC_200, f"User {form.user_id} updated successfully")


async def disable_user(form, current_admin: dict):
    """Demo disable user handler."""
    logger.info(f"Admin disabled user {form.user_id}")
    return successResponse(HSC_200, f"User {form.user_id} disabled successfully")


async def enable_user(form, current_admin: dict):
    """Demo enable user handler."""
    logger.info(f"Admin enabled user {form.user_id}")
    return successResponse(HSC_200, f"User {form.user_id} enabled successfully")
'''

    routes_admin_py = '''from fastapi import APIRouter, Depends
from app.admin.admin import dashboard, get_profile, get_settings
from common.comman_function import get_current_admin
from common.rate_limit import rate_limit

admin_router = APIRouter(tags=["Admin"])


@admin_router.get("/profile")
@rate_limit(limit=30, window=60)
async def get_profile_api(current_admin: dict = Depends(get_current_admin)):
    """Fetch current admin profile."""
    return await get_profile(current_admin)


@admin_router.get("/dashboard")
@rate_limit(limit=60, window=60)
async def dashboard_api(current_admin: dict = Depends(get_current_admin)):
    """Fetch admin dashboard metrics."""
    return await dashboard(current_admin)


@admin_router.get("/settings")
@rate_limit(limit=30, window=60)
async def settings_api(current_admin: dict = Depends(get_current_admin)):
    """Fetch application settings."""
    return await get_settings(current_admin)
'''

    routes_auth_py = '''from fastapi import APIRouter, Depends, Request
from app.admin.auth import admin_login, logout, verify_2fa
from app.admin.forms.model import Admin2faForm, AdminLoginForm
from common.comman_function import get_current_admin
from common.rate_limit import rate_limit

auth_router = APIRouter(tags=["Admin-Auth"])


@auth_router.post("/login")
@rate_limit(limit=5, window=60)
async def admin_login_api(form: AdminLoginForm, request: Request):
    """Admin login endpoint."""
    client_ip = request.headers.get("X-Client-IP") or (request.client.host if request.client else "-")
    return await admin_login(form, client_ip)


@auth_router.post("/verify-2fa")
@rate_limit(limit=10, window=60)
async def verify_2fa_api(form: Admin2faForm, request: Request):
    """Admin 2FA verification endpoint."""
    client_ip = request.headers.get("X-Client-IP") or (request.client.host if request.client else "-")
    return await verify_2fa(form, client_ip)


@auth_router.post("/logout")
async def logout_api(current_admin: dict = Depends(get_current_admin)):
    """Admin logout endpoint."""
    return await logout(current_admin)
'''

    routes_users_py = '''from fastapi import APIRouter, Depends
from app.admin.forms.model import AdminUserActionForm, AdminUserEditForm, AdminUserListForm
from app.admin.users import disable_user, edit_user, enable_user, get_user_details, list_users
from common.comman_function import get_current_admin

user_router = APIRouter(tags=["Admin-Users"])


@user_router.post("/list")
async def list_users_api(form: AdminUserListForm, current_admin: dict = Depends(get_current_admin)):
    """List users endpoint."""
    return await list_users(form, current_admin)


@user_router.get("/details/{user_id}")
async def get_user_details_api(user_id: int, current_admin: dict = Depends(get_current_admin)):
    """User details endpoint."""
    return await get_user_details(user_id, current_admin)


@user_router.post("/edit")
async def edit_user_api(form: AdminUserEditForm, current_admin: dict = Depends(get_current_admin)):
    """Edit user endpoint."""
    return await edit_user(form, current_admin)


@user_router.post("/disable")
async def disable_user_api(form: AdminUserActionForm, current_admin: dict = Depends(get_current_admin)):
    """Disable user endpoint."""
    return await disable_user(form, current_admin)


@user_router.post("/enable")
async def enable_user_api(form: AdminUserActionForm, current_admin: dict = Depends(get_current_admin)):
    """Enable user endpoint."""
    return await enable_user(form, current_admin)
'''

    return {
        "app/admin/__init__.py": "",
        "app/admin/admin_main.py": admin_main_py,
        "app/admin/admin.py": admin_py,
        "app/admin/auth.py": auth_py,
        "app/admin/users.py": users_py,
        "app/admin/forms/__init__.py": "",
        "app/admin/forms/model.py": model_py,
        "app/admin/routes/__init__.py": "",
        "app/admin/routes/admin.py": routes_admin_py,
        "app/admin/routes/auth.py": routes_auth_py,
        "app/admin/routes/users.py": routes_users_py,
    }
