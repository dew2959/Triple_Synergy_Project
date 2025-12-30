from sqlalchemy.orm import Session
from app.models.interview import Answer
from typing import Optional


class AnswerRepository:

    # 1️⃣ 답변 생성
    def create(
        self,
        db: Session,
        question_id: int,
        video_path: str,
        audio_path: Optional[str] = None
    ) -> Answer:
        """
        질문에 대한 답변 row 생성
        """
        db_obj = Answer(
            question_id=question_id,
            video_path=video_path,
            audio_path=audio_path,
            stt_text=None,
            analysis_status="PENDING"
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


    # 2️⃣ 답변 조회 (분석 파이프라인 기준점)
    def get_by_id(self, db: Session, answer_id: int) -> Optional[Answer]:
        """
        answer_id로 Answer 조회
        """
        return (
            db.query(Answer)
            .filter(Answer.answer_id == answer_id)
            .first()
        )


    # 3️⃣ 분석 상태 업데이트 (매우 중요 ⭐)
    def update_analysis_status(
        self,
        db: Session,
        answer_id: int,
        status: str
    ) -> None:
        """
        PENDING → PROCESSING → DONE / FAILED
        """
        db.query(Answer)\
          .filter(Answer.answer_id == answer_id)\
          .update({"analysis_status": status})

        db.commit()


    # 4️⃣ STT 결과 저장 (Whisper 이후)
    def update_stt_result(
        self,
        db: Session,
        answer_id: int,
        stt_text: str
    ) -> None:
        """
        Whisper STT 결과 저장
        """
        db.query(Answer)\
          .filter(Answer.answer_id == answer_id)\
          .update({"stt_text": stt_text})

        db.commit()


# 싱글톤처럼 사용
answer_repo = AnswerRepository()
