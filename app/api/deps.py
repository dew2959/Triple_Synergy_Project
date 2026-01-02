from typing import Generator
from psycopg2.extensions import connection

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

from app.core.config import settings
from app.repositories.user_repo import user_repo

# [수정됨] db.py에서 함수 가져오기 (이제 여기서 직접 connect 안 함)
from app.core.db import get_connection, release_connection


# =========================================================
# 1. DB 연결 (Dependency) - Pool 사용
# =========================================================
def get_db_conn() -> Generator:
    """
    API 요청 시 Pool에서 연결을 빌려오고(yield), 
    요청이 끝나면 다시 반납(putconn)합니다.
    """
    conn = None
    try:
        conn = get_connection() # 1. 빌린다 (db.py 함수 사용)
        yield conn              # 2. 쓴다
    finally:
        if conn:
            release_connection(conn) # 3. 반납한다


# =========================================================
# 2. 인증/보안 (Dependency) - 기존 유지
# =========================================================
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    conn: connection = Depends(get_db_conn)
) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="자격 증명을 검증할 수 없습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = user_repo.get_by_id(conn, int(user_id))
    
    if user is None:
        raise credentials_exception
        
    return user