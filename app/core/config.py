from pydantic_settings import BaseSettings 
from pydantic import Field
class Settings(BaseSettings):
    # Project
    PROJECT_NAME: str = "Interview Analysis AI"
    VERSION: str = "1.0.0"

    # Database
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int = Field(..., env="DB_PORT")
    DB_NAME: str

    # AI
    OPENAI_API_KEY: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # .env에 있지만 여기 정의 안 된 변수는 에러 내지 말고 무시하라는 설정
        extra = "ignore"

settings = Settings()
