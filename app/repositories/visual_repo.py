from typing import Dict, Any
from psycopg2.extensions import connection
from .base import BaseRepository


class VisualRepository(BaseRepository):

    def upsert_visual_result(
        self,
        conn: connection,
        payload: Dict[str, Any]
    ) -> dict:
        sql = """
        INSERT INTO answer_visual_analysis (
            answer_id,
            score,
            head_center_ratio,
            feedback,
            good_points_json,
            bad_points_json
        )
        VALUES (
            %(answer_id)s,
            %(score)s,
            %(head_center_ratio)s,
            %(feedback)s,
            %(good_points_json)s,
            %(bad_points_json)s
        )
        ON CONFLICT (answer_id)
        DO UPDATE SET
            score = EXCLUDED.score,
            head_center_ratio = EXCLUDED.head_center_ratio,
            feedback = EXCLUDED.feedback,
            good_points_json = EXCLUDED.good_points_json,
            bad_points_json = EXCLUDED.bad_points_json
        RETURNING *
        """
        return self.fetch_one(conn, sql, payload)


visual_repo = VisualRepository()
