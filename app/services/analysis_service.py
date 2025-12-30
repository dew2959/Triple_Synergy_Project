# app/services/analysis_service.py
import traceback
from sqlalchemy.orm import Session
from app.models.enums import AnswerAnalysisStatus

# Repositories
from app.repositories.answer_repo import answer_repo
#from app.repositories.visual_repo import visual_repo
# from app.repositories.voice_repo import voice_repo (나중에 추가)
# from app.repositories.content_repo import content_repo (나중에 추가)

# Engines (AI 모듈) - 지금은 가짜(Mock)로라도 연결해둬야 함
# from app.engines.visual.engine import VisualAnalyzer

class MockVisualRepo:
    def save_result(self, db: Session, result):
        print(f"🛠️ [MOCK] Visual Repo가 작동하는 '척' 합니다.")
        print(f"   - 받은 데이터 점수: {result.score}")
        print(f"   - 받은 피드백: {result.feedback.summary}")
        # 실제 DB 저장은 안 하고, 그냥 성공했다고 침
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
            # =================================================
            # 2-1. 비주얼 분석 (Visual Engine)
            # =================================================
            print("👁️ 비주얼 분석 시작...")
            # analyzer = VisualAnalyzer()          # 엔진 생성
            # result_dict = analyzer.analyze(file_path) # 분석 실행
            
            # [테스트용 가짜 데이터] (엔진 완성 전까지 사용)
            from app.schemas.visual import VisualResult
            from app.schemas.common import AnalysisFeedback
            
            # 엔진에서 나왔다고 가정한 데이터
            dummy_result = VisualResult(
                module="visual",
                answer_id=answer_id,
                score=85,
                head_center_ratio=0.9,
                feedback=AnalysisFeedback(summary="시선 처리가 훌륭합니다.")
            )
            
            # DB 저장 (Repository 이용)
            visual_repo.save_result(db, dummy_result)
            print("✅ 비주얼 분석 완료")


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