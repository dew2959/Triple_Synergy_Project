from fastapi import FastAPI
from app.api.v1 import interview, auth

app = FastAPI()


app.include_router(interview.router, prefix="/api/v1/interview", tags=["Interview"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])


@app.get("/")
def read_root():
    return {"message": "Triple Synergy API is running!"}