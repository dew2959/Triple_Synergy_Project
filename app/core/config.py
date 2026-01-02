import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Interview Analysis AI"
    VERSION: str = "1.0.0"

    # Database (Raw SQL 기준)
    DB_HOST: str = os.getenv("DB_HOST")
    DB_PORT: int = int(os.getenv("DB_PORT", 5432))
    DB_NAME: str = os.getenv("DB_NAME")
    DB_USER: str = os.getenv("DB_USER")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD")

    # AI
    OPENAI_API_KEY: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # .env에 있지만 여기 정의 안 된 변수는 에러 내지 말고 무시하라는 설정
        extra = "ignore"

settings = Settings()
