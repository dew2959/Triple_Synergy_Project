import traceback
import json  # 👈 [필수] 이거 꼭 추가해주세요!
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

# Schemas
from app.schemas.visual import VisualDBPayload
from app.schemas.voice import VoiceDBPayload
from app.schemas.content import ContentDBPayload


class AnalysisService:
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
                
                # 점수 계산 로직
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
                
                # 🟡 [수정] Service에서 JSON 문자열로 변환
                visual_data = visual_payload.model_dump()
                visual_data['good_points_json'] = json.dumps(visual_data['good_points_json'])
                visual_data['bad_points_json'] = json.dumps(visual_data['bad_points_json'])
                
                visual_repo.upsert_visual_result(conn, visual_data)
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
                
                # 🟡 [수정] Service에서 JSON 문자열로 변환 후 Repo에 전달
                voice_data = voice_payload.model_dump()
                voice_data['silence_timeline_json'] = json.dumps(voice_data['silence_timeline_json'])
                voice_data['good_points_json'] = json.dumps(voice_data['good_points_json'])
                voice_data['bad_points_json'] = json.dumps(voice_data['bad_points_json'])

                voice_repo.upsert_voice_result(conn, voice_data)
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
                
                content_payload = ContentDBPayload(
                    answer_id=answer_id,
                    logic_score=c_metrics.get("logic_score", 0),
                    job_fit_score=c_metrics.get("job_fit_score", 0),
                    time_management_score=c_metrics.get("time_management_score", 0),
                    filler_count=filler_count,
                    keywords_json=c_metrics.get("keywords", []),
                    feedback=c_metrics.get("feedback", ""),
                    model_answer=c_metrics.get("model_answer"),
                    summarized_text=None
                )
                
                # 🟡 [수정] Service에서 JSON 문자열로 변환
                content_data = content_payload.model_dump()
                content_data['keywords_json'] = json.dumps(content_data['keywords_json'])
                
                content_repo.upsert_content_result(conn, content_data)
                print(f"✅ 내용 분석 저장 완료")


            # 4. 최종 완료 처리
            answer_repo.update_analysis_status(conn, answer_id, "DONE")
            print(f"🎉 [Analysis Done] Answer ID: {answer_id}")

        except Exception as e:
            print(f"💥 [Analysis Failed] Error: {e}")
            traceback.print_exc()
            answer_repo.update_analysis_status(conn, answer_id, "FAILED")

analysis_service = AnalysisService()