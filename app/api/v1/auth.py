from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from psycopg2.extensions import connection
from pydantic import ValidationError

from app.api.deps import get_db_conn
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserResponse, UserLogin
from app.services.auth_service import auth_service

router = APIRouter()

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(
    user_in: UserCreate,
    conn: connection = Depends(get_db_conn)
):
    try:
        return auth_service.signup(conn, user_in)
    except ValueError as e:
        # 서비스에서 "이미 존재하는 이메일입니다" 에러가 오면 400으로 반환
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=Token)
def login(
    conn: connection = Depends(get_db_conn),
    form_data: OAuth2PasswordRequestForm = Depends() 
):
    try:
        # 1. 여기서 이메일 형식이 맞는지 검사 (Pydantic)
        user_in = UserLogin(
            email=form_data.username, 
            password=form_data.password
        )
        
        # 2. 서비스 로그인 로직 실행
        return auth_service.login(conn, user_in)
        
    except ValidationError:
        # 이메일 형식이 틀렸을 때 (l5726493 입력 시)
        raise HTTPException(
            status_code=422, 
            detail="유효하지 않은 이메일 형식입니다. (@ 포함 필수)"
        )
        
    except ValueError as e:
        # 아이디가 없거나 비밀번호가 틀렸을 때 (AuthService에서 발생)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )