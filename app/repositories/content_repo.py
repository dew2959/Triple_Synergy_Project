from typing import Dict, Any
from psycopg2.extras import RealDictCursor


class ContentRepository:

    def upsert_content_result(self, conn, payload: Dict[str, Any]):
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO answer_content_analysis
                    (answer_id, logic_score, job_fit_score,
                     time_management_score, feedback,
                     model_answer, keywords_json)
                VALUES
                    (%(answer_id)s, %(logic_score)s, %(job_fit_score)s,
                     %(time_management_score)s, %(feedback)s,
                     %(model_answer)s, %(keywords_json)s)
                ON CONFLICT (answer_id)
                DO UPDATE SET
                    logic_score = EXCLUDED.logic_score,
                    job_fit_score = EXCLUDED.job_fit_score,
                    time_management_score = EXCLUDED.time_management_score,
                    feedback = EXCLUDED.feedback,
                    model_answer = EXCLUDED.model_answer,
                    keywords_json = EXCLUDED.keywords_json
                RETURNING *
                """,
                payload
            )
            return cur.fetchone()

    # 기존 클래스 내부에 추가
    def get_by_answer_id(self, conn, answer_id: int):
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM answer_content_analysis WHERE answer_id = %s",
                (answer_id,)
            )
            return cur.fetchone()
        
content_repo = ContentRepository()
