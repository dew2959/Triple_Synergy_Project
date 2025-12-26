import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
from urllib.parse import quote_plus  # [1] 이 줄을 추가하세요!

load_dotenv()

# 환경변수 가져오기
USER = os.getenv("DB_USER")
PASSWORD = os.getenv("DB_PASSWORD")
HOST = os.getenv("DB_HOST")
PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# [2] 비밀번호와 유저명을 안전한 문자로 변환(인코딩)합니다.
# 이렇게 하면 @ 같은 특수문자도 안전하게 처리됩니다.
encoded_password = quote_plus(PASSWORD)
encoded_user = quote_plus(USER)

# [3] 인코딩된 변수를 넣어서 URL을 만듭니다.
SQLALCHEMY_DATABASE_URL = f"postgresql://{encoded_user}:{encoded_password}@{HOST}:{PORT}/{DB_NAME}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    pool_size=5, 
    max_overflow=10
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()