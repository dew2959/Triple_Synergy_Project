from fastapi import APIRouter, Depends, HTTPException, status
from psycopg2.extensions import connection

from app.api.deps import get_db_conn, get_current_user
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.services.auth_service import auth_service

router = APIRouter()

@router.post("/signup", response_model=UserResponse)
def signup(
    user_in: UserCreate,
    conn: connection = Depends(get_db_conn)
):
    try:
        return auth_service.signup(conn, user_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
def login(
    user_in: UserLogin,
    conn: connection = Depends(get_db_conn)
):
    try:
        return auth_service.login(conn, user_in)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: dict = Depends(get_current_user)):
    """현재 로그인한 사용자 정보 조회 (토큰 필요)"""
    return current_user