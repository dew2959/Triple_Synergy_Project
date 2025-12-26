import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class Settings:
    # 프로젝트 기본 설정
    PROJECT_NAME: str = "Interview Analysis AI"
    VERSION: str = "1.0.0"

    # 데이터베이스 설정
    DB_USER: str = os.getenv("DB_USER")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD")
    DB_HOST: str = os.getenv("DB_HOST")
    DB_PORT: str = os.getenv("DB_PORT")
    DB_NAME: str = os.getenv("DB_NAME")
    
    # URL 인코딩 등 복잡한 로직을 여기서 처리 (Clean Code)
    @property
    def DATABASE_URL(self) -> str:
        from urllib.parse import quote_plus
        encoded_user = quote_plus(self.DB_USER)
        encoded_password = quote_plus(self.DB_PASSWORD)
        return f"postgresql://{encoded_user}:{encoded_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # AI API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")

settings = Settings()