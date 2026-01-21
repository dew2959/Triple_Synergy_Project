from psycopg2.extensions import connection
from app.repositories.question_repo import question_repo
from app.repositories.resume_repo import resume_repo
from app.engines.resume.engine import resume_question_engine

class QuestionGenerationService:
    def generate_interview_questions(self, conn: connection, session_id: int, resume_id: int = None):
        """
        면접 세션을 위한 질문 5개를 생성하여 DB에 저장합니다.
        """
        final_questions = [] # (content, category) 튜플 리스트

        # ---------------------------------------------------
        # 1. 고정 질문 (1번, 2번)
        # ---------------------------------------------------
        q1 = question_repo.get_fixed_question_from_pool(conn, 1)
        q2 = question_repo.get_fixed_question_from_pool(conn, 2)
        
        if q1: final_questions.append((q1['content'], q1['category']))
        if q2: final_questions.append((q2['content'], q2['category']))

        # ---------------------------------------------------
        # 2. 중간 질문 (3번, 4번) - 이력서 분석 vs 랜덤
        # ---------------------------------------------------
        middle_questions = []
        is_resume_analyzed = False

        if resume_id:
            resume = resume_repo.get_by_id(conn, resume_id)
            if resume:
                # 이력서 텍스트 추출 (DB에 content 컬럼이 있다고 가정하거나, 파일에서 읽어야 함)
                # 여기서는 resume 테이블에 'content'가 없으면 job_title + company로 대체한다고 가정
                resume_text = resume.get('content') or f"직무: {resume.get('job_title')}, 목표회사: {resume.get('target_company')}"
                job_role = resume.get('job_title', 'General')

                # 엔진 호출
                generated = resume_question_engine.generate_questions(resume_text, job_role)
                
                for q_text in generated:
                    middle_questions.append((q_text, "RESUME_BASED"))
                
                if middle_questions:
                    is_resume_analyzed = True

        # 이력서가 없거나 분석에 실패해서 질문이 안 나왔으면 -> 랜덤 풀에서 가져옴
        if not is_resume_analyzed or len(middle_questions) < 2:
            needed = 2 - len(middle_questions)
            random_qs = question_repo.get_random_questions_from_pool(conn, needed)
            for rq in random_qs:
                middle_questions.append((rq['content'], rq['category']))

        final_questions.extend(middle_questions)

        # ---------------------------------------------------
        # 3. 마지막 질문 (5번)
        # ---------------------------------------------------
        q5 = question_repo.get_fixed_question_from_pool(conn, 5)
        if q5: final_questions.append((q5['content'], q5['category']))

        # ---------------------------------------------------
        # 4. DB 저장
        # ---------------------------------------------------
        saved_questions = []
        for idx, (content, category) in enumerate(final_questions, 1):
            # idx가 곧 order_index (1~5)
            question_repo.create(conn, session_id, content, category, idx)
            saved_questions.append({"order": idx, "content": content, "category": category})

        return saved_questions

question_generation_service = QuestionGenerationService()