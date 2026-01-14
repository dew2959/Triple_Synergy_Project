import requests

class APIClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url

    def signup(self, email, password, name=None):
        res = requests.post(
            f"{self.base_url}/api/v1/auth/signup",
            json={"email": email, "password": password, "name": name},
        )
        if res.status_code in (200, 201):
            return res.json()
        raise Exception(res.text)

    def login(self, email, password):
        res = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            data={"username": email, "password": password},
        )
        if res.status_code == 200:
            return res.json()
        raise Exception(res.text)

auth_api = APIClient()
