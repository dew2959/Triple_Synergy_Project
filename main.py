from fastapi import FastAPI

app = FastAPI()

@app.get("/ping")  # @ 데코레이터 : app객체의 기능get을 내 함수에 붙여주는 것. "/"최상위 디렉토리에 get 메서드 들어오면 ping 함수를 수행하라는 것 
def ping():
    msg = {"msg" : "OK"}
    return msg
