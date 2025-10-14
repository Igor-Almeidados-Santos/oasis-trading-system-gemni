import os
from contextlib import contextmanager
from typing import Any, Iterable, Optional

from psycopg2.extras import DictCursor
from psycopg2.pool import SimpleConnectionPool


class PostgresManager:
    """Gerencia conexões com o PostgreSQL utilizando um pool compartilhado."""

    _pool: Optional[SimpleConnectionPool] = None

    def __init__(self) -> None:
        if PostgresManager._pool is None:
            PostgresManager._pool = SimpleConnectionPool(
                minconn=int(os.getenv("POSTGRES_POOL_MIN", "1")),
                maxconn=int(os.getenv("POSTGRES_POOL_MAX", "5")),
                host=os.getenv("POSTGRES_HOST", "localhost"),
                database=os.getenv("POSTGRES_DB"),
                user=os.getenv("POSTGRES_USER"),
                password=os.getenv("POSTGRES_PASSWORD"),
            )

    @contextmanager
    def get_cursor(self) -> Iterable[DictCursor]:
        if PostgresManager._pool is None:
            raise RuntimeError("Connection pool not initialised")

        connection = PostgresManager._pool.getconn()
        try:
            cursor = connection.cursor(cursor_factory=DictCursor)
            try:
                yield cursor
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                cursor.close()
        finally:
            PostgresManager._pool.putconn(connection)

    def execute_query(self, query: str, params: Optional[Iterable[Any]] = None, fetch: Optional[str] = None):
        """Executa uma query no banco de dados com commit automático."""
        with self.get_cursor() as cur:
            cur.execute(query, params)
            if fetch == "one":
                return cur.fetchone()
            if fetch == "all":
                return cur.fetchall()
        return None

    @classmethod
    def close_pool(cls) -> None:
        if cls._pool is not None:
            cls._pool.closeall()
            cls._pool = None
