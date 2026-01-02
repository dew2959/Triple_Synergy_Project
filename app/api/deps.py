from typing import Generator, Optional
import psycopg2
from psycopg2.extensions import connection

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

# 설정 파일 로드
from app.core.config import settings
# 유저 조회용 레포지토리 로드
from app.repositories.user_repo import user_repo


# =========================================================
# 1. DB 연결 (Dependency)
# =========================================================
def get_db_conn() -> Generator:
    """
    API 요청 시 DB 커넥션을 생성하고, 요청이 끝나면 닫습니다.
    """
    conn = None
    try:
        conn = psycopg2.connect(settings.DATABASE_URL)
        yield conn
    finally:
        if conn:
            conn.close()


# =========================================================
# 2. 인증/보안 (Dependency)
# =========================================================

# 토큰을 헤더에서 꺼내는 도구
# tokenUrl은 실제 로그인 API 주소와 일치해야 Swagger UI에서 로그인 테스트 가능
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    conn: connection = Depends(get_db_conn)
) -> dict:
    """
    Access Token을 검증하고, 유효하면 DB에서 해당 유저 정보를 가져옵니다.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="자격 증명을 검증할 수 없습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # 1. 토큰 디코딩
        # (비밀키와 알고리즘으로 서명 확인)
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # 'sub' 클레임에서 user_id 추출 (우리는 user_id를 넣기로 약속함)
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        # 토큰 만료, 서명 불일치 등 모든 에러 처리
        raise credentials_exception

    # 2. DB에서 유저 확인
    # (토큰은 진짜인데, 그 사이 유저가 탈퇴했을 수도 있으므로 확인)
    user = user_repo.get_by_id(conn, int(user_id))
    
    if user is None:
        raise credentials_exception
        
    return user