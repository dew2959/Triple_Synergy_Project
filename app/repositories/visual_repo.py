from sqlalchemy.orm import Session
from app.models.interview import AnswerVisualAnalysis
from typing import Dict, Any


class VisualRepository:

    def upsert_visual_result(
        self,
        db: Session,
        payload: Dict[str, Any]
    ) -> AnswerVisualAnalysis:
        """
        answer_id 기준 UPSERT
        """
        answer_id = payload["answer_id"]

        obj = (
            db.query(AnswerVisualAnalysis)
            .filter(AnswerVisualAnalysis.answer_id == answer_id)
            .first()
        )

        if obj:
            # UPDATE
            for key, value in payload.items():
                setattr(obj, key, value)
        else:
            # INSERT
            obj = AnswerVisualAnalysis(**payload)
            db.add(obj)

        db.commit()
        db.refresh(obj)
        return obj


visual_repo = VisualRepository()
