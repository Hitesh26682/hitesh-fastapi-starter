import os
import sys


def create_project_cli():
    if len(sys.argv) < 2:
        print("❌ Usage: your-cli-command <project_name>")
        sys.exit(1)
    create_project(sys.argv[1])


def create_project(project_name):
    base = os.path.abspath(project_name)

    # Create base folders
    os.makedirs(os.path.join(base, "app", "user", "forms"), exist_ok=True)
    os.makedirs(os.path.join(base, "app", "account", "forms"), exist_ok=True)
    os.makedirs(os.path.join(base, "websocket"), exist_ok=True)
    os.makedirs(os.path.join(base, "common"), exist_ok=True)
    os.makedirs(os.path.join(base, "shared"), exist_ok=True)
    os.makedirs(os.path.join(base, "middleware"), exist_ok=True)
    os.makedirs(os.path.join(base, "config"), exist_ok=True)

    # Create user/account route files
    for app_name in ["user", "account"]:
        app_dir = os.path.join(base, "app", app_name)
        forms_dir = os.path.join(app_dir, "forms")
        with open(os.path.join(app_dir, "__init__.py"), "w"): pass
        with open(os.path.join(forms_dir, "__init__.py"), "w"): pass
        with open(os.path.join(app_dir, "route.py"), "w") as f:
            f.write(f"""from fastapi import APIRouter

{app_name}_router = APIRouter()

@{app_name}_router.get("/ping")
def ping():
    return {{"message": "{app_name} pong"}}
""")

    # Common
    with open(os.path.join(base, "common", "comman_function.py"), "w") as f:
        f.write("# Common functions\n")
    with open(os.path.join(base, "common", "common_response.py"), "w") as f:
        f.write("""from fastapi.responses import JSONResponse
import traceback
from fastapi import status, Depends
from fastapi.encoders import jsonable_encoder
import json
import requests
import datetime

# HTTP Success Messages
HEM_INTERNAL_SERVER_ERROR = "Something went wrong. Please try again."
HEM_UNAUTHORIZED = "Your Session has been expired!"
HSM_SUCCESS = "success"

# HTTP Error Messages
HEM_ERROR = "error"
HEM_INVALID_EMAIL_FORMAT = "Invalid email format"
HEM_INVALID_MOBILE_FORMAT = "Invalid mobile number format"
HEM_INVALID_VERIFY_CODE_FORMAT = "Verify code must contain only numbers."

def successResponse(status_code, msg, data={{}}):
    return JSONResponse(
        status_code=status_code,
        content={{
            "status": "success",
            "message": msg,
            "data": data,
        }}
    )

def errorResponse(status_code, msg, data={{}}):
    return JSONResponse(
        status_code=status_code,
        content={{
            "status": "error",
            "message": msg,
            "data": data,
        }}
    )
""")

    # Shared
    with open(os.path.join(base, "shared", "__init__.py"), "w"): pass
    with open(os.path.join(base, "shared", "db.py"), "w") as f:
        f.write("# DB connection code\n")

    # Middleware
    with open(os.path.join(base, "middleware", "request_auth_middleware.py"), "w") as f:
        f.write("# Custom auth middleware\n")

    # Config
    with open(os.path.join(base, "config", "config.ini"), "w") as f:
        f.write("[DEFAULT]\nexample_key = value\n")
    with open(os.path.join(base, "config", "logging_config.json"), "w") as f:
        f.write("{\n  \"version\": 1,\n  \"handlers\": {},\n  \"loggers\": {}\n}\n")

    with open(os.path.join(base , "customized_log.py") , "w") as f:
        f.write("""
        #     logger file 
        
        # Custom Logger Using Loguru

import logging
import sys
from pathlib import Path
from loguru import logger
import json


class InterceptHandler(logging.Handler):
    loglevel_mapping = {
        50: 'CRITICAL',
        40: 'ERROR',
        30: 'WARNING',
        20: 'INFO',
        10: 'DEBUG',
        0: 'NOTSET',
    }

    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except AttributeError:
            level = self.loglevel_mapping[record.levelno]

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        log = logger.bind(request_id='app')
        log.opt(
            depth=depth,
            exception=record.exc_info
        ).log(level, record.getMessage())


class CustomizeLogger:

    @classmethod
    def make_logger(cls, config_path: Path):
        config = cls.load_logging_config(config_path)
        logging_config = config.get('logger')

        logger = cls.customize_logging(
            logging_config.get('path'),
            level=logging_config.get('level'),
            retention=logging_config.get('retention'),
            rotation=logging_config.get('rotation'),
            format=logging_config.get('format')
        )
        return logger

    @classmethod
    def customize_logging(cls,
                          filepath: Path,
                          level: str,
                          rotation: str,
                          retention: str,
                          format: str
                          ):
        logger.remove()
        logger.add(
            sys.stdout,
            enqueue=True,
            backtrace=True,
            level=level.upper(),
            format=format
        )
        logger.add(
            str(filepath),
            rotation=rotation,
            retention=retention,
            enqueue=True,
            backtrace=True,
            level=level.upper(),
            format=format
        )
        logging.basicConfig(handlers=[InterceptHandler()], level=0)
        logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
        for _log in ['uvicorn',
                     'uvicorn.error',
                     'fastapi'
                     ]:
            _logger = logging.getLogger(_log)
            _logger.handlers = [InterceptHandler()]

        return logger.bind(request_id=None, method=None)

    @classmethod
    def load_logging_config(cls, config_path):
        config = None
        with open(config_path) as config_file:
            config = json.load(config_file)
        return config

        """)


    # main.py
    with open(os.path.join(base, "main.py"), "w") as f:
        f.write("""\"\"\"
Main module of exchange backend.
\"\"\"
import os
import pathlib
import logging
import uvicorn
from app.account.route import account_router
from customized_log import CustomizeLogger
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request, HTTPException, Security

\"\"\"
code for save logs in customise path
\"\"\"
logger = logging.getLogger(__name__)
module_path = str(pathlib.Path(__file__).parent.absolute())
config_path = str(os.path.join(module_path, "config", "logging_config.json"))

def create_app() -> FastAPI:
    app = FastAPI(title=' demo | demo API', debug=False)
    logger = CustomizeLogger.make_logger(config_path)
    app.logger = logger
    app.include_router(account_router)
    return app

app = create_app()

origins = [
    "*"
    # "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    uvicorn.run(app, port=8060, ws_ping_interval=1, ws_ping_timeout=-1)
""")

    print(f"✅ Project '{project_name}' generated successfully!")
