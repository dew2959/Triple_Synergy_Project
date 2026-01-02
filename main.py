# main.py
from fastapi import FastAPI
from app.api.v1 import interview # 라우터 import
from app.api.v1 import interview, auth

app = FastAPI()

# 라우터 등록 (prefix를 붙이면 주소 관리가 편함)
# 실제 주소: http://localhost:8000/api/v1/interview/upload
app.include_router(interview.router, prefix="/api/v1/interview", tags=["Interview"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])


app.get("/")
def read_root():
    return {"message": "Triple Synergy API is running!"}