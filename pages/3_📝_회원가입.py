"""
회원가입 페이지
"""
import streamlit as st
from utils.api_client import auth_api

st.title("📝 회원가입")
st.markdown("AI 모의면접 서비스를 시작하세요")

with st.form("signup_form"):
    email = st.text_input("이메일", placeholder="example@email.com")
    password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요", help="최소 6자 이상")
    name = st.text_input("이름 (선택)", placeholder="이름을 입력하세요")
    
    col1, col2 = st.columns(2)
    
    with col1:
        submitted = st.form_submit_button("회원가입", use_container_width=True, type="primary")
    
    with col2:
        if st.form_submit_button("돌아가기", use_container_width=True):
            st.switch_page("streamlit_app.py")
    
    if submitted:
        if not email or not password:
            st.error("이메일과 비밀번호를 입력해주세요.")
        elif len(password) < 6:
            st.error("비밀번호는 최소 6자 이상이어야 합니다.")
        else:
            try:
                result = auth_api.signup(email, password, name if name else None)
                st.success("회원가입이 완료되었습니다!")
                st.session_state.user = result
                st.info("로그인 페이지로 이동합니다...")
                st.switch_page("pages/3_🔐_로그인.py")
            except Exception as e:
                st.error(f"회원가입 실패: {str(e)}")

st.markdown("---")
st.markdown("이미 계정이 있으신가요? [로그인 페이지로 이동](pages/3_🔐_로그인.py)")
