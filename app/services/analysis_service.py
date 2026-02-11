import traceback
import json
import math
import os
from typing import Optional
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
from app.services.final_report_service import final_report_service
from app.utils.chart_utils import calculate_cps_flow

# Schemas
from app.schemas.visual import VisualDBPayload
from app.schemas.voice import VoiceDBPayload
from app.schemas.content import ContentDBPayload

# 1. Speed Score (CPS 기반)
def speed_score_from_cps(avg_cps: float) -> float:
    cps = float(avg_cps)
    # 튜닝 포인트
    cps_min, cps_low, cps_high, cps_max = 2.5, 4.8, 6.2, 8.0

    if not math.isfinite(cps): return 0.0
    if cps <= cps_min or cps >= cps_max: return 0.0
    if cps_low <= cps <= cps_high: return 100.0

    # 느린 구간 (선형 증가)
    if cps < cps_low:
        return (cps - cps_min) / (cps_low - cps_min) * 100.0
    
    # 빠른 구간 (선형 감소)
    return (cps_max - cps) / (cps_max - cps_high) * 100.0

# 2. Burst Penalty (급발진 감점)
def burst_penalty_from_high_speed_share(high_speed_share: Optional[float]) -> float:
    h = 0.0 if high_speed_share is None else float(high_speed_share)
    if not math.isfinite(h): h = 0.0
    h = max(0.0, min(1.0, h))

    h0, h1, max_pen = 0.05, 0.25, 20.0

    if h <= h0: return 0.0
    if h >= h1: return max_pen
    return (h - h0) / (h1 - h0) * max_pen

# -> 종합 Speed Score
def compute_speed_score(avg_cps: float, high_speed_share: Optional[float]) -> float:
    base = speed_score_from_cps(avg_cps)
    pen = burst_penalty_from_high_speed_share(high_speed_share)
    return max(0.0, min(100.0, base - pen))

# 3. Flow Score (Voiced Ratio + Silence Count)
def score_voiced(voiced_ratio: float) -> float:
    vr = float(voiced_ratio)
    if not math.isfinite(vr): return 0.0
    vr = max(0.0, min(1.0, vr))

    if vr >= 0.85: return 100.0
    if vr >= 0.78: return 60.0 + (vr - 0.78) / (0.85 - 0.78) * 40.0
    
    floor = 0.60
    if vr <= floor: return 0.0
    return (vr - floor) / (0.78 - floor) * 60.0

def score_silence_30s(silence_30s: float) -> float:
    s = float(silence_30s)
    if not math.isfinite(s):
        return 0.0
    s = max(0.0, s)

    if s <= 3: 
        return 100.0
    if s <= 9:
        # 3 -> 100, 9 -> 92  (8점만 감점)
        return 100.0 - (s - 3) / (9 - 3) * 8.0
    if s <= 18:
        # 9 -> 92, 18 -> 80 (12점 감점)
        return 92.0 - (s - 9) / (18 - 9) * 12.0
    if s <= 30:
        # 18 -> 80, 30 -> 60 (20점 감점)
        return 80.0 - (s - 18) / (30 - 18) * 20.0
    return 60.0

def compute_flow_score(voiced_ratio: float, silence_count: int) -> float:
    v = score_voiced(voiced_ratio)
    s = score_silence_30s(silence_count)
    # 가중치: Voiced 65% + Silence 35%
    return 0.65 * v + 0.35 * s

# 4. Final Score Calculation (게이트 방식)
def compute_final_voice_score(
    avg_cps: float,
    high_speed_share: Optional[float],
    voiced_ratio: float,
    silence_count: int,
) -> int:
    speed = compute_speed_score(avg_cps, high_speed_share)
    flow = compute_flow_score(voiced_ratio, silence_count)

    # Flow가 나쁘면 전체 점수를 깎음 (최대 30% 감점)
    # flow가 0점이면 0.7배, 100점이면 1.0배
    mult = 0.70 + 0.30 * (flow / 100.0)
    final = speed * mult
    
    return int(round(max(0.0, min(100.0, final))))

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
            
            visual_output = run_visual(optimized_video_path)

            if visual_output.get("error"):
                print(f"❌ [Visual Engine Error] {visual_output['error']}")
            else:
                try:
                    v_metrics = visual_output.get("metrics") or {}

                    v_score = v_metrics.get("score", 0)
                    v_feedback = v_metrics.get("feedback", "")
                    v_details = (visual_output.get("metrics") or {}).get("details", {})

                    details_str = json.dumps(v_details, default=str)

                    visual_payload = VisualDBPayload(
                        answer_id=answer_id,
                        score=v_score,
                        head_center_ratio=0.0,
                        feedback=v_feedback,
                        good_points_json=[details_str],
                        bad_points_json=[],
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
                try:
                    answer_repo.update_stt_result(conn, answer_id, stt_text)
                    conn.commit()
                    print("✅ STT 텍스트 저장 완료")
                except Exception as e:
                    try: conn.rollback()
                    except: pass
                    print(f"⚠️ [STT Save Warning] 텍스트 저장 실패: {e}")

            # 차트 데이터
            speed_flow_data = calculate_cps_flow(stt_segments)

            voice_output = run_voice(audio_path, stt_text=stt_text, stt_segments=stt_segments)

            if voice_output.get("error"):
                print(f"❌ [Voice Engine Error] {voice_output['error']}")
            else:
                try:
                    metrics = voice_output.get("metrics", {})
                    
                    # 🟢 [데이터 추출] 엔진에서 넘어온 Raw Metrics
                    avg_cps = float(metrics.get("avg_cps") or 0.0)
                    high_speed_share = metrics.get("high_speed_share") # None 가능
                    voiced_ratio = float(metrics.get("voiced_ratio") or 0.0)
                    silence_count = int(metrics.get("silence_count") or 0)
                    duration_sec = float(metrics.get("duration_sec") or 1.0)

                    # 🟢 [점수 계산] 새로운 로직 적용
                    final_score = compute_final_voice_score(
                        avg_cps=avg_cps,
                        high_speed_share=high_speed_share,
                        voiced_ratio=voiced_ratio,
                        silence_count=silence_count
                    )

                    # 🟢 [피드백 생성] 점수 기반 피드백
                    feedbacks = []
                    
                    # (1) 속도 피드백
                    if avg_cps < 2.5: feedbacks.append("말하기 속도가 너무 느립니다.")
                    elif 2.5 <= avg_cps < 4.8: feedbacks.append("말하기 속도가 다소 느린 편입니다.")
                    elif 4.8 <= avg_cps <= 6.2: pass # 적정
                    elif 6.2 < avg_cps <= 8.0: feedbacks.append("말하기 속도가 다소 빠릅니다.")
                    else: feedbacks.append("말하기 속도가 너무 빠릅니다.")

                    # (2) 급발진 피드백
                    h_share = float(high_speed_share or 0.0)
                    if h_share >= 0.05:
                        feedbacks.append("중간중간 말이 급격히 빨라지는 구간이 있습니다.")

                    # (3) 흐름(Flow) 피드백
                    vr_score = score_voiced(voiced_ratio)
                    sc_score = score_silence_30s(silence_count)
                    
                    if vr_score < 60: feedbacks.append("발화 사이의 공백이 길어 불안정해 보입니다.")
                    if sc_score < 80: feedbacks.append("말 끊김이 잦아 전달력이 떨어질 수 있습니다.")

                    feedback_text = " ".join(feedbacks) if feedbacks else "음성 전달력과 속도가 매우 훌륭합니다."

                    # DB 저장
                    voice_payload = VoiceDBPayload(
                        answer_id=answer_id,
                        score=final_score,
                        feedback=feedback_text,
                        
                        # Raw Data 저장
                        avg_wpm=int(metrics.get("avg_wpm") or 0),
                        max_wpm=int(metrics.get("max_wpm") or 0),
                        silence_count=silence_count,
                        avg_silence_length=0.0,
                        silence_timeline_json=[],
                        duration_sec=duration_sec,
                        avg_cps=avg_cps,
                        avg_cpm=float(metrics.get("avg_cpm") or 0.0),
                        avg_pitch=float(metrics.get("avg_pitch") or 0.0),
                        max_pitch=float(metrics.get("max_pitch") or 0.0),
                        pitch_std=float(metrics.get("pitch_std") or 0.0),
                        voiced_ratio=voiced_ratio,
                        burst_ratio=float(metrics.get("burst_ratio") or 0.0),
                        high_speed_share=float(metrics.get("high_speed_share") or 0.0),
                        cv_cps=float(metrics.get("cv_cps") or 0.0),
                        
                        good_points_json=[],
                        bad_points_json=feedbacks,
                        charts_json={"speed_flow": speed_flow_data}
                    )
                    
                    a_data = voice_payload.model_dump()
                    a_data["charts_json"] = {'speed_flow': speed_flow_data}
                    a_data["silence_timeline_json"] = json.dumps(a_data["silence_timeline_json"])
                    a_data["good_points_json"] = json.dumps(a_data["good_points_json"])
                    a_data["bad_points_json"] = json.dumps(a_data["bad_points_json"])

                    voice_repo.upsert_voice_result(conn, a_data)
                    conn.commit()
                    print(f"✅ 음성 분석 저장 완료 (점수: {final_score})")

                except Exception as e:
                    try: conn.rollback()
                    except: pass
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
