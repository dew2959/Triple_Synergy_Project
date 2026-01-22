import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # =========================================================
    # 1. 기본 프로젝트 설정
    # =========================================================
    PROJECT_NAME: str = "Interview Analysis AI"
    VERSION: str = "1.0.0"

    # =========================================================
    # 2. 데이터베이스 설정 (DB 연결용)
    # =========================================================
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "password"
    DB_NAME: str = "triple_synergy"

    # [핵심] DB 연결 주소 자동 생성 (db.py에서 이걸 씁니다)
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # =========================================================
    # 3. 보안 및 인증 (JWT) - 여기가 없어서 에러가 났던 것!
    # =========================================================
    SECRET_KEY: str = "CHANGE_THIS_TO_YOUR_SECRET_KEY"  # .env에 있으면 덮어씌워짐
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 토큰 만료 시간 (30분)

    # =========================================================
    # 4. 외부 AI API 키
    # =========================================================
    OPENAI_API_KEY: str = "" # .env에서 자동으로 읽어옴

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# 설정 인스턴스 생성
settings = Settings()