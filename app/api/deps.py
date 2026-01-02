# app/api/deps.py
import psycopg2
from typing import Generator
# db_config는 프로젝트 설정에 맞게 가져오세요
from app.core.config import settings 

def get_db_conn() -> Generator:
    try:
        conn = psycopg2.connect(settings.DATABASE_URL)
        yield conn
    finally:
        conn.close()