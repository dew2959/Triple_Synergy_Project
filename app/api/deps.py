from typing import Generator
from psycopg2.extensions import connection
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

from app.core.config import settings
from app.repositories.user_repo import user_repo

# [수정] 방금 만든 Context Manager 하나만 가져옵니다.
from app.core.db import get_db_connection

# =========================================================
# 1. DB 연결 (Dependency) - Context Manager 재사용
# =========================================================
def get_db_conn() -> Generator:
    """
    FastAPI 의존성 주입용 함수
    get_db_connection()이라는 Context Manager를 열어서
    그 안의 conn을 yield 해줍니다.
    """
    with get_db_connection() as conn:
        yield conn
    # with 문을 빠져나오면 자동으로 finally가 실행되어 반납됩니다.


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