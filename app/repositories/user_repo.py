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
            sql = """
                INSERT INTO users (email, password_hash, name)
                VALUES (%(email)s, %(password_hash)s, %(name)s)
                RETURNING user_id, email, name, created_at
            """
            params = {
                "email": email,
                "password_hash": password_hash,
                "name": name
            }
            
            cur.execute(sql, params)
            
            # 생성된 user_id를 포함한 레코드를 가져옵니다.
            new_user = cur.fetchone()
            
            # [중요] SQLAlchemy Core 트랜잭션을 사용하므로, 
            # 외부에서 commit이 관리되지 않는다면 여기서 명시적으로 해줘야 할 수 있습니다.
            # conn.commit() 
            
            return new_user

user_repo = UserRepository()
