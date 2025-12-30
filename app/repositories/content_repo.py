from sqlalchemy.orm import Session
from app.models.interview import AnswerContentAnalysis
from typing import Dict, Any


class ContentRepository:

    def upsert_content_result(
        self,
        db: Session,
        payload: Dict[str, Any]
    ) -> AnswerContentAnalysis:
        """
        answer_id 기준 LLM 분석 결과 UPSERT
        """
        answer_id = payload["answer_id"]

        obj = (
            db.query(AnswerContentAnalysis)
            .filter(AnswerContentAnalysis.answer_id == answer_id)
            .first()
        )

        if obj:
            # UPDATE
            for key, value in payload.items():
                setattr(obj, key, value)
        else:
            # INSERT
            obj = AnswerContentAnalysis(**payload)
            db.add(obj)

        db.commit()
        db.refresh(obj)
        return obj


content_repo = ContentRepository()
