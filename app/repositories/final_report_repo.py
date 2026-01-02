from typing import Dict, Any
from psycopg2.extras import RealDictCursor
from app.core.db import with_connection

class FinalReportRepository:

    @with_connection
    def upsert_final_report(self, conn, payload: Dict[str, Any]):
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO final_reports
                    (session_id, total_score, summary_headline,
                     overall_feedback, avg_visual_score,
                     avg_voice_score, avg_content_score,
                     visual_strengths_json, visual_weaknesses_json,
                     voice_strengths_json, voice_weaknesses_json,
                     content_strengths_json, content_weaknesses_json,
                     action_plans_json)
                VALUES
                    (%(session_id)s, %(total_score)s, %(summary_headline)s,
                     %(overall_feedback)s, %(avg_visual_score)s,
                     %(avg_voice_score)s, %(avg_content_score)s,
                     %(visual_strengths_json)s, %(visual_weaknesses_json)s,
                     %(voice_strengths_json)s, %(voice_weaknesses_json)s,
                     %(content_strengths_json)s, %(content_weaknesses_json)s,
                     %(action_plans_json)s)
                ON CONFLICT (session_id)
                DO UPDATE SET
                    total_score = EXCLUDED.total_score,
                    summary_headline = EXCLUDED.summary_headline,
                    overall_feedback = EXCLUDED.overall_feedback,
                    avg_visual_score = EXCLUDED.avg_visual_score,
                    avg_voice_score = EXCLUDED.avg_voice_score,
                    avg_content_score = EXCLUDED.avg_content_score,
                    visual_strengths_json = EXCLUDED.visual_strengths_json,
                    visual_weaknesses_json = EXCLUDED.visual_weaknesses_json,
                    voice_strengths_json = EXCLUDED.voice_strengths_json,
                    voice_weaknesses_json = EXCLUDED.voice_weaknesses_json,
                    content_strengths_json = EXCLUDED.content_strengths_json,
                    content_weaknesses_json = EXCLUDED.content_weaknesses_json,
                    action_plans_json = EXCLUDED.action_plans_json
                RETURNING *
                """,
                payload
            )
            return cur.fetchone()


final_report_repo = FinalReportRepository()
