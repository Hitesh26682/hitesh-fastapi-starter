"""Config template files for FastAPI Starter."""

def get_config_files(project_name: str) -> dict[str, str]:
    config_py = f'''import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "{project_name.upper()}")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:password@localhost:5432/{project_name.lower().replace('-', '_')}_db"
    )
    SECRET_KEY: str = os.getenv("SECRET_KEY", "default_secret_key_change_in_production")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "default_jwt_secret_key_change_in_production")
    ADMIN_JWT_SECRET_KEY: str = os.getenv("ADMIN_JWT_SECRET_KEY", "default_admin_jwt_secret_change_in_production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
        or os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24))
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

    # Developer settings
    ENABLE_TEMP_DEV_TOKEN: bool = os.getenv("ENABLE_TEMP_DEV_TOKEN", "true").lower() == "true"
    TEMP_DEV_TOKEN_PASSWORD: str = os.getenv("TEMP_DEV_TOKEN_PASSWORD", "Dev@12345")

    # Cache TTL (seconds)
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", 60))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_RETENTION_DAYS: int = int(os.getenv("LOG_RETENTION_DAYS", 10))

    # Gateway + Service ports
    GATEWAY_PORT: int = int(os.getenv("GATEWAY_PORT", "7060"))
    AUTH_PORT: int = int(os.getenv("AUTH_PORT", "7001"))
    USER_PORT: int = int(os.getenv("USER_PORT", "7002"))
    ADMIN_PORT: int = int(os.getenv("ADMIN_PORT", "7004"))

    # Service URLs (for Gateway proxy)
    AUTH_SERVICE_URL: str = os.getenv("AUTH_SERVICE_URL", "http://127.0.0.1:7001")
    USER_SERVICE_URL: str = os.getenv("USER_SERVICE_URL", "http://127.0.0.1:7002")
    ADMIN_SERVICE_URL: str = os.getenv("ADMIN_SERVICE_URL", "http://127.0.0.1:7004")

    # Workers
    GATEWAY_WORKERS: int = int(os.getenv("GATEWAY_WORKERS", "1"))
    SERVICE_WORKERS: int = int(os.getenv("SERVICE_WORKERS", os.getenv("WORKERS", "2")))

    # DB Connection Pool
    DB_POOL_MIN: int = int(os.getenv("DB_POOL_MIN", "5"))
    DB_POOL_MAX: int = int(os.getenv("DB_POOL_MAX", "20"))


settings = Settings()
'''

    logging_config_json = '''{
  "logger": {
    "path": "logs/app.log",
    "level": "INFO",
    "rotation": "1 day",
    "retention": "10 days",
    "format": "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}"
  }
}
'''

    return {
        "config/__init__.py": "",
        "config/config.py": config_py,
        "config/logging_config.json": logging_config_json,
    }
