from typing import Optional
from psycopg2.extensions import connection
from .base import BaseRepository

class UserRepository(BaseRepository):
    
    def create(self, conn: connection, email: str, password_hash: str, name: str) -> dict:
        sql = """
        INSERT INTO users (email, password_hash, name)
        VALUES (%(email)s, %(password_hash)s, %(name)s)
        RETURNING user_id, email, name, created_at
        """
        # 비밀번호 해시는 여기서 만들지 않고 Service에서 받아서 저장만 함
        return self.fetch_one(conn, sql, {
            "email": email,
            "password_hash": password_hash,
            "name": name
        })

    def get_by_email(self, conn: connection, email: str) -> Optional[dict]:
        sql = "SELECT * FROM users WHERE email = %(email)s"
        return self.fetch_one(conn, sql, {"email": email})

    def get_by_id(self, conn: connection, user_id: int) -> Optional[dict]:
        sql = "SELECT * FROM users WHERE user_id = %(user_id)s"
        return self.fetch_one(conn, sql, {"user_id": user_id})

user_repo = UserRepository()