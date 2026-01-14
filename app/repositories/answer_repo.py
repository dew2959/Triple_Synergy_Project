from typing import Optional
from psycopg2.extras import RealDictCursor


class AnswerRepository:

    def create(
        self,
        conn,
        question_id: int,
        video_path: str,
        audio_path: Optional[str] = None
    ):
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO answers
                    (question_id, video_path, audio_path, stt_text, analysis_status)
                VALUES
                    (%s, %s, %s, %s, 'PENDING')
                RETURNING *
                """,
                (question_id, video_path, audio_path, None)
            )
            return cur.fetchone()

    def get_by_id(self, conn, answer_id: int):
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM answers WHERE answer_id = %s",
                (answer_id,)
            )
            return cur.fetchone()

    def update_analysis_status(self, conn, answer_id: int, status: str):
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE answers
                SET analysis_status = %s
                WHERE answer_id = %s
                """,
                (status, answer_id)
            )

    def update_stt_result(self, conn, answer_id: int, stt_text: str):
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE answers
                SET stt_text = %s
                WHERE answer_id = %s
                """,
                (stt_text, answer_id)
            )

    def get_all_by_session_id(self, conn, session_id: int):
        """특정 세션에 속한 모든 답변 조회"""
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT a.answer_id, a.video_path 
                FROM answers a
                JOIN questions q ON a.question_id = q.question_id
                WHERE q.session_id = %s
                """,
                (session_id,)
            )
            return cur.fetchall()

answer_repo = AnswerRepository()
