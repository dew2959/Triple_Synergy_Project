from pydantic import BaseSettings, Field

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

settings = Settings()
