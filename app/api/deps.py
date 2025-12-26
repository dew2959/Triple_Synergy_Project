# app/api/deps.py (먼저 작성)
from typing import Generator
from app.core.db import SessionLocal

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()