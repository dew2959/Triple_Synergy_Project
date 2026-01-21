from psycopg2.extras import RealDictCursor

class QuestionRepository:
    def create(self, conn, session_id: int, content: str, category: str, order_index: int):
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO questions (session_id, content, category, order_index)
                VALUES (%s, %s, %s, %s)
                RETURNING question_id
                """,
                (session_id, content, category, order_index)
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

    def get_fixed_question_from_pool(self, conn, order_num: int):
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM default_question_pool WHERE fixed_order = %s LIMIT 1",
                (order_num,)
            )
            return cur.fetchone()

    # 🔴 [추가] 랜덤 질문 가져오기 (이력서 없을 때 사용)
    def get_random_questions_from_pool(self, conn, count: int):
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM default_question_pool 
                WHERE fixed_order IS NULL 
                ORDER BY RANDOM() 
                LIMIT %s
                """,
                (count,)
            )
            return cur.fetchall()
question_repo = QuestionRepository()