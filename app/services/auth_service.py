from psycopg2.extensions import connection
from app.repositories.user_repo import user_repo
from app.core.security import verify_password, get_password_hash, create_access_token
from app.schemas.user import UserCreate, UserLogin

class AuthService:
    def signup(self, conn: connection, user_in: UserCreate) -> dict:
        # 1. 이메일 중복 체크
        existing_user = user_repo.get_by_email(conn, user_in.email)
        if existing_user:
            raise ValueError("이미 존재하는 이메일입니다.")
        
        # 2. 비밀번호 해싱
        hashed_pw = get_password_hash(user_in.password)
        
        # 3. DB 저장
        return user_repo.create(conn, user_in.email, hashed_pw, user_in.name)

    def login(self, conn: connection, user_in: UserLogin) -> dict:
        # 1. 유저 조회
        user = user_repo.get_by_email(conn, user_in.email)
        if not user:
            raise ValueError("이메일 또는 비밀번호가 잘못되었습니다.")
        
        # 2. 비밀번호 검증
        if not verify_password(user_in.password, user['password_hash']):
            raise ValueError("이메일 또는 비밀번호가 잘못되었습니다.")
            
        # 3. 토큰 발급
        access_token = create_access_token(subject=user['user_id'])
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_info": {
                "user_id": user['user_id'],
                "email": user['email'],
                "name": user['name']
            }
        }

auth_service = AuthService()