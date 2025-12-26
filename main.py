from fastapi import FastAPI
from app.core.db import engine, Base
# 모델을 import 해줘야 DB 테이블이 생성됩니다.
from app.models import answer 

# 테이블 자동 생성 (실무에선 Alembic을 쓰지만 지금은 이걸로 유지)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Interview AI Backend")

# 헬스 체크용 (서버 켜졌나 확인)
@app.get("/")
def health_check():
    return {"status": "ok", "structure": "refactored"}

# 나중에 여기에 router를 추가할 예정입니다.
# from app.api.v1 import interview
# app.include_router(interview.router)