"""Shared database templates for FastAPI Starter."""

def get_shared_files() -> dict[str, str]:
    db_py = '''import json
import asyncpg
from config.config import settings


def _sql_literal_for_log(value) -> str:
    """Format a Python value as an SQL-ish literal for logs only."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, (dict, list)):
        raw = json.dumps(value, default=str)
    else:
        raw = str(value)
    return "'" + raw.replace("'", "''") + "'"


class Database:
    def __init__(self):
        self._pool = None

    async def connect(self):
        if not self._pool:
            self._pool = await asyncpg.create_pool(
                settings.DATABASE_URL,
                min_size=max(1, int(getattr(settings, "DB_POOL_MIN", 5) or 5)),
                max_size=max(1, int(getattr(settings, "DB_POOL_MAX", 20) or 20)),
            )

    async def disconnect(self):
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def execute(self, query, *args):
        async with self._pool.acquire() as connection:
            return await connection.execute(query, *args)

    async def fetch(self, query, *args):
        async with self._pool.acquire() as connection:
            return await connection.fetch(query, *args)

    async def fetchrow(self, query, *args):
        async with self._pool.acquire() as connection:
            return await connection.fetchrow(query, *args)

    async def call_function(self, function_name: str, **kwargs):
        """
        Call PostgreSQL function using named parameters.

        Example:
            await db.call_function("my_custom_procedure", param_id=1, param_status="active")
        """
        if not kwargs:
            query = f"SELECT {function_name}()"
            args = []
            log_query = query
        else:
            placeholders = []
            log_parts = []
            args = []

            for i, (key, value) in enumerate(kwargs.items(), start=1):
                if isinstance(value, list) and all(isinstance(x, str) for x in value):
                    placeholders.append(f"{key} => ${i}::text[]")
                    args.append(value)
                    log_parts.append(f"{key} => {_sql_literal_for_log(value)}")
                elif isinstance(value, (dict, list)):
                    placeholders.append(f"{key} => ${i}::jsonb")
                    dumped = json.dumps(value)
                    args.append(dumped)
                    log_parts.append(f"{key} => {_sql_literal_for_log(value)}::jsonb")
                else:
                    placeholders.append(f"{key} => ${i}")
                    args.append(value)
                    log_parts.append(f"{key} => {_sql_literal_for_log(value)}")

            query = f"SELECT {function_name}({', '.join(placeholders)})"
            log_query = f"SELECT {function_name}({', '.join(log_parts)})"

        from common.comman_function import get_active_logger
        get_active_logger().info(log_query)

        row = await self.fetchrow(query, *args)
        if row and row[0]:
            if isinstance(row[0], str):
                try:
                    return json.loads(row[0])
                except Exception:
                    return row[0]
            return row[0]

        return None


db = Database()
'''

    return {
        "shared/__init__.py": "",
        "shared/db.py": db_py,
    }
