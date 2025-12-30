from sqlalchemy.orm import Session
# 아까 수정한 '올바른 모델 경로' (models.answer -> models.interview)
from app.models.interview import Answer 

class AnswerRepository:
    # 1. 답변 생성 (기존에 있던 것)
    def create(self, db: Session, question_id: int, video_path: str) -> Answer:
        db_obj = Answer(
            question_id=question_id, 
            video_path=video_path,
            stt_text="분석 대기 중..."
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # 2. 답변 조회 (★ 이 함수가 없어서 에러가 났습니다! 추가해주세요)
    def get_by_id(self, db: Session, answer_id: int) -> Answer:
        # DB에서 answer_id가 일치하는 첫 번째 데이터를 가져옵니다.
        return db.query(Answer).filter(Answer.answer_id == answer_id).first()

# 인스턴스 생성
answer_repo = AnswerRepository()