from sqlalchemy.orm import Session
from app.models.interview import AnswerVoiceAnalysis
from typing import Dict, Any


class VoiceRepository:

    def upsert_voice_result(
        self,
        db: Session,
        payload: Dict[str, Any]
    ) -> AnswerVoiceAnalysis:
        """
        answer_id 기준 UPSERT
        """
        answer_id = payload["answer_id"]

        obj = (
            db.query(AnswerVoiceAnalysis)
            .filter(AnswerVoiceAnalysis.answer_id == answer_id)
            .first()
        )

        if obj:
            # UPDATE
            for key, value in payload.items():
                setattr(obj, key, value)
        else:
            # INSERT
            obj = AnswerVoiceAnalysis(**payload)
            db.add(obj)

        db.commit()
        db.refresh(obj)
        return obj


voice_repo = VoiceRepository()
