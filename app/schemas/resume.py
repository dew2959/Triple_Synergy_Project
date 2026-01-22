from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# ==========================================
# 하위 아이템 모델 (JSON 내부 구조)
# ==========================================
class EducationItem(BaseModel):
    school: str
    major: str
    degree: str
    start_date: str
    end_date: Optional[str] = None
    status: str

class ExperienceItem(BaseModel):
    company: str
    position: str
    start_date: str
    end_date: Optional[str] = None
    description: str

class ProjectItem(BaseModel):
    name: str
    role: str
    start_date: str
    end_date: Optional[str] = None
    description: str

class AwardItem(BaseModel):
    name: str
    date: str
    organization: str

class CertificationItem(BaseModel):
    name: str
    date: str
    organization: str

# ==========================================
# 메인 스키마
# ==========================================
class ResumeCreate(BaseModel):
    """
    [이력서 생성 요청]
    프론트엔드에서 입력받는 데이터 구조
    """
    # 기본 정보
    name: str = Field(..., description="이름")
    email: str = Field(..., description="이메일")
    
    # 지원 정보 (SQL: job_title NOT NULL)
    job_title: str = Field(..., description="지원 직무 (필수)")
    target_company: Optional[str] = Field(None, description="지원 회사")

    # 상세 정보 (JSON 배열들)
    education: List[EducationItem] = []
    experience: List[ExperienceItem] = []
    projects: List[ProjectItem] = []
    awards: List[AwardItem] = []
    certifications: List[CertificationItem] = []
    skills: List[str] = []
    
    introduction: Optional[str] = None


class ResumeResponse(ResumeCreate):
    """
    [이력서 응답]
    DB 저장 후 반환되는 데이터 구조
    """
    resume_id: int
    user_id: int
    
    # 파일 관련 (직접 입력 시 NULL)
    file_path: Optional[str] = None
    parsed_text: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ResumeQuestionsOut(BaseModel):
    """
    [LLM 출력] 이력서 기반 생성 질문
    """
    questions: List[str] = Field(
        description="이력서를 보고 생성한 날카로운 면접 질문 2개",
        min_items=2,
        max_items=2
    )