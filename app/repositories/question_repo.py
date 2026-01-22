from psycopg2.extras import RealDictCursor
import random

class QuestionRepository:
    def create(self, conn, question_data: dict):
        """
        questions 테이블에 질문 저장
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
                    "category": str(question_data["category"]),
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
        
    # ===============================================
    # default_question_pool에서 질문 가져오기
    # ===============================================
    def get_by_pool_category(self, conn, category: str, order_by: str = None):
        """
        기본 질문 풀에서 카테고리별 질문 조회
        order_by = 'fixed_order'이면 고정 순서대로 정렬
        """
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if order_by == "fixed_order":
                cur.execute(
                    """
                    SELECT * FROM default_question_pool 
                    WHERE category = %s
                    ORDER BY fixed_order ASC
                    """,
                    (category,)
                )
            else:
                cur.execute(
                    """
                    SELECT * FROM default_question_pool 
                    WHERE category = %s
                    """,
                    (category,)
                )
            return cur.fetchall()

    def get_random_body_questions(self, conn, count: int = 3):
        """
        RANDOM_BODY 질문 중 count개 랜덤 선택
        """
        all_body = self.get_by_pool_category(conn, "RANDOM_BODY")
        return random.sample(all_body, min(count, len(all_body)))


question_repo = QuestionRepository()