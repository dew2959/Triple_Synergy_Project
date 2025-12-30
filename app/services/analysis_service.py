# app/services/analysis_service.py
import traceback
from sqlalchemy.orm import Session
from app.models.enums import AnswerAnalysisStatus

# Repositories
from app.repositories.answer_repo import answer_repo
from app.schemas.visual import VisualResult, VisualMetrics, VisualDBPayload
from app.schemas.common import AnalysisFeedback, TimeEvent
#from app.repositories.visual_repo import visual_repo
# from app.repositories.voice_repo import voice_repo (나중에 추가)
# from app.repositories.content_repo import content_repo (나중에 추가)

# Engines (AI 모듈) - 지금은 가짜(Mock)로라도 연결해둬야 함
# from app.engines.visual.engine import VisualAnalyzer

class MockVisualRepo:
    def save_result(self, db: Session, result):
        print(f"\n[MockRepo] 🛠️ 가짜 저장소가 데이터를 받았습니다!")
        print(f"   - 받은 데이터 점수: {result.score}")
        
        # ✅ .summary를 지우고 그냥 출력하세요. (이제 feedback은 그냥 글자니까요)
        print(f"   - 받은 피드백: {result.feedback}") 
        
        return True

# 가짜 객체 생성 (이 변수 이름을 그대로 씀)
visual_repo = MockVisualRepo()


class AnalysisService:
    def __init__(self):
        # 엔진들 초기화 (비용이 큰 작업이면 여기서 함)
        pass

    def run_full_analysis(self, db: Session, answer_id: int, file_path: str):
        """
        [지휘자 역할]
        1. 상태 변경 (PENDING -> PROCESSING)
        2. 비주얼, 음성, 내용 분석 순차 실행
        3. 결과 저장
        4. 상태 변경 (PROCESSING -> DONE or FAILED)
        """
        print(f"🎬 [Analysis Start] Answer ID: {answer_id}")
        
        # 1. 답변 조회 및 상태 변경 (PROCESSING)
        answer = answer_repo.get_by_id(db, answer_id)
        if not answer:
            print("❌ 답변을 찾을 수 없습니다.")
            return

        answer.analysis_status = AnswerAnalysisStatus.PROCESSING
        db.commit() # 상태 저장

        try:
            print("👁️ 비주얼 분석 시작...")
            
            # 1. [AI 분석] Engine이 결과를 뱉음 (VisualResult 구조)
            # (가짜 데이터 생성 예시)
            visual_metrics = VisualMetrics(
                score=88,
                head_center_ratio=0.92,
                events=[
                    TimeEvent(type="eye_contact", start=0.0, end=5.0, duration=5.0),
                    TimeEvent(type="look_away", start=5.1, end=6.0, duration=0.9)
                ]
            )
            
            visual_result = VisualResult(
                module="visual",
                answer_id=answer_id,
                metrics=visual_metrics,
                feedback=AnalysisFeedback(
                    summary="시선 처리가 안정적입니다.",
                    good_points=["정면 응시"],
                    bad_points=[]
                )
            )

            # 2. [변환] Result(객체) -> Payload(DB용 Flat 데이터)
            # Service가 이 '번역' 역할을 담당합니다.
            visual_payload = VisualDBPayload(
                answer_id=visual_result.answer_id,
                score=visual_result.metrics.score,
                head_center_ratio=visual_result.metrics.head_center_ratio,
                
                # [핵심] 리스트 내부의 객체(TimeEvent)를 dict로 변환 (model_dump 사용)
                events_json=[event.model_dump() for event in visual_result.metrics.events],
                
                feedback=visual_result.feedback.summary,
                good_points_json=visual_result.feedback.good_points,
                bad_points_json=visual_result.feedback.bad_points
            )

            # 3. [저장] Repository에는 Payload를 전달
            visual_repo.save_result(db, visual_payload)
            print("✅ 비주얼 분석 저장 완료")


            # =================================================
            # 2-2. 음성 분석 (Voice Engine) - 나중에 주석 해제
            # =================================================
            # print("🎤 음성 분석 시작...")
            # voice_result = voice_engine.analyze(file_path)
            # voice_repo.save_result(db, voice_result)


            # =================================================
            # 2-3. 내용 분석 (Content Engine) - 나중에 주석 해제
            # =================================================
            # print("🧠 내용 분석 시작...")
            # stt_text = stt_engine.transcribe(file_path) # 1. STT
            # answer.stt_text = stt_text # 2. STT 결과 저장
            # content_result = llm_engine.analyze(stt_text) # 3. LLM
            # content_repo.save_result(db, content_result)


            # =================================================
            # 3. 최종 완료 처리
            # =================================================
            answer.analysis_status = AnswerAnalysisStatus.DONE
            db.commit()
            print(f"🎉 [Analysis Done] Answer ID: {answer_id}")

        except Exception as e:
            # =================================================
            # 4. 실패 시 처리 (에러 핸들링 & 상태 업데이트)
            # =================================================
            print(f"💥 [Analysis Failed] Error: {e}")
            traceback.print_exc() # 에러 위치 상세 출력
            
            # 상태를 '실패'로 변경 (롤백하지 않고 실패 상태로 둠)
            answer.analysis_status = AnswerAnalysisStatus.FAILED # (Enum에 FAILED가 없다면 추가 필요)
            db.commit()

# 인스턴스 생성 (싱글톤처럼 사용)
analysis_service = AnalysisService()



if __name__ == "__main__":
    from app.core.db import SessionLocal
    
    # 1. DB 연결
    db = SessionLocal()
    
    # 2. 테스트할 답변 ID 설정 (아까 DB에 1번이나 5번 같은게 있어야 함)
    TEST_ANSWER_ID = 5
    TEST_FILE_PATH = "uploads\1. self_introduction_euiju(knee)_A.mp4" # 실제 파일 없어도 됨 (분석 로직만 테스트하니까)

    print("🚀 테스트를 시작합니다...")
    
    try:
        # 서비스 호출!
        analysis_service.run_full_analysis(db, TEST_ANSWER_ID, TEST_FILE_PATH)
    finally:
        db.close()
        print("🏁 테스트 종료")