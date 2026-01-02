from psycopg2.extras import RealDictCursor


class UserRepository:

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

    def get_by_id(self, conn, user_id: int):
        """
        토큰 검증 후 사용자 ID로 조회
        """
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT user_id, email, password_hash, name, created_at
                FROM users
                WHERE user_id = %s
                """,
                (user_id,)
            )
            return cur.fetchone()


    def create(
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
                RETURNING user_id, email, name, created_at
                """,
                (email, password_hash, name)
            )
            return cur.fetchone()


user_repo = UserRepository()
