# app/services/analysis_service.py
import traceback
from psycopg2.extensions import connection  # Session 대신 사용
from app.utils.media_utils import MediaUtils

# Repositories (ORM 제거 버전)
from app.repositories.answer_repo import answer_repo
from app.repositories.visual_repo import visual_repo
from app.repositories.voice_repo import voice_repo
from app.repositories.content_repo import content_repo

# Schemas
from app.schemas.visual import VisualResult, VisualDBPayload, VisualMetrics
from app.schemas.common import AnalysisFeedback, TimeEvent

class AnalysisService:
    def run_full_analysis(self, conn: connection, answer_id: int, file_path: str):
        print(f"🎬 [Analysis Start] Answer ID: {answer_id}")
        
        # 1. 답변 조회 (이제 dict를 반환함)
        answer = answer_repo.get_by_id(conn, answer_id)
        if not answer:
            print("❌ 답변을 찾을 수 없습니다.")
            return

        # 2. 상태 변경 (ORM이 아니므로 명시적 update 함수 호출 필요)
        print(f"🔄 상태 변경: PENDING -> PROCESSING")
        answer_repo.update_analysis_status(conn, answer_id, "PROCESSING")

        try:
            # 0. 오디오 추출
            print("🔊 오디오 추출 중...")
            audio_path = MediaUtils.extract_audio(file_path)

            # =================================================
            # 1. 비주얼 분석
            # =================================================
            print("👁️ 비주얼 분석 시작...")
            # (가짜 데이터 생성 예시)
            visual_metrics = VisualMetrics(
                score=85,
                head_center_ratio=0.8,
                events=[]
            )
            visual_result = VisualResult(
                module="visual",
                answer_id=answer_id,
                metrics=visual_metrics,
                feedback=AnalysisFeedback(summary="좋습니다")
            )

            # [핵심 변경] Repository가 dict를 원하므로 model_dump() 사용
            visual_payload = VisualDBPayload(
                answer_id=visual_result.answer_id,
                score=visual_result.metrics.score,
                head_center_ratio=visual_result.metrics.head_center_ratio,
                feedback=visual_result.feedback.summary,
                good_points_json=visual_result.feedback.good_points,
                bad_points_json=visual_result.feedback.bad_points
            )
            
            # upsert_visual_result는 이제 (conn, dict)를 받음
            visual_repo.upsert_visual_result(conn, visual_payload.model_dump())
            print("✅ 비주얼 분석 저장 완료")


            # =================================================
            # 2. 음성 분석 & 3. 내용 분석 (위와 동일한 패턴)
            # =================================================
            # ... (Voice, Content도 model_dump() 해서 upsert 호출) ...


            # 4. 최종 완료 처리
            answer_repo.update_analysis_status(conn, answer_id, "DONE")
            print(f"🎉 [Analysis Done] Answer ID: {answer_id}")

        except Exception as e:
            print(f"💥 [Analysis Failed] Error: {e}")
            traceback.print_exc()
            # 실패 상태 업데이트
            answer_repo.update_analysis_status(conn, answer_id, "FAILED")

analysis_service = AnalysisService()