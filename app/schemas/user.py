from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# [회원가입/로그인 요청] (Input)
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserProfile(BaseModel):
    user_id: int
    email: str
    name: Optional[str]
    created_at: datetime

# [사용자 정보 응답] (Output) - 비밀번호 절대 제외!
class UserResponse(BaseModel):
    user_id: int
    email: EmailStr
    name: str
    created_at: datetime

    class Config:
        from_attributes = True