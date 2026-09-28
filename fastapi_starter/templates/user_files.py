"""User microservice templates for FastAPI Starter (Demo boilerplate)."""

def get_user_files() -> dict[str, str]:
    user_main_py = '''import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

from app.user.routes.profile import profile_route
from app.user.routes.user import user_router
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

logger = setup_logger("user-service")
set_active_logger(logger)

app = FastAPI(title="User Service", lifespan=lifespan)
app.logger = logger
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, custom_http_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)
app.add_middleware(SafetyMiddleware)

app.include_router(user_router)
app.include_router(profile_route, prefix="/profile")

if __name__ == "__main__":
    uvicorn.run(
        "app.user.user_main:app",
        host="0.0.0.0",
        port=settings.USER_PORT,
        workers=settings.SERVICE_WORKERS,
        log_config=UVICORN_LOG_CONFIG,
    )
'''

    model_py = '''from pydantic import Field
from common.comman_function import SecurityBaseModel


class EditProfileForm(SecurityBaseModel):
    full_name: str = Field(..., min_length=1, description="Full name")
    phone: str | None = Field(None, description="Phone number")
    country: str | None = Field(None, description="Country")


class ChangePasswordForm(SecurityBaseModel):
    old_password: str = Field(..., min_length=6, description="Current password")
    new_password: str = Field(..., min_length=6, description="New password")


class TempGenerateTokenForm(SecurityBaseModel):
    user_id: int = Field(..., description="Target user ID")
    password: str = Field(..., description="Dev secret password")
'''

    user_py = '''import traceback
from common.comman_function import create_access_token, logger
from common.common_response import (
    HEC_400,
    HEC_401,
    HEC_500,
    HEM_INTERNAL_SERVER_ERROR,
    HSC_200,
    errorResponse,
    successResponse,
)
from config.config import settings


async def get_user_details(current_user: dict):
    """Demo user profile fetcher."""
    user_id = current_user.get("user_id")
    email = current_user.get("email") or current_user.get("sub")
    logger.info(f"Fetching details for user_id: {user_id}")

    demo_data = {
        "user_id": user_id,
        "email": email,
        "full_name": "Demo User",
        "status": "active",
        "created_at": "2026-01-01T00:00:00Z",
    }
    return successResponse(HSC_200, "User details fetched successfully", demo_data)


async def generate_temp_dev_token(form):
    """DEV ONLY: Generate an access token for local API testing."""
    try:
        if not settings.ENABLE_TEMP_DEV_TOKEN:
            return errorResponse(HEC_400, "Temp token generation is disabled")

        if form.password != settings.TEMP_DEV_TOKEN_PASSWORD:
            return errorResponse(HEC_401, "Invalid developer password")

        access_token = create_access_token({
            "sub": f"user{form.user_id}@example.com",
            "user_id": form.user_id,
            "role": "user",
        })

        logger.warning(f"DEV token generated for user_id={form.user_id}")
        return successResponse(
            HSC_200,
            "Temp access token generated (DEV ONLY)",
            {"access_token": access_token, "token_type": "bearer", "user_id": form.user_id},
        )
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error generating dev token: {e}", exc_info=True)
        return errorResponse(HEC_500, HEM_INTERNAL_SERVER_ERROR)
'''

    profile_py = '''import traceback
from common.comman_function import logger
from common.common_response import HEC_400, HEC_500, HEM_INTERNAL_SERVER_ERROR, HSC_200, errorResponse, successResponse


async def update_profile(form, current_user: dict):
    """Demo profile update handler."""
    user_id = current_user.get("user_id")
    logger.info(f"User {user_id} updated profile: {form.full_name}")

    return successResponse(
        HSC_200,
        "Profile updated successfully",
        {
            "user_id": user_id,
            "full_name": form.full_name,
            "phone": form.phone,
            "country": form.country,
        },
    )


async def change_password(form, current_user: dict):
    """Demo password change handler."""
    try:
        if form.old_password == form.new_password:
            return errorResponse(HEC_400, "New password cannot be the same as old password")

        user_id = current_user.get("user_id")
        logger.info(f"User {user_id} changed password successfully")
        return successResponse(HSC_200, "Password changed successfully")
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error during password change: {e}", exc_info=True)
        return errorResponse(HEC_500, HEM_INTERNAL_SERVER_ERROR)
'''

    routes_user_py = '''from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.user.forms.model import TempGenerateTokenForm
from app.user.user import generate_temp_dev_token, get_user_details
from common.comman_function import resolve_current_user
from common.rate_limit import enforce_rate_limit, rate_limit

user_router = APIRouter(tags=["User"])
_bearer = HTTPBearer()


@user_router.get("/ping")
async def ping():
    return {"message": "user service pong"}


@user_router.post("/temp/generate-token", tags=["Developer"])
@rate_limit(limit=20, window=60)
async def temp_generate_token_api(form: TempGenerateTokenForm):
    """Generate temporary test token (development mode only)."""
    return await generate_temp_dev_token(form)


@user_router.get("/get-user")
async def user_details_api(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
):
    """Fetch current user profile details."""
    await enforce_rate_limit(request, limit=30, window=60, scope="user:get-user")
    current_user = await resolve_current_user(credentials.credentials)
    return await get_user_details(current_user)
'''

    routes_profile_py = '''from fastapi import APIRouter, Depends

from app.user.forms.model import ChangePasswordForm, EditProfileForm
from app.user.profile import change_password, update_profile
from common.comman_function import get_current_user

profile_route = APIRouter(tags=["User-Profile"])


@profile_route.post("/update-profile")
async def update_profile_api(form: EditProfileForm, current_user: dict = Depends(get_current_user)):
    return await update_profile(form, current_user)


@profile_route.post("/change-password")
async def change_password_api(form: ChangePasswordForm, current_user: dict = Depends(get_current_user)):
    return await change_password(form, current_user)
'''

    return {
        "app/user/__init__.py": "",
        "app/user/user_main.py": user_main_py,
        "app/user/user.py": user_py,
        "app/user/profile.py": profile_py,
        "app/user/forms/__init__.py": "",
        "app/user/forms/model.py": model_py,
        "app/user/routes/__init__.py": "",
        "app/user/routes/user.py": routes_user_py,
        "app/user/routes/profile.py": routes_profile_py,
    }
