"""
로그인 페이지
"""
import streamlit as st
from utils.api_client import auth_api
import os
import sys

# 프로젝트 루트 경로를 추가하여 utils를 찾을 수 있게 합니다.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from utils.api_client import auth_api
except ImportError:
    st.error("api_client.py를 찾을 수 없습니다. utils 폴더에 파일이 있는지 확인해주세요.")
    st.stop()


st.title("🔐 로그인")
st.markdown("AI 모의면접 서비스에 오신 것을 환영합니다")

with st.form("login_form"):
    email = st.text_input("이메일", placeholder="example@email.com")
    password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")
    
    col1, col2 = st.columns(2)
    
    with col1:
        submitted = st.form_submit_button("로그인", use_container_width=True, type="primary")
    
    with col2:
        if st.form_submit_button("돌아가기", use_container_width=True):
            st.switch_page("streamlit_app.py")
    
    if submitted:
        if not email or not password:
            st.error("이메일과 비밀번호를 입력해주세요.")
        else:
            login_success = False
            
            try:
                result = auth_api.login(email, password)
                
                # 토큰 및 유저 정보 저장
                st.session_state.token = result["access_token"]
                st.session_state.user = {
                    "email": email
                }
                
                st.success("로그인 성공!")
                # 여기서 바로 이동하지 않고 성공 플래그만 세웁니다.
                login_success = True 

            except Exception as e:
                st.error(f"로그인 실패: {e}")
            
            # try-except 블록이 끝난 후, 성공했다면 페이지 이동
            # (이제 이동 신호가 에러로 잡히지 않습니다)
            if login_success:
                st.info("프로필 설정 페이지로 이동합니다...")
                st.switch_page("pages/5_👤_이력서.py")


st.markdown("---")
st.markdown("계정이 없으신가요? [회원가입 페이지로 이동](pages/3_📝_회원가입.py)")