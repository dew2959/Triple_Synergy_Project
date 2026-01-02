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
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")

settings = Settings()
