"""
API 클라이언트 유틸리티
Streamlit에서 FastAPI 백엔드와 통신하는 함수들
"""
import requests
import streamlit as st

API_BASE_URL = "http://localhost:8000/api/v1"

def get_headers():
    """인증 헤더 포함"""
    headers = {"Content-Type": "application/json"}
    token = st.session_state.get('token')
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

class AuthAPI:
    """인증 관련 API"""
    
    @staticmethod
    def signup(email: str, password: str, name: str = None):
        """회원가입"""
        url = f"{API_BASE_URL}/auth/signup"
        data = {"email": email, "password": password}
        if name:
            data["name"] = name
        
        response = requests.post(url, json=data)
        if response.status_code == 200:
            return response.json()
        else:
            error_detail = response.json().get('detail', '회원가입에 실패했습니다.')
            raise Exception(error_detail)
    
    @staticmethod
    def login(email: str, password: str):
        url = f"{API_BASE_URL}/auth/login"

        form = {
            "grant_type": "password",   # ✅ pattern ^password$ 맞추기
            "username": email.strip(),  # ✅ 백엔드는 username 필드로 받음 (여기에 email을 넣는 구조)
            "password": password,
            "scope": "",                # optional
            # client_id / client_secret 은 보통 비워둠
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(url, data=form, headers=headers)

        # 응답 파싱
        try:
            body = response.json()
        except Exception:
            body = {"raw": response.text}

        if response.status_code == 200:
            return body

        # 에러 메시지 최대한 살리기
        detail = body.get("detail") if isinstance(body, dict) else None
        raise Exception(f"{response.status_code} {detail or body}")

    
    @staticmethod
    def get_me():
        """현재 사용자 정보 조회 (디버그 포함)"""
        url = f"{API_BASE_URL}/auth/me"
        headers = get_headers()

        response = requests.get(url, headers=headers)

        # ✅ 에러 바디를 안전하게 파싱
        try:
            body = response.json()
        except Exception:
            body = {"raw": response.text}

        if response.status_code == 200:
            return body

        # ✅ 지금 뭐가 문제인지 한 줄로 보여주기
        raise Exception(f"/auth/me failed: {response.status_code} {body}")


class ReportAPI:
    """리포트 관련 API"""
    
    @staticmethod
    def get_report(session_id: int):
        """리포트 조회"""
        url = f"{API_BASE_URL}/interview/report/{session_id}"
        headers = get_headers()
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            error_detail = response.json().get('detail', '리포트를 불러올 수 없습니다.')
            raise Exception(error_detail)

class InterviewAPI:
    """면접 관련 API"""
    
    @staticmethod
    def upload_video(question_id: int, video_file):
        """면접 영상 업로드"""
        url = f"{API_BASE_URL}/interview/upload"
        headers = {"Authorization": f"Bearer {st.session_state.get('token')}"}
        
        files = {"file": video_file}
        data = {"question_id": question_id}
        
        response = requests.post(url, files=files, data=data, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            error_detail = response.json().get('detail', '영상 업로드에 실패했습니다.')
            raise Exception(error_detail)

# API 인스턴스
auth_api = AuthAPI()
report_api = ReportAPI()
interview_api = InterviewAPI()
