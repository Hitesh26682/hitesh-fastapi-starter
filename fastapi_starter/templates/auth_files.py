"""Auth microservice templates for FastAPI Starter (Demo boilerplate)."""

def get_auth_files() -> dict[str, str]:
    auth_main_py = '''import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.auth.routes.auth import auth_router
from common.comman_function import (
    global_exception_handler,
    lifespan,
    set_active_logger,
    setup_logger,
    UVICORN_LOG_CONFIG,
    validation_exception_handler,
)
from config.config import settings
from middleware.security import SafetyMiddleware

logger = setup_logger("auth-service")
set_active_logger(logger)

app = FastAPI(title="Auth Service", lifespan=lifespan)
app.logger = logger
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)
app.add_middleware(SafetyMiddleware)
app.include_router(auth_router)

if __name__ == "__main__":
    uvicorn.run(
        "app.auth.auth_main:app",
        host="0.0.0.0",
        port=settings.AUTH_PORT,
        workers=settings.SERVICE_WORKERS,
        log_config=UVICORN_LOG_CONFIG,
    )
'''

    model_py = '''from pydantic import EmailStr, Field
from common.comman_function import SecurityBaseModel


class RegisterForm(SecurityBaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")
    full_name: str = Field(..., min_length=1, description="Full name")
    phone: str | None = Field(None, description="Optional phone number")


class VerifyRegisterOtpForm(SecurityBaseModel):
    email: EmailStr = Field(..., description="Registered email address")
    otp: str = Field(..., min_length=4, max_length=6, description="Verification OTP")


class LoginForm(SecurityBaseModel):
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")
'''

    auth_py = '''import traceback

from common.comman_function import (
    create_access_token,
    generate_temp_token,
    hash_password,
    logger,
    verify_password,
)
from common.common_response import (
    HEC_400,
    HEC_500,
    HEM_INTERNAL_SERVER_ERROR,
    HSC_200,
    errorResponse,
    successResponse,
)


async def register_user(form, client_ip: str):
    """Demo registration handler."""
    try:
        logger.info(f"IP: {client_ip} - Registration request for: {form.email}")

        # Demo password hashing
        hashed_password = hash_password(form.password)
        temp_token = generate_temp_token({"email": form.email, "action": "verify_otp"})

        return successResponse(
            HSC_200,
            "Registration initiated. Please verify with OTP (Demo OTP: 1234).",
            {
                "email": form.email,
                "full_name": form.full_name,
                "token": temp_token,
            },
        )
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error during registration: {e}", exc_info=True)
        return errorResponse(HEC_500, HEM_INTERNAL_SERVER_ERROR)


async def verify_register_otp(form, client_ip: str):
    """Demo OTP verification handler."""
    try:
        logger.info(f"IP: {client_ip} - Verifying OTP for: {form.email}")

        # Demo check (accepts any 4-6 digit OTP or '1234')
        if not form.otp.isdigit():
            return errorResponse(HEC_400, "OTP must contain digits only")

        demo_user_id = 101
        access_token = create_access_token({
            "sub": form.email,
            "user_id": demo_user_id,
            "role": "user",
        })

        return successResponse(
            HSC_200,
            "Account verified successfully",
            {
                "user_id": demo_user_id,
                "email": form.email,
                "access_token": access_token,
                "token_type": "bearer",
            },
        )
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error during OTP verification: {e}", exc_info=True)
        return errorResponse(HEC_500, HEM_INTERNAL_SERVER_ERROR)


async def login_user(form, client_ip: str):
    """Demo login handler."""
    try:
        logger.info(f"IP: {client_ip} - Login attempt for: {form.email}")

        # Demo user response (replace with your real DB authentication)
        demo_user_id = 101
        access_token = create_access_token({
            "sub": form.email,
            "user_id": demo_user_id,
            "role": "user",
        })

        return successResponse(
            HSC_200,
            "Login successful",
            {
                "user_id": demo_user_id,
                "email": form.email,
                "access_token": access_token,
                "token_type": "bearer",
            },
        )
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error during login: {e}", exc_info=True)
        return errorResponse(HEC_500, HEM_INTERNAL_SERVER_ERROR)


async def logout_user(current_user: dict):
    """Demo logout handler."""
    email = current_user.get("email") or current_user.get("sub")
    logger.info(f"User logged out: {email}")
    return successResponse(HSC_200, "Logout successful")
'''

    routes_auth_py = '''from fastapi import APIRouter, Depends, Request

from app.auth.auth import (
    login_user,
    logout_user,
    register_user,
    verify_register_otp,
)
from app.auth.forms.model import (
    LoginForm,
    RegisterForm,
    VerifyRegisterOtpForm,
)
from common.comman_function import get_current_user
from common.rate_limit import rate_limit

auth_router = APIRouter(tags=["Auth"])


@auth_router.post("/register")
@rate_limit(limit=5, window=60)
async def register(form: RegisterForm, request: Request):
    """Register a new user account."""
    client_ip = request.headers.get("X-Client-IP") or (request.client.host if request.client else "-")
    return await register_user(form, client_ip)


@auth_router.post("/verify-otp")
@rate_limit(limit=10, window=60)
async def verify_otp(form: VerifyRegisterOtpForm, request: Request):
    """Verify registration OTP."""
    client_ip = request.headers.get("X-Client-IP") or (request.client.host if request.client else "-")
    return await verify_register_otp(form, client_ip)


@auth_router.post("/login")
@rate_limit(limit=10, window=60)
async def login(form: LoginForm, request: Request):
    """User authentication endpoint."""
    client_ip = request.headers.get("X-Client-IP") or (request.client.host if request.client else "-")
    return await login_user(form, client_ip)


@auth_router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout current user session."""
    return await logout_user(current_user)
'''

    return {
        "app/auth/__init__.py": "",
        "app/auth/auth_main.py": auth_main_py,
        "app/auth/auth.py": auth_py,
        "app/auth/forms/__init__.py": "",
        "app/auth/forms/model.py": model_py,
        "app/auth/routes/__init__.py": "",
        "app/auth/routes/auth.py": routes_auth_py,
    }
