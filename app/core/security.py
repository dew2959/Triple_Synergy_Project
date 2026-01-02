import hashlib # ✅ 추가
from datetime import datetime, timedelta
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

# 비밀번호 해싱 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(subject: Union[str, Any]) -> str:
    """JWT 액세스 토큰 생성"""
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# ----------------------------------------------------------------
# [핵심 수정] 72바이트 제한 해결을 위한 '전처리(Pre-hashing)' 로직 추가
# ----------------------------------------------------------------

def _hash_pre_process(password: str) -> str:
    """
    비밀번호를 SHA-256으로 한 번 해싱하여 길이를 64자로 고정합니다.
    이렇게 하면 bcrypt의 72바이트 제한을 우회할 수 있습니다.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 비교"""
    # 1. 들어온 비밀번호를 먼저 전처리(SHA-256)
    pre_hashed_password = _hash_pre_process(plain_password)
    # 2. 그 다음 bcrypt로 비교
    return pwd_context.verify(pre_hashed_password, hashed_password)


def get_password_hash(password: str) -> str:
    """비밀번호 해싱"""
    # 1. 비밀번호를 전처리(SHA-256)해서 길이를 줄임
    pre_hashed_password = _hash_pre_process(password)
    # 2. bcrypt로 최종 암호화
    return pwd_context.hash(pre_hashed_password)