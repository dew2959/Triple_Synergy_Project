# app/repositories/user_repo.py
from psycopg2.extras import RealDictCursor
from app.core.db import with_connection


class UserRepository:

    @with_connection
    def get_by_email(self, conn, email: str):
        """
        로그인용: email로 사용자 조회
        """
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT user_id, email, password_hash, name
                FROM users
                WHERE email = %s
                """,
                (email,)
            )
            return cur.fetchone()

    @with_connection
    def create_user(
        self,
        conn,
        email: str,
        password_hash: str,
        name: str | None = None
    ):
        """
        회원가입
        """
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO users (email, password_hash, name)
                VALUES (%s, %s, %s)
                RETURNING user_id, email, name
                """,
                (email, password_hash, name)
            )
            return cur.fetchone()


user_repo = UserRepository()
