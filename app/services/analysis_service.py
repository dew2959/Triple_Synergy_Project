import traceback
import json
import os
from psycopg2.extensions import connection
from app.utils.media_utils import MediaUtils

# Engines
from app.engines.visual.engine import visual_engine
from app.engines.voice.engine import run_voice
from app.engines.stt.engine import run_stt
from app.engines.llm.engine import run_content

# Repositories
from app.repositories.answer_repo import answer_repo
from app.repositories.visual_repo import visual_repo
from app.repositories.voice_repo import voice_repo
from app.repositories.content_repo import content_repo

# Services
from app.services.final_report_service import final_report_service
from app.utils.chart_utils import calculate_cps_flow

# Schemas
from app.schemas.visual import VisualDBPayload
from app.schemas.voice import VoiceDBPayload
from app.schemas.content import ContentDBPayload


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

        # 2. 상태 변경 (PENDING -> PROCESSING) + ✅ commit
        try:
            answer_repo.update_analysis_status(conn, answer_id, "PROCESSING")
            conn.commit()
        except Exception as e:
            try:
                conn.rollback()
            except:
                pass
            print(f"❌ [DB Error] Failed to set PROCESSING: {e}")
            return

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

                # (3) 경로 업데이트 + ✅ commit
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE answers SET audio_path = %s WHERE answer_id = %s",
                        (audio_path, answer_id),
                    )
                conn.commit()

            except Exception as e:
                try:
                    conn.rollback()
                except:
                    pass
                print(f"❌ [Media Error] 미디어 변환 중 실패: {e}")
                raise  # 미디어 실패 시 분석 불가

            # -------------------------------------------------
            # 1. 비주얼 분석 (V3 적용)
            # -------------------------------------------------
            print(f"👁️ 비주얼 분석 시작...")
            
            # 🔴 [수정] visual_engine.analyze() 호출
            visual_output = visual_engine.analyze(optimized_video_path)

            if visual_output.get("error"):
                print(f"❌ [Visual Engine Error] {visual_output['error']}")
            else:
                try:
                    # V3 결과 추출
                    v_score = visual_output.get("score", 0)
                    v_feedback = visual_output.get("feedback", "")
                    v_details = visual_output.get("details", {})
                    details_str = json.dumps(v_details, default=str)
                    # DB 저장용 Payload 생성
                    # - head_center_ratio: V3에서는 미사용이므로 0.0 처리
                    # - good_points_json: V3의 상세 데이터(details)를 저장하여 프론트엔드 차트 등에서 활용
                    visual_payload = VisualDBPayload(
                        answer_id=answer_id,
                        score=v_score,
                        head_center_ratio=0.0, 
                        feedback=v_feedback,
                        good_points_json=[details_str], # 상세 데이터 저장
                        bad_points_json=[], # 감점 사유는 feedback 텍스트에 포함됨
                    )
                    
                    v_data = visual_payload.model_dump()
                    v_data["good_points_json"] = json.dumps(v_data["good_points_json"])
                    v_data["bad_points_json"] = json.dumps(v_data["bad_points_json"])

                    visual_repo.upsert_visual_result(conn, v_data)
                    conn.commit()
                    print(f"✅ 비주얼 분석 저장 완료")

                except Exception as e:
                    try: conn.rollback()
                    except: pass
                    print(f"❌ [Visual Save Error] 결과 저장 실패: {e}")
                    traceback.print_exc()

            # -------------------------------------------------
            # 2. STT & 음성 분석
            # -------------------------------------------------
            print(f"🗣️ STT & 음성 분석 시작...")
            stt_output = run_stt(audio_path)
            stt_text = ""
            stt_segments = []

            if stt_output.get("error"):
                print(f"❌ [STT Error] {stt_output['error']}")
            else:
                stt_text = (stt_output.get("metrics") or {}).get("text", "")
                stt_segments = (stt_output.get("metrics") or {}).get("segments", [])

                # STT 결과 저장 + ✅ commit
                try:
                    # repo 함수 써도 되고(아래), 지금처럼 직접 SQL도 OK
                    answer_repo.update_stt_result(conn, answer_id, stt_text)
                    conn.commit()
                    print("✅ STT 텍스트 저장 완료")
                except Exception as e:
                    try:
                        conn.rollback()
                    except:
                        pass
                    print(f"⚠️ [STT Save Warning] 텍스트 저장 실패 (계속 진행): {e}")

            # [추가] 1. 차트 데이터 미리 계산 (STT 세그먼트 활용)
            speed_flow_data = calculate_cps_flow(stt_segments)

            voice_output = run_voice(audio_path, stt_text=stt_text, stt_segments=stt_segments)

            if voice_output.get("error"):
                print(f"❌ [Voice Engine Error] {voice_output['error']}")
            else:
                try:
                    metrics = voice_output.get("metrics", {})
                    avg_wpm = metrics.get("avg_wpm") or 0
                    silence_count = metrics.get("silence_count", 0)
                    duration_sec = metrics.get("duration_sec") or 1  # duration이 없으면 1로 설정 (나누기 오류 방지)

                    # 1. 점수 체계 세분화 (기본 점수에서 시작하여 항목별 감점)
                    v_score = 100
                    bad_points = []
                    good_points = []

                    # 2. 속도(WPM) 분석: 면접 최적 속도는 110~150 WPM입니다.
                    if 90 <= avg_wpm <= 130:
                        good_points.append("말하기 속도가 매우 안정적입니다.")
                    elif 60 <= avg_wpm < 90:
                        v_score -= 5
                        bad_points.append("말이 다소 느린 편입니다. 조금 더 활기차게 전달해 보세요.")
                    elif avg_wpm < 60:
                        v_score -= 15 # 감점 폭 확대
                        bad_points.append("말이 너무 느려 지루한 인상을 줄 수 있습니다.")
                    elif 130 < avg_wpm <= 160:
                        v_score -= 5
                        bad_points.append("말이 다소 빠릅니다. 중요한 부분에서 호흡을 가다듬어 주세요.")
                    else: # 160 초과
                        v_score -= 15
                        bad_points.append("말이 너무 빨라 내용 전달력이 떨어집니다.")

                    # 3. 침묵(Silence) 분석: 시간 대비 비율로 계산 (중요!)
                    # 면접에서는 1분(60초)당 3~4번의 적절한 멈춤은 정상입니다.
                    # 하지만 60초 기준 5번 이상 혹은 전체 시간의 20% 이상이 침묵이면 감점합니다.
                    silence_per_minute = (silence_count / duration_sec) * 60
                    if silence_per_minute > 8: # 1분에 8회 이상 멈춤 (잦은 끊김)
                        v_score -= 20
                        bad_points.append("답변 중 흐름이 자주 끊깁니다. 문장을 끝까지 맺는 연습이 필요합니다.")
                    elif silence_per_minute > 5:
                        v_score -= 10
                        bad_points.append("말 사이의 공백이 잦아 답변이 다소 불안정해 보입니다.")
                    elif 1 <= silence_per_minute <= 4:
                        good_points.append("적절한 휴지(Pause)를 활용하여 전달력을 높였습니다.")

                    voice_payload = VoiceDBPayload(
                        answer_id=answer_id,
                        score=max(0, v_score),
                        feedback=" ".join(bad_points) if bad_points else "음성 전달력이 매우 훌륭합니다.",
                        
                        # 1. [기존] 속도 및 침묵 (Basic)
                        avg_wpm=int(avg_wpm),
                        max_wpm=int(metrics.get("max_wpm", 0)),
                        silence_count=int(silence_count),
                        avg_silence_length=0.0,   # 기존 유지
                        silence_timeline_json=[], # 기존 유지
                        
                        # 2. [추가] 시간 및 상세 속도 (CPS/CPM)
                        duration_sec=float(metrics.get("duration_sec", 0.0)),
                        avg_cps=float(metrics.get("avg_cps", 0.0)),
                        avg_cpm=float(metrics.get("avg_cpm", 0.0)),

                        # 3. [추가] 피치(Pitch) 상세 분석
                        avg_pitch=float(metrics.get("avg_pitch", 0.0)),
                        max_pitch=float(metrics.get("max_pitch", 0.0)),
                        pitch_std=float(metrics.get("pitch_std", 0.0)),
                        voiced_ratio=float(metrics.get("voiced_ratio", 0.0)),

                        # 4. [추가] 불안정성(Instability) 지표
                        burst_ratio=float(metrics.get("burst_ratio", 0.0)),
                        high_speed_share=float(metrics.get("high_speed_share", 0.0)),
                        cv_cps=float(metrics.get("cv_cps", 0.0)),

                        # 5. [JSON] 피드백 및 차트 데이터
                        good_points_json=good_points,
                        bad_points_json=bad_points,
                        
                        # Service Layer에서 계산한 차트 데이터를 여기에 주입
                        charts_json={"speed_flow": speed_flow_data}
                    )
                    
                    # voice_payload 생성 부분 (v_score와 feedback_text 사용)
                    a_data = voice_payload.model_dump()

                    # -----------------------------------------------------------
                    # [추가] 2. 딕셔너리에 차트 데이터 주입 (Injection)
                    # -----------------------------------------------------------
                    
                    charts_data = {
                        "speed_flow": speed_flow_data
                    }
                    a_data["charts_json"] = {'speed_flow': speed_flow_data}

                    a_data["silence_timeline_json"] = json.dumps(a_data["silence_timeline_json"])
                    a_data["good_points_json"] = json.dumps(a_data["good_points_json"])
                    a_data["bad_points_json"] = json.dumps(a_data["bad_points_json"])

                    voice_repo.upsert_voice_result(conn, a_data)
                    conn.commit()  # ✅ commit
                    print(f"✅ 음성 분석 저장 완료")

                except Exception as e:
                    try:
                        conn.rollback()
                    except:
                        pass
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
                duration_sec=duration_sec,
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
                        summarized_text=None,
                    )
                    c_data = content_payload.model_dump()
                    c_data["keywords_json"] = json.dumps(c_data["keywords_json"])

                    content_repo.upsert_content_result(conn, c_data)
                    conn.commit()  # ✅ commit
                    print(f"✅ 내용 분석 저장 완료")

                except Exception as e:
                    try:
                        conn.rollback()
                    except:
                        pass
                    print(f"❌ [Content Save Error] 결과 저장 실패: {e}")
                    traceback.print_exc()

            # -------------------------------------------------
            # 최종 완료 처리 + ✅ commit
            # -------------------------------------------------
            try:
                answer_repo.update_analysis_status(conn, answer_id, "DONE")
                conn.commit()
                print(f"🎉 [Answer Analysis Done] Answer ID: {answer_id}")
            except Exception as e:
                try:
                    conn.rollback()
                except:
                    pass
                print(f"❌ [DB Error] Failed to set DONE: {e}")

        except Exception as e:
            # 전체 프로세스 중 잡히지 않은 에러 처리
            print(f"💥 [Critical Analysis Failed] Answer ID {answer_id}")
            print(f"   Error Detail: {e}")
            print("   Traceback:")
            print(traceback.format_exc())

            # ✅ 실패 직후 트랜잭션 정리
            try:
                conn.rollback()
            except:
                pass

            # ✅ FAILED 상태 반영 + commit
            try:
                answer_repo.update_analysis_status(conn, answer_id, "FAILED")
                conn.commit()
            except Exception as e2:
                try:
                    conn.rollback()
                except:
                    pass
                print(f"   (DB Status Update Failed too): {e2}")

    # =========================================================================
    # 기능 2: 세션 종합 리포트 생성 (모든 답변 완료 후 호출 권장)
    # =========================================================================
    def generate_session_report(self, conn: connection, session_id: int):
        """
        특정 세션의 모든 답변 데이터를 조회하여 종합 리포트를 생성/갱신합니다.
        """
        print(f"📊 [Session Report Start] Session ID: {session_id}")

        try:
            report_result = final_report_service.create_or_upsert(conn, session_id)
            # (create_or_upsert 내부에서 커밋을 하는지 여부에 따라 여기서 commit이 필요할 수도 있음)
            # 안전하게 하려면:
            try:
                conn.commit()
            except:
                pass

            if report_result:
                print(f"✅ 종합 리포트 생성 완료 (Total Score: {report_result.total_score})")
                return report_result
            else:
                print(f"⚠️ [Report Warning] 리포트 생성 실패 (데이터 없음)")
                return None

        except Exception as e:
            try:
                conn.rollback()
            except:
                pass
            print(f"💥 [Session Report Failed] Error: {e}")
            print(traceback.format_exc())
            return None

analysis_service = AnalysisService()
