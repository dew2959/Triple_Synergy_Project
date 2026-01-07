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
        """로그인"""
        url = f"{API_BASE_URL}/auth/login"
        data = {"email": email, "password": password}
        
        response = requests.post(url, json=data)
        if response.status_code == 200:
            return response.json()
        else:
            error_detail = response.json().get('detail', '로그인에 실패했습니다.')
            raise Exception(error_detail)
    
    @staticmethod
    def get_me():
        """현재 사용자 정보 조회"""
        url = f"{API_BASE_URL}/auth/me"
        headers = get_headers()
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception("사용자 정보를 불러올 수 없습니다.")

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
