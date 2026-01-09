from typing import Dict, Any
from psycopg2.extras import RealDictCursor


class VoiceRepository:

    def upsert_voice_result(self, conn, payload: Dict[str, Any]):
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO answer_voice_analysis
                    (answer_id, score, avg_wpm, max_wpm,
                     silence_count, avg_pitch, feedback,
                     good_points_json, bad_points_json)
                VALUES
                    (%(answer_id)s, %(score)s, %(avg_wpm)s, %(max_wpm)s,
                     %(silence_count)s, %(avg_pitch)s, %(feedback)s,
                     %(good_points_json)s, %(bad_points_json)s)
                ON CONFLICT (answer_id)
                DO UPDATE SET
                    score = EXCLUDED.score,
                    avg_wpm = EXCLUDED.avg_wpm,
                    max_wpm = EXCLUDED.max_wpm,
                    silence_count = EXCLUDED.silence_count,
                    avg_pitch = EXCLUDED.avg_pitch,
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
                "SELECT * FROM answer_voice_analysis WHERE answer_id = %s",
                (answer_id,)
            )
            return cur.fetchone()


voice_repo = VoiceRepository()
