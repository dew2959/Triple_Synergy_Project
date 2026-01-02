from typing import Optional
from psycopg2.extras import RealDictCursor
from app.core.db import with_connection


class AnswerRepository:

    @with_connection
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

    @with_connection
    def get_by_id(self, conn, answer_id: int):
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM answers WHERE answer_id = %s",
                (answer_id,)
            )
            return cur.fetchone()

    @with_connection
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

    @with_connection
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


answer_repo = AnswerRepository()
