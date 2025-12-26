from sqlalchemy.orm import Session
from app.models.answer import Answer

class AnswerRepository:
    # question_id 인자 추가!
    def create(self, db: Session, question_id: int, video_path: str) -> Answer:
        db_obj = Answer(
            question_id=question_id, # [핵심] DB에 질문 ID 저장
            video_path=video_path,
            stt_text="분석 대기 중..."
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

answer_repo = AnswerRepository()