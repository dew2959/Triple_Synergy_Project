from typing import Dict, Any
from psycopg2.extras import RealDictCursor


class VisualRepository:

    def upsert_visual_result(self, conn, payload: Dict[str, Any]):
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO answer_visual_analysis
                    (answer_id, score, head_center_ratio, feedback,
                     good_points_json, bad_points_json)
                VALUES
                    (%(answer_id)s, %(score)s, %(head_center_ratio)s,
                     %(feedback)s, %(good_points_json)s, %(bad_points_json)s)
                ON CONFLICT (answer_id)
                DO UPDATE SET
                    score = EXCLUDED.score,
                    head_center_ratio = EXCLUDED.head_center_ratio,
                    feedback = EXCLUDED.feedback,
                    good_points_json = EXCLUDED.good_points_json,
                    bad_points_json = EXCLUDED.bad_points_json
                RETURNING *
                """,
                payload
            )
            return cur.fetchone()

    # 기존 클래스 내부에 추가
    def get_by_answer_id(self, conn, answer_id: int):
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM answer_visual_analysis WHERE answer_id = %s",
                (answer_id,)
            )
            return cur.fetchone()

visual_repo = VisualRepository()
