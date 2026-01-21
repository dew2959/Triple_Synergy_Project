import traceback
import json
import os
from psycopg2.extensions import connection
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
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content or "{}"
        except Exception as e:
            print(f"❌ [LLM Client Error] {e}")
            return "{}"

# 인스턴스 생성
llm_client = OpenAIClientAdapter()
final_report_service = FinalReportService(llm_client)


class AnalysisService:
    
    # =========================================================================
    # 기능 1: 개별 답변 분석 (Visual, Voice, Content)
    # =========================================================================
    def run_answer_analysis(self, conn: connection, answer_id: int, file_path: str):
        """
        단일 답변 영상에 대해 3가지 엔진(Visual, Voice, Content)을 돌리고 결과를 저장합니다.
        (파이널 리포트는 생성하지 않습니다.)
        """
        print(f"🎬 [Answer Analysis Start] Answer ID: {answer_id}")
        
        # 1. 답변 조회
        answer = answer_repo.get_by_id(conn, answer_id)
        if not answer:
            print(f"❌ [Error] Answer ID {answer_id} not found in DB.")
            return

        # 2. 상태 변경 (PENDING -> PROCESSING)
        answer_repo.update_analysis_status(conn, answer_id, "PROCESSING")

        try:
            # -------------------------------------------------
            # 0. 미디어 전처리 (압축 + 오디오 추출)
            # -------------------------------------------------
            print(f"🔨 미디어 처리 중... (파일: {file_path})")
            
            try:
                # (1) 영상 압축
                optimized_video_path = MediaUtils.compress_video(file_path, overwrite=True)
                
                # (2) 오디오 추출
                audio_path = MediaUtils.extract_audio(optimized_video_path, overwrite=True)
                
                # (3) 경로 업데이트
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE answers SET audio_path = %s WHERE answer_id = %s",
                        (audio_path, answer_id)
                    )
                    conn.commit()
            except Exception as e:
                print(f"❌ [Media Error] 미디어 변환 중 실패: {e}")
                raise e  # 미디어 실패 시 분석 불가하므로 상위 catch로 던짐

            # -------------------------------------------------
            # 1. 비주얼 분석
            # -------------------------------------------------
            print(f"👁️ 비주얼 분석 시작...")
            visual_output = run_visual(optimized_video_path)
            
            if visual_output.get("error"):
                print(f"❌ [Visual Engine Error] {visual_output['error']}")
            else:
                try:
                    v_metrics = visual_output.get("metrics", {})
                    score = 100
                    feedbacks = []
                    
                    if v_metrics.get("face_presence_ratio", 0.0) < 0.8: score -= 20; feedbacks.append("화면 이탈이 잦습니다.")
                    if v_metrics.get("head_center_ratio", 0.0) < 0.6: score -= 10; feedbacks.append("고개가 중앙에서 벗어났습니다.")
                    
                    visual_payload = VisualDBPayload(
                        answer_id=answer_id,
                        score=max(0, score),
                        head_center_ratio=v_metrics.get("head_center_ratio", 0.0),
                        feedback=" ".join(feedbacks) or "자세가 훌륭합니다.",
                        good_points_json=[], bad_points_json=[],
                    )
                    v_data = visual_payload.model_dump()
                    v_data['good_points_json'] = json.dumps(v_data['good_points_json'])
                    v_data['bad_points_json'] = json.dumps(v_data['bad_points_json'])
                    
                    visual_repo.upsert_visual_result(conn, v_data)
                    print(f"✅ 비주얼 분석 저장 완료")
                except Exception as e:
                    print(f"❌ [Visual Save Error] 결과 저장 실패: {e}")
                    traceback.print_exc()

            # -------------------------------------------------
            # 2. 음성 분석
            # -------------------------------------------------
            print(f"🗣️ STT & 음성 분석 시작...")
            stt_output = run_stt(audio_path)
            stt_text = ""
            stt_segments = []

            if stt_output.get("error"):
                print(f"❌ [STT Error] {stt_output['error']}")
            else:
                stt_text = stt_output["metrics"].get("text", "")
                stt_segments = stt_output["metrics"].get("segments", [])
                
                # STT 결과 저장
                try:
                    with conn.cursor() as cur:
                        cur.execute("UPDATE answers SET stt_text = %s WHERE answer_id = %s", (stt_text, answer_id))
                except Exception as e:
                    print(f"⚠️ [STT Save Warning] 텍스트 저장 실패 (계속 진행): {e}")

            voice_output = run_voice(audio_path, stt_text=stt_text, stt_segments=stt_segments)
            
            if voice_output.get("error"):
                 print(f"❌ [Voice Engine Error] {voice_output['error']}")
            else:
                try:
                    metrics = voice_output.get("metrics", {})
                    avg_wpm = metrics.get("avg_wpm") or 0
                    silence_count = metrics.get("silence_count", 0)
                    v_score = 100
                    bad_points = []
                    good_points = []
                    
                    if avg_wpm < 80: v_score -= 10; bad_points.append("말이 느립니다.")
                    elif avg_wpm > 180: v_score -= 10; bad_points.append("말이 빠릅니다.")
                    else: good_points.append("속도가 적절합니다.")
                    
                    if silence_count > 5: v_score -= 10; bad_points.append("침묵이 잦습니다.")

                    voice_payload = VoiceDBPayload(
                        answer_id=answer_id,
                        score=max(0, v_score),
                        avg_wpm=int(avg_wpm),
                        max_wpm=int(metrics.get("max_wpm", 0)),
                        silence_count=int(silence_count),
                        avg_silence_length=0.0,
                        avg_pitch=float(metrics.get("avg_pitch", 0.0)),
                        max_pitch=0.0,
                        silence_timeline_json=[],
                        feedback=" ".join(bad_points) or "훌륭합니다.",
                        good_points_json=good_points, bad_points_json=bad_points
                    )
                    
                    a_data = voice_payload.model_dump()
                    a_data['silence_timeline_json'] = json.dumps(a_data['silence_timeline_json'])
                    a_data['good_points_json'] = json.dumps(a_data['good_points_json'])
                    a_data['bad_points_json'] = json.dumps(a_data['bad_points_json'])
                    
                    voice_repo.upsert_voice_result(conn, a_data)
                    print(f"✅ 음성 분석 저장 완료")
                except Exception as e:
                    print(f"❌ [Voice Save Error] 결과 저장 실패: {e}")
                    traceback.print_exc()

            # -------------------------------------------------
            # 3. 내용 분석
            # -------------------------------------------------
            print(f"📝 내용 분석 시작...")
            question_text = answer.get("question_content", "")
            duration_sec = stt_segments[-1]["end"] if stt_segments else 0.0
            
            content_output = run_content(
                answer_text=stt_text, 
                question_text=question_text, 
                duration_sec=duration_sec
            )
            
            if content_output.get("error"):
                print(f"❌ [Content Engine Error] {content_output['error']}")
            else:
                try:
                    c_metrics = content_output.get("metrics", {})
                    l_score = c_metrics.get("logic_score", 0)
                    j_score = c_metrics.get("job_fit_score", 0)
                    t_score = c_metrics.get("time_management_score", 0)
                    final_c_score = int((l_score + j_score + t_score) / 3)
                    
                    filler_count = stt_text.count("음") + stt_text.count("어")

                    content_payload = ContentDBPayload(
                        answer_id=answer_id,
                        score=final_c_score,
                        logic_score=l_score,
                        job_fit_score=j_score,
                        time_management_score=t_score,
                        filler_count=filler_count,
                        keywords_json=c_metrics.get("keywords", []),
                        feedback=c_metrics.get("feedback", ""),
                        model_answer=c_metrics.get("model_answer"),
                        summarized_text=None
                    )
                    c_data = content_payload.model_dump()
                    c_data['keywords_json'] = json.dumps(c_data['keywords_json'])
                    
                    content_repo.upsert_content_result(conn, c_data)
                    print(f"✅ 내용 분석 저장 완료")
                except Exception as e:
                    print(f"❌ [Content Save Error] 결과 저장 실패: {e}")
                    traceback.print_exc()

            # 최종 완료 처리
            answer_repo.update_analysis_status(conn, answer_id, "DONE")
            print(f"🎉 [Answer Analysis Done] Answer ID: {answer_id}")

        except Exception as e:
            # 전체 프로세스 중 잡히지 않은 에러 처리
            print(f"💥 [Critical Analysis Failed] Answer ID {answer_id}")
            print(f"   Error Detail: {e}")
            print("   Traceback:")
            print(traceback.format_exc()) # 스택 트레이스 전체 출력
            
            try:
                answer_repo.update_analysis_status(conn, answer_id, "FAILED")
            except:
                print("   (DB Status Update Failed too)")


    # =========================================================================
    # 기능 2: 세션 종합 리포트 생성 (모든 답변 완료 후 호출 권장)
    # =========================================================================
    def generate_session_report(self, conn: connection, session_id: int):
        """
        특정 세션의 모든 답변 데이터를 조회하여 종합 리포트를 생성/갱신합니다.
        """
        print(f"📊 [Session Report Start] Session ID: {session_id}")
        
        try:
            # FinalReportService가 알아서 DB 긁어와서 처리함
            report_result = final_report_service.create_or_upsert(conn, session_id)
            
            if report_result:
                print(f"✅ 종합 리포트 생성 완료 (Total Score: {report_result.total_score})")
                return report_result
            else:
                print(f"⚠️ [Report Warning] 리포트 생성 실패 (데이터 없음)")
                return None
                
        except Exception as e:
            print(f"💥 [Session Report Failed] Error: {e}")
            print(traceback.format_exc()) # 스택 트레이스 출력
            return None

analysis_service = AnalysisService()