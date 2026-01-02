from typing import Optional, List, Dict, Any
from psycopg2.extensions import connection


class BaseRepository:
    def fetch_one(
        self,
        conn: connection,
        sql: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()

    def fetch_all(
        self,
        conn: connection,
        sql: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def execute(
        self,
        conn: connection,
        sql: str,
        params: Optional[Dict[str, Any]] = None
    ) -> None:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
