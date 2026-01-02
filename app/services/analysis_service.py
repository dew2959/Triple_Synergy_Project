import traceback
from psycopg2.extensions import connection  
from app.utils.media_utils import MediaUtils

from app.engines.visual.engine import run_visual

# Repositories 
from app.repositories.answer_repo import answer_repo
from app.repositories.visual_repo import visual_repo
from app.repositories.voice_repo import voice_repo
from app.repositories.content_repo import content_repo

# Schemas
from app.schemas.visual import VisualDBPayload

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
            print(f"👁️ 비주얼 분석 시작 (파일: {file_path})...")
            
            # [Step 1] 엔진 실행
            visual_output = run_visual(file_path)
            if visual_output.get("error"):
                error_info = visual_output["error"]
                print(f"❌ 비주얼 분석 엔진 에러: {error_info}")
                # 에러가 나도 멈출지, 그냥 넘어갈지 결정 (일단 로그 찍고 넘어감)
            
            else:
                # [Step 3] 결과 해석 (Metrics -> Score/Feedback 변환)
                # 엔진은 '수치'만 주므로, 서비스가 '평가'를 내려야 합니다.
                metrics = visual_output.get("metrics", {})
                
                # 값 가져오기 (없으면 기본값)
                face_ratio = metrics.get("face_presence_ratio", 0.0)
                center_ratio = metrics.get("head_center_ratio", 0.0)
                movement_std = metrics.get("head_movement_std", 0.0)
                
                # --- 간단한 점수 계산 로직 (임시) ---
                # 기본 100점에서 감점 방식
                score = 100
                feedbacks = []
                
                if face_ratio < 0.8:
                    score -= 20
                    feedbacks.append("화면에서 얼굴이 자주 사라집니다. 카메라를 정면으로 응시해주세요.")
                
                if center_ratio < 0.6:
                    score -= 10
                    feedbacks.append("고개가 중앙에서 많이 벗어났습니다. 자세를 바르게 해주세요.")
                    
                if movement_std > 0.5: # 기준값은 테스트하며 조정 필요
                    score -= 10
                    feedbacks.append("고개 움직임이 많아 산만해 보일 수 있습니다.")
                
                if score == 100:
                    feedbacks.append("시선 처리와 자세가 매우 훌륭합니다!")

                final_feedback = " ".join(feedbacks)
                final_score = max(0, score) # 음수 방지

                # [Step 4] DB Payload 생성
                visual_payload = VisualDBPayload(
                    answer_id=answer_id,
                    score=final_score,
                    head_center_ratio=center_ratio, # DB 컬럼에 있는 것만 넣음
                    feedback=final_feedback,
                    good_points_json=[], # 엔진에서 아직 안 줌
                    bad_points_json=[],  # 엔진에서 아직 안 줌
                    # events_json=visual_output.get("events", []) # DB에 컬럼 있으면 추가
                )
                
                # [Step 5] DB 저장
                visual_repo.upsert_visual_result(conn, visual_payload.model_dump())
                print(f"✅ 비주얼 분석 저장 완료 (점수: {final_score})")


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




# 파일 상단에 import 추가 필요 (이미 있다면 패스)
import psycopg2
from app.core.config import settings
# 만약 run_full_analysis가 같은 파일 내에 있는 함수라면:
# import 할 필요 없이 바로 호출 가능합니다.

if __name__ == "__main__":
    conn = None
    try:
        # 1. DB 직접 연결 (Generator 대신 직접 connect 사용)
        # Settings에 정의된 정보로 직접 연결합니다.
        print("DB 연결 시도...")
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            dbname=settings.DB_NAME
        )
        print("DB 연결 성공")

        # 2. 테스트 데이터 설정
        TEST_FILE_PATH = "uploads/1. self_introduction_euiju(knee)_A.mp4" 
        TEST_ANSWER_ID = 5 

        # 3. 분석 로직 실행
        # (이 코드가 analysis_service.py 안에 있다면 'analysis_service.' 접두어 없이 함수명만 쓰세요)
        # 만약 클래스 메서드라면 클래스 인스턴스화가 필요할 수 있습니다.
        analysis_service.run_full_analysis(conn, TEST_ANSWER_ID, TEST_FILE_PATH)
        
        # 4. 트랜잭션 확정
        conn.commit()
        print("분석 완료 및 커밋 성공")

    except Exception as e:
        # 에러 발생 시 롤백
        if conn:
            conn.rollback()
        print(f"테스트 실패: {e}")
        
    finally:
        # 5. 연결 종료
        if conn:
            conn.close()
            print("DB 연결 종료")