from sqlalchemy.orm import Session
from app.models.interview import FinalReport
from typing import Dict, Any


class FinalReportRepository:

    def upsert_final_report(
        self,
        db: Session,
        payload: Dict[str, Any]
    ) -> FinalReport:
        """
        session_id 기준 최종 리포트 UPSERT
        """
        session_id = payload["session_id"]

        obj = (
            db.query(FinalReport)
            .filter(FinalReport.session_id == session_id)
            .first()
        )

        if obj:
            # UPDATE
            for key, value in payload.items():
                setattr(obj, key, value)
        else:
            # INSERT
            obj = FinalReport(**payload)
            db.add(obj)

        db.commit()
        db.refresh(obj)
        return obj


final_report_repo = FinalReportRepository()
