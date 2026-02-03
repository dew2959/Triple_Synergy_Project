from typing import Dict, Any
from psycopg2.extras import RealDictCursor, Json


class VoiceRepository:

    def upsert_voice_result(self, conn, payload: Dict[str, Any]):
        # ---------------------------------------------------------
        # [추가] 파이썬 객체(List/Dict)를 DB JSONB 타입으로 변환
        # Service Layer에서 json.dumps를 안 하고 딕셔너리째로 넘겨도 되도록 처리
        # ---------------------------------------------------------
        # charts_json이 payload에 없으면 빈 딕셔너리 {} 로 처리
        if 'charts_json' not in payload or payload['charts_json'] is None:
            payload['charts_json'] = {}
        
        # 이미 문자열(String)이 아니라면 Json()으로 감싸기
        if not isinstance(payload['charts_json'], str):
            payload['charts_json'] = Json(payload['charts_json'])

        # 기존 JSON 필드들도 안전하게 처리 (필요시 주석 해제하여 사용)
        # payload['good_points_json'] = Json(payload.get('good_points_json', []))
        # payload['bad_points_json'] = Json(payload.get('bad_points_json', []))

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO answer_voice_analysis
                    (
                    answer_id, score, feedback,
                        good_points_json, bad_points_json, charts_json,
                        
                        -- [metrics] Basic
                        avg_wpm, max_wpm, silence_count, duration_sec,
                        
                        -- [metrics] Pitch
                        avg_pitch, max_pitch, pitch_std, voiced_ratio,
                        
                        -- [metrics] Speed (CPS/CPM)
                        avg_cps, avg_cpm,
                        
                        -- [metrics] Instability
                        burst_ratio, high_speed_share, cv_cps
                    )  
                VALUES
                    (
                        %(answer_id)s, %(score)s, %(feedback)s,
                        %(good_points_json)s, %(bad_points_json)s, %(charts_json)s,
                        
                        %(avg_wpm)s, %(max_wpm)s, %(silence_count)s, %(duration_sec)s,
                        %(avg_pitch)s, %(max_pitch)s, %(pitch_std)s, %(voiced_ratio)s,
                        %(avg_cps)s, %(avg_cpm)s,
                        %(burst_ratio)s, %(high_speed_share)s, %(cv_cps)s
                    )
                ON CONFLICT (answer_id)
                DO UPDATE SET
                    score = EXCLUDED.score,
                    feedback = EXCLUDED.feedback,
                    good_points_json = EXCLUDED.good_points_json,
                    bad_points_json = EXCLUDED.bad_points_json,
                    charts_json = EXCLUDED.charts_json,
                    
                    -- Metrics 업데이트
                    avg_wpm = EXCLUDED.avg_wpm,
                    max_wpm = EXCLUDED.max_wpm,
                    silence_count = EXCLUDED.silence_count,
                    duration_sec = EXCLUDED.duration_sec,
                    
                    avg_pitch = EXCLUDED.avg_pitch,
                    max_pitch = EXCLUDED.max_pitch,
                    pitch_std = EXCLUDED.pitch_std,
                    voiced_ratio = EXCLUDED.voiced_ratio,
                    
                    avg_cps = EXCLUDED.avg_cps,
                    avg_cpm = EXCLUDED.avg_cpm,
                    
                    burst_ratio = EXCLUDED.burst_ratio,
                    high_speed_share = EXCLUDED.high_speed_share,
                    cv_cps = EXCLUDED.cv_cps
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
