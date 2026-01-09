import traceback
import json
import os
from psycopg2.extensions import connection
from psycopg2.extras import RealDictCursor
from app.utils.media_utils import MediaUtils

# Engines
from app.engines.visual.engine import run_visual
from app.engines.voice.engine import run_voice
from app.engines.stt.engine import run_stt
from app.engines.llm.engine import run_content

# Repositories
from app.repositories.answer_repo import answer_repo
from app.repositories.visual_repo import visual_repo
from app.repositories.voice_repo import voice_repo
from app.repositories.content_repo import content_repo
# [NEW] Final Report Repository
from app.repositories.final_report_repo import final_report_repo

# Services
# [NEW] Final Report Service
from app.services.final_report_service import FinalReportService

# Schemas
from app.schemas.visual import VisualDBPayload
from app.schemas.voice import VoiceDBPayload
from app.schemas.content import ContentDBPayload

# [NEW] LLM Client Adapter for FinalReportService
class OpenAIClientAdapter:
    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        """
        FinalReportService가 사용하는 인터페이스(generate)를 
        OpenAI SDK에 맞춰 구현
        """
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model="gpt-4o", # 또는 gpt-3.5-turbo
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                response_format={"type": "json_object"} # JSON 강제
            )
            return response.choices[0].message.content or "{}"
        except Exception as e:
            print(f"LLM Error: {e}")
            return "{}"

# 인스턴스 생성
llm_client = OpenAIClientAdapter()
final_report_service = FinalReportService(llm_client)


class AnalysisService:
    def _get_session_id(self, conn: connection, answer_id: int) -> int:
        """
        answer_id를 통해 session_id를 역추적하는 헬퍼 함수
        (answers -> questions -> interview_sessions)
        """
        with conn.cursor() as cur:
            cur.execute("""
                SELECT q.session_id 
                FROM answers a
                JOIN questions q ON a.question_id = q.question_id
                WHERE a.answer_id = %s
            """, (answer_id,))
            row = cur.fetchone()
            if row:
                return row['session_id']
            return None

    def run_full_analysis(self, conn: connection, answer_id: int, file_path: str):
        print(f"🎬 [Analysis Start] Answer ID: {answer_id}")
        
        # 1. 답변 조회
        answer = answer_repo.get_by_id(conn, answer_id)
        if not answer:
            print("❌ 답변을 찾을 수 없습니다.")
            return

        # 2. 상태 변경
        print(f"🔄 상태 변경: PENDING -> PROCESSING")
        answer_repo.update_analysis_status(conn, answer_id, "PROCESSING")

        # 엔진 결과 담을 변수 초기화
        visual_output = {}
        voice_output = {}
        content_output = {}

        try:
            # 0. 오디오 추출
            print("🔊 오디오 추출 중...")
            audio_path = MediaUtils.extract_audio(file_path)

            # =================================================
            # 1. 비주얼 분석
            # =================================================
            print(f"👁️ 비주얼 분석 시작...")
            visual_output = run_visual(file_path)
            
            if visual_output.get("error"):
                print(f"❌ 비주얼 분석 에러: {visual_output['error']}")
            else:
                v_metrics = visual_output.get("metrics", {})
                
                # 비주얼 점수 계산 로직
                face_ratio = v_metrics.get("face_presence_ratio", 0.0)
                center_ratio = v_metrics.get("head_center_ratio", 0.0)
                score = 100
                feedbacks = []
                
                if face_ratio < 0.8: score -= 20; feedbacks.append("화면 이탈이 잦습니다.")
                if center_ratio < 0.6: score -= 10; feedbacks.append("고개가 중앙에서 벗어났습니다.")
                
                visual_payload = VisualDBPayload(
                    answer_id=answer_id,
                    score=max(0, score),
                    head_center_ratio=center_ratio,
                    feedback=" ".join(feedbacks) or "자세가 훌륭합니다.",
                    good_points_json=[],
                    bad_points_json=[],
                )
                
                # Service에서 JSON 문자열로 변환 (기존 로직 유지)
                visual_data = visual_payload.model_dump()
                visual_data['good_points_json'] = json.dumps(visual_data['good_points_json'])
                visual_data['bad_points_json'] = json.dumps(visual_data['bad_points_json'])
                
                visual_repo.upsert_visual_result(conn, visual_data)
                
                # [중요] FinalReportService에 넘겨주기 위해 score를 metrics에 주입
                visual_output["metrics"]["score"] = max(0, score)
                print(f"✅ 비주얼 분석 저장 완료")


            # =================================================
            # 2. STT 및 음성 분석
            # =================================================
            print(f"🗣️ STT 변환 시작...")
            stt_output = run_stt(audio_path)
            stt_text = ""
            stt_segments = []
            if not stt_output.get("error"):
                stt_text = stt_output["metrics"].get("text", "")
                stt_segments = stt_output["metrics"].get("segments", [])

            print(f"🎙️ 음성 분석 시작...")
            voice_output = run_voice(audio_path, stt_text=stt_text, stt_segments=stt_segments)
            
            if voice_output.get("error"):
                 print(f"❌ 음성 분석 에러: {voice_output['error']}")
            else:
                metrics = voice_output.get("metrics", {})
                
                avg_wpm = metrics.get("avg_wpm") or 0
                max_wpm = metrics.get("max_wpm") or 0
                silence_count = metrics.get("silence_count", 0)
                avg_pitch = metrics.get("avg_pitch") or 0.0
                
                v_score = 100
                good_points = []
                bad_points = []
                
                if avg_wpm < 80: v_score -= 10; bad_points.append("말이 느립니다.")
                elif avg_wpm > 180: v_score -= 10; bad_points.append("말이 빠릅니다.")
                else: good_points.append("속도가 적절합니다.")

                if silence_count > 5: v_score -= 10; bad_points.append("침묵이 잦습니다.")
                else: good_points.append("자연스럽게 말했습니다.")

                voice_payload = VoiceDBPayload(
                    answer_id=answer_id,
                    score=max(0, v_score),
                    avg_wpm=int(avg_wpm),
                    max_wpm=int(max_wpm),
                    silence_count=int(silence_count),
                    avg_silence_length=0.0,
                    avg_pitch=float(avg_pitch),
                    max_pitch=0.0,
                    silence_timeline_json=[],
                    feedback=" ".join(bad_points) or "훌륭합니다.",
                    good_points_json=good_points,
                    bad_points_json=bad_points
                )
                
                voice_data = voice_payload.model_dump()
                voice_data['silence_timeline_json'] = json.dumps(voice_data['silence_timeline_json'])
                voice_data['good_points_json'] = json.dumps(voice_data['good_points_json'])
                voice_data['bad_points_json'] = json.dumps(voice_data['bad_points_json'])

                voice_repo.upsert_voice_result(conn, voice_data)
                
                # [중요] FinalReportService용 점수 주입
                voice_output["metrics"]["score"] = max(0, v_score)
                print(f"✅ 음성 분석 저장 완료")


            # =================================================
            # 3. 내용 분석 (LLM)
            # =================================================
            print(f"📝 내용 분석 시작 (LLM)...")
            
            fillers = ["음", "어", "그", "아"]
            filler_count = 0
            if stt_text:
                for f in fillers: filler_count += stt_text.count(f)

            question_text = answer.get("question_content", "") 
            duration_sec = stt_segments[-1]["end"] if stt_segments else 0.0

            content_output = run_content(
                answer_text=stt_text,
                question_text=question_text,
                duration_sec=duration_sec
            )

            if content_output.get("error"):
                print(f"❌ 내용 분석 에러: {content_output['error']}")
            else:
                c_metrics = content_output.get("metrics", {})
                
                # 종합 점수 계산 (Content Engine이 안 주면 평균으로 계산)
                l_score = c_metrics.get("logic_score", 0)
                j_score = c_metrics.get("job_fit_score", 0)
                t_score = c_metrics.get("time_management_score", 0)
                # 만약 metrics에 'score'가 없다면 임의 계산
                final_content_score = int((l_score + j_score + t_score) / 3)
                
                content_payload = ContentDBPayload(
                    answer_id=answer_id,
                    score=final_content_score, # 여기에 점수 필요
                    logic_score=l_score,
                    job_fit_score=j_score,
                    time_management_score=t_score,
                    filler_count=filler_count,
                    keywords_json=c_metrics.get("keywords", []),
                    feedback=c_metrics.get("feedback", ""),
                    model_answer=c_metrics.get("model_answer"),
                    summarized_text=None
                )
                
                content_data = content_payload.model_dump()
                content_data['keywords_json'] = json.dumps(content_data['keywords_json'])
                
                content_repo.upsert_content_result(conn, content_data)
                
                # [중요] FinalReportService용 점수 주입
                content_output["metrics"]["score"] = final_content_score
                print(f"✅ 내용 분석 저장 완료")


            # =================================================
            # 4. Final Report 생성 (종합 분석)
            # =================================================
            print(f"📊 종합 리포트 생성 시작...")
            
            # (1) Session ID 조회
            session_id = self._get_session_id(conn, answer_id)
            
            if session_id:
                # (2) 리포트 생성 및 저장 (Upsert)
                # 이 함수 내부에서 LLM 호출 -> JSON 파싱 -> DB 저장이 일어납니다.
                report_result = final_report_service.create_or_upsert(
                    conn=conn,
                    session_id=session_id,
                    visual_out=visual_output,
                    voice_out=voice_output,
                    content_out=content_output
                )
                print(f"✅ 종합 리포트 저장 완료 (Total Score: {report_result.total_score})")
            else:
                print(f"⚠️ Session ID를 찾을 수 없어 종합 리포트를 생성하지 못했습니다.")


            # 5. 최종 완료 처리
            answer_repo.update_analysis_status(conn, answer_id, "DONE")
            print(f"🎉 [Analysis Done] Answer ID: {answer_id}")

        except Exception as e:
            print(f"💥 [Analysis Failed] Error: {e}")
            traceback.print_exc()
            answer_repo.update_analysis_status(conn, answer_id, "FAILED")

analysis_service = AnalysisService()