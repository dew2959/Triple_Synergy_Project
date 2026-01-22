from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
import psycopg2
from app.core.config import settings

from app.api.deps import get_db_conn, get_current_user
from app.repositories.answer_repo import answer_repo
from app.repositories.session_repo import session_repo
from app.services.analysis_service import analysis_service

router = APIRouter()

def _run_session_analysis_pipeline(session_id: int, answers: list):
    """
    [백그라운드 파이프라인]
    1. 세션 내 모든 답변 순차 분석
    2. 모든 분석 완료 후 종합 리포트 생성
    3. 세션 상태 완료 처리
    """
    conn = None
    try:
        # DB 직접 연결 (백그라운드 스레드용)
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            dbname=settings.DB_NAME
        )
        
        print(f"🚀 [Pipeline Start] Session {session_id} 분석 파이프라인 시작")

        # -------------------------------------------------------
        # Step 1: 개별 답변 분석 (순차 실행)
        # -------------------------------------------------------
        for ans in answers:
            if ans['video_path']:
                # 기존 run_full_analysis -> run_answer_analysis로 변경
                analysis_service.run_answer_analysis(conn, ans['answer_id'], ans['video_path'])
                
                # 하나 끝날 때마다 커밋 (중간에 실패해도 앞부분은 저장되도록)
                conn.commit()

        # -------------------------------------------------------
        # Step 2: 종합 리포트 생성
        # -------------------------------------------------------
        print(f"📊 [Pipeline Step 2] 종합 리포트 생성 중...")
        analysis_service.generate_session_report(conn, session_id)
        conn.commit()

        # -------------------------------------------------------
        # Step 3: 세션 상태 완료 (COMPLETED)
        # -------------------------------------------------------
        session_repo.update_status(conn, session_id, "COMPLETED")
        conn.commit()
        
        print(f"✅ [Pipeline Finish] Session {session_id} 모든 작업 완료")

    except Exception as e:
        print(f"💥 [Pipeline Error] Session {session_id}: {e}")
        if conn: conn.rollback()
        # 에러 발생 시 세션 상태를 뭔가 표시해주고 싶다면 여기서 처리 (예: FAILED)
    finally:
        if conn: conn.close()


@router.post("/session/{session_id}")
def analyze_session_answers(
    session_id: int,
    background_tasks: BackgroundTasks,
    conn=Depends(get_db_conn),
    current_user=Depends(get_current_user)
):
    """
    [세션 일괄 분석 요청]
    해당 세션의 모든 답변을 분석하고, 마지막에 종합 리포트를 생성합니다.
    """
    # 1. 답변 목록 조회
    answers = answer_repo.get_all_by_session_id(conn, session_id)
    if not answers:
        raise HTTPException(status_code=400, detail="분석할 답변 데이터가 없습니다.")

    # 2. 세션 상태 변경 (ANALYZING)
    session_repo.update_status(conn, session_id, "ANALYZING")
    conn.commit()

    # 3. 백그라운드 파이프라인 시작 (단 하나의 태스크만 등록)
    # 리스트(answers)를 통째로 넘겨서 스레드 안에서 for문을 돌립니다.
    background_tasks.add_task(_run_session_analysis_pipeline, session_id, answers)
            
    return {
        "message": f"Session {session_id} analysis pipeline started.",
        "target_answers_count": len(answers),
        "status": "ANALYZING"
    }