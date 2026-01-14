from psycopg2.extras import RealDictCursor

class SessionRepository:
    def create(self, conn, user_id: int, resume_id: int, job_role: str, company_name: str):
        """
        이력서 정보를 바탕으로 새 면접 세션 생성
        """
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO interview_sessions (
                    user_id, resume_id, job_role, company_name, status
                )
                VALUES (
                    %(user_id)s, %(resume_id)s, %(job_role)s, %(company_name)s, 'READY'
                )
                RETURNING *
                """,
                {
                    "user_id": user_id,
                    "resume_id": resume_id,
                    "job_role": job_role,
                    "company_name": company_name
                }
            )
            return cur.fetchone()

    def get_by_id(self, conn, session_id: int):
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM interview_sessions WHERE session_id = %s",
                (session_id,)
            )
            return cur.fetchone()
        
    def update_status(self, conn, session_id: int, status: str):
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE interview_sessions SET status = %s WHERE session_id = %s",
                (status, session_id)
            )

    def get_all_by_user_id(self, conn, user_id: int):
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM interview_sessions 
                WHERE user_id = %s 
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
            return cur.fetchall()
session_repo = SessionRepository()