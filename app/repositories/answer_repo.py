from typing import Optional
from psycopg2.extensions import connection
from .base import BaseRepository


class AnswerRepository(BaseRepository):

    # 1️⃣ 답변 생성
    def create(
        self,
        conn: connection,
        question_id: int,
        video_path: str,
        audio_path: Optional[str] = None
    ) -> dict:
        sql = """
        INSERT INTO answers (
            question_id,
            video_path,
            audio_path,
            stt_text,
            analysis_status
        )
        VALUES (
            %(question_id)s,
            %(video_path)s,
            %(audio_path)s,
            NULL,
            'PENDING'
        )
        RETURNING *
        """
        return self.fetch_one(conn, sql, {
            "question_id": question_id,
            "video_path": video_path,
            "audio_path": audio_path
        })

    # 2️⃣ 답변 조회
    def get_by_id(
        self,
        conn: connection,
        answer_id: int
    ) -> Optional[dict]:
        sql = """
        SELECT *
        FROM answers
        WHERE answer_id = %(answer_id)s
        """
        return self.fetch_one(conn, sql, {"answer_id": answer_id})

    # 3️⃣ 분석 상태 업데이트
    def update_analysis_status(
        self,
        conn: connection,
        answer_id: int,
        status: str
    ) -> None:
        sql = """
        UPDATE answers
        SET analysis_status = %(status)s
        WHERE answer_id = %(answer_id)s
        """
        self.execute(conn, sql, {
            "answer_id": answer_id,
            "status": status
        })

    # 4️⃣ STT 결과 저장
    def update_stt_result(
        self,
        conn: connection,
        answer_id: int,
        stt_text: str
    ) -> None:
        sql = """
        UPDATE answers
        SET stt_text = %(stt_text)s
        WHERE answer_id = %(answer_id)s
        """
        self.execute(conn, sql, {
            "answer_id": answer_id,
            "stt_text": stt_text
        })


answer_repo = AnswerRepository()
