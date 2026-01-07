"""
이력서 관련 스키마
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class EducationItem(BaseModel):
    """학력 항목"""
    school: str = Field(..., description="학교명")
    major: str = Field(..., description="전공")
    degree: str = Field(..., description="학위 (예: 학사, 석사, 박사)")
    start_date: str = Field(..., description="입학일")
    end_date: Optional[str] = Field(None, description="졸업일")
    status: str = Field(..., description="상태 (예: 졸업, 재학, 휴학)")


class ExperienceItem(BaseModel):
    """경력 항목"""
    company: str = Field(..., description="회사명")
    position: str = Field(..., description="직책")
    department: Optional[str] = Field(None, description="부서")
    start_date: str = Field(..., description="입사일")
    end_date: Optional[str] = Field(None, description="퇴사일")
    description: str = Field(..., description="업무 내용")
    achievements: Optional[str] = Field(None, description="주요 성과")


class ProjectItem(BaseModel):
    """프로젝트 경험 항목"""
    name: str = Field(..., description="프로젝트명")
    role: str = Field(..., description="역할")
    start_date: str = Field(..., description="시작일")
    end_date: Optional[str] = Field(None, description="종료일")
    description: str = Field(..., description="프로젝트 설명")
    technologies: List[str] = Field(default_factory=list, description="사용 기술")
    achievements: Optional[str] = Field(None, description="성과")


class AwardItem(BaseModel):
    """수상 경력 항목"""
    name: str = Field(..., description="수상명")
    organization: str = Field(..., description="수여 기관")
    date: str = Field(..., description="수상일")
    description: Optional[str] = Field(None, description="수상 내용")


class CertificationItem(BaseModel):
    """자격증/교육 항목"""
    name: str = Field(..., description="자격증/교육명")
    organization: str = Field(..., description="발급 기관")
    date: str = Field(..., description="취득일")
    valid_until: Optional[str] = Field(None, description="만료일")
    description: Optional[str] = Field(None, description="설명")


class ResumeCreate(BaseModel):
    """이력서 생성 스키마"""
    name: str = Field(..., description="이름")
    email: str = Field(..., description="이메일")
    phone: Optional[str] = Field(None, description="연락처")
    birth_date: Optional[str] = Field(None, description="생년월일")
    education: List[EducationItem] = Field(default_factory=list, description="학력")
    experience: List[ExperienceItem] = Field(default_factory=list, description="경력")
    projects: List[ProjectItem] = Field(default_factory=list, description="프로젝트 경험")
    awards: List[AwardItem] = Field(default_factory=list, description="수상 경력")
    certifications: List[CertificationItem] = Field(default_factory=list, description="자격증/교육")
    skills: List[str] = Field(default_factory=list, description="기술 스택")
    introduction: Optional[str] = Field(None, description="자기소개")


class ResumeUpdate(BaseModel):
    """이력서 수정 스키마"""
    name: Optional[str] = Field(None, description="이름")
    email: Optional[str] = Field(None, description="이메일")
    phone: Optional[str] = Field(None, description="연락처")
    birth_date: Optional[str] = Field(None, description="생년월일")
    education: Optional[List[EducationItem]] = Field(None, description="학력")
    experience: Optional[List[ExperienceItem]] = Field(None, description="경력")
    projects: Optional[List[ProjectItem]] = Field(None, description="프로젝트 경험")
    awards: Optional[List[AwardItem]] = Field(None, description="수상 경력")
    certifications: Optional[List[CertificationItem]] = Field(None, description="자격증/교육")
    skills: Optional[List[str]] = Field(None, description="기술 스택")
    introduction: Optional[str] = Field(None, description="자기소개")


class ResumeResponse(BaseModel):
    """이력서 응답 스키마"""
    id: int
    user_id: int
    name: str
    email: str
    phone: Optional[str]
    birth_date: Optional[str]
    education: List[EducationItem]
    experience: List[ExperienceItem]
    projects: List[ProjectItem]
    awards: List[AwardItem]
    certifications: List[CertificationItem]
    skills: List[str]
    introduction: Optional[str]
    created_at: datetime
    updated_at: datetime


class ResumeUploadResponse(BaseModel):
    resume_id: int
    parsed_text: Optional[str]


class ResumeView(BaseModel):
    resume_id: int
    file_path: str
    created_at: datetime
