from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# 1. 공통 속성
class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None

# 2. 회원가입 요청
class UserCreate(UserBase):
    password: str

# 3. [수정] 로그인 요청 
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# 4. 응답용
class UserResponse(UserBase):
    user_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True