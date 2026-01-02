from psycopg2.extensions import connection
from .base import BaseRepository


class VoiceRepository(BaseRepository):

    def upsert_voice_result(self, conn: connection, payload: dict) -> dict:
        sql = """
        INSERT INTO answer_voice_analysis (
            answer_id,
            score,
            avg_wpm,
            max_wpm,
            silence_count,
            avg_pitch,
            feedback,
            good_points_json,
            bad_points_json
        )
        VALUES (
            %(answer_id)s,
            %(score)s,
            %(avg_wpm)s,
            %(max_wpm)s,
            %(silence_count)s,
            %(avg_pitch)s,
            %(feedback)s,
            %(good_points_json)s,
            %(bad_points_json)s
        )
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
        """
        return self.fetch_one(conn, sql, payload)


voice_repo = VoiceRepository()
