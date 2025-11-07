from fastapi import FastAPI 

app = FastAPI()

@app.get("/ping")
def ping():
    msg = {"msg":"OK"}
    return msg