from psycopg2.extensions import connection
from .base import BaseRepository


class ContentRepository(BaseRepository):

    def upsert_content_result(self, conn: connection, payload: dict) -> dict:
        sql = """
        INSERT INTO answer_content_analysis (
            answer_id,
            logic_score,
            job_fit_score,
            time_management_score,
            feedback,
            model_answer,
            keywords_json
        )
        VALUES (
            %(answer_id)s,
            %(logic_score)s,
            %(job_fit_score)s,
            %(time_management_score)s,
            %(feedback)s,
            %(model_answer)s,
            %(keywords_json)s
        )
        ON CONFLICT (answer_id)
        DO UPDATE SET
            logic_score = EXCLUDED.logic_score,
            job_fit_score = EXCLUDED.job_fit_score,
            time_management_score = EXCLUDED.time_management_score,
            feedback = EXCLUDED.feedback,
            model_answer = EXCLUDED.model_answer,
            keywords_json = EXCLUDED.keywords_json
        RETURNING *
        """
        return self.fetch_one(conn, sql, payload)


content_repo = ContentRepository()
