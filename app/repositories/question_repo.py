from psycopg2.extras import RealDictCursor

class QuestionRepository:
    def create(self, conn, question_data: dict):
        """
        질문 데이터를 DB에 저장
        """
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO questions (
                    session_id, content, category, order_index
                )
                VALUES (
                    %(session_id)s, 
                    %(content)s, 
                    %(category)s, 
                    %(order_index)s
                )
                RETURNING *
                """,
                {
                    "session_id": question_data["session_id"],
                    "content": question_data["content"],
                    # Enum은 string value로 변환해서 저장
                    "category": question_data["category"].value,
                    "order_index": question_data["order_index"]
                }
            )
            return cur.fetchone()

    def get_by_session_id(self, conn, session_id: int):
        """
        특정 세션의 모든 질문 조회 (순서대로)
        """
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM questions 
                WHERE session_id = %s 
                ORDER BY order_index ASC
                """,
                (session_id,)
            )
            return cur.fetchall()

question_repo = QuestionRepository()