"""Template aggregations for fastapi_starter."""

from .root_files import get_root_files
from .config_files import get_config_files
from .shared_files import get_shared_files
from .middleware_files import get_middleware_files
from .common_files import get_common_files
from .auth_files import get_auth_files
from .user_files import get_user_files
from .admin_files import get_admin_files


def get_all_templates(project_name: str) -> dict[str, str]:
    files: dict[str, str] = {}
    files.update(get_root_files(project_name))
    files.update(get_config_files(project_name))
    files.update(get_shared_files())
    files.update(get_middleware_files())
    files.update(get_common_files())
    files.update(get_auth_files())
    files.update(get_user_files())
    files.update(get_admin_files())
    return files
