import json
from psycopg2.extras import RealDictCursor

class ResumeRepository:
    def create(self, conn, user_id: int, resume_data: dict):
        """
        [이력서 저장]
        Pydantic 데이터를 받아서 resumes 테이블에 저장
        """
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO resumes (
                    user_id,
                    name, email,
                    job_title, target_company,
                    education, experience, projects, 
                    awards, certifications, skills,
                    introduction,
                    file_path, parsed_text
                )
                VALUES (
                    %(user_id)s,
                    %(name)s, %(email)s,
                    %(job_title)s, %(target_company)s,
                    %(education)s, %(experience)s, %(projects)s, 
                    %(awards)s, %(certifications)s, %(skills)s,
                    %(introduction)s,
                    %(file_path)s, %(parsed_text)s
                )
                RETURNING *
                """,
                {
                    "user_id": user_id,
                    "name": resume_data.get("name"),
                    "email": resume_data.get("email"),
                    "phone": resume_data.get("phone"),
                    # birth_date는 SQL에서 빠진 것 같아 제외했습니다. (필요하면 추가)
                    
                    "job_title": resume_data.get("job_title"),
                    "target_company": resume_data.get("target_company"),
                    
                    # [핵심] 리스트/딕셔너리 -> JSON 문자열 변환
                    "education": json.dumps(resume_data.get("education", []), ensure_ascii=False),
                    "experience": json.dumps(resume_data.get("experience", []), ensure_ascii=False),
                    "projects": json.dumps(resume_data.get("projects", []), ensure_ascii=False),
                    "awards": json.dumps(resume_data.get("awards", []), ensure_ascii=False),
                    "certifications": json.dumps(resume_data.get("certifications", []), ensure_ascii=False),
                    "skills": json.dumps(resume_data.get("skills", []), ensure_ascii=False),
                    
                    "introduction": resume_data.get("introduction"),
                    
                    # 직접 입력 시 파일 정보는 없음
                    "file_path": None,
                    "parsed_text": None
                }
            )
            return cur.fetchone()
        
    def get_all_by_user_id(self, conn, user_id: int):
        """특정 유저의 모든 이력서 조회 (최신순)"""
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM resumes 
                WHERE user_id = %s 
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
            return cur.fetchall()

    def get_latest_by_user_id(self, conn, user_id: int):
        """특정 유저의 가장 최근 이력서 1개 조회"""
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM resumes 
                WHERE user_id = %s 
                ORDER BY created_at DESC 
                LIMIT 1
                """,
                (user_id,)
            )
            return cur.fetchone()
    def get_by_id(self, conn, resume_id: int):
        """이력서 ID로 단건 조회"""
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM resumes WHERE resume_id = %s",
                (resume_id,)
            )
            return cur.fetchone()


resume_repo = ResumeRepository()