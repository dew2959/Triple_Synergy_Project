import requests

class APIClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url

    def signup(self, email, password, name=None):
        """회원가입: 201 Created 응답을 정상 처리합니다."""
        url = f"{self.base_url}/api/v1/auth/signup"
        payload = {"email": email, "password": password, "name": name}
        
        response = requests.post(url, json=payload)
        
        # 200(OK)뿐만 아니라 201(Created)도 성공으로 처리
        if response.status_code in [200, 201]:
            return response.json()
        else:
            raise Exception(f"회원가입 실패: {response.json()}")

    def login(self, email, password):
        """로그인: OAuth2 표준에 맞춰 username과 Form 형식을 사용합니다."""
        url = f"{self.base_url}/api/v1/auth/login"
        
        # FastAPI의 OAuth2PasswordRequestForm은 'username'이라는 이름을 원함
        payload = {
            "username": email,
            "password": password
        }
        
        # json= 대신 data=를 사용하여 application/x-www-form-urlencoded로 전송
        response = requests.post(url, data=payload)
        
        if response.status_code == 200:
            return response.json() # 성공 시 토큰 반환
        else:
            error_info = response.json()
            print(f"DEBUG: 서버 응답 코드 {response.status_code}")
            print(f"DEBUG: 서버 응답 내용 {response.text}")
            raise Exception(f"서버 응답: {error_info}")
        
auth_api = APIClient()