from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import interview # 라우터 import
from app.api.v1 import interview, auth

app = FastAPI()

# CORS 설정 (프론트엔드 연결용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501"    # Streamlit
        "http://127.0.0.1:8501"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록 (prefix를 붙이면 주소 관리가 편함)
# 실제 주소: http://localhost:8000/api/v1/interview/upload

app.include_router(interview.router, prefix="/api/v1/interview", tags=["Interview"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
#app.include_router(resume.router, prefix="/api/v1/resume", tags=["resume"])


@app.get("/")
def read_root():
    return {"message": "Triple Synergy API is running!"}