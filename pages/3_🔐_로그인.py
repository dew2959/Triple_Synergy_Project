"""
로그인 페이지
"""
import streamlit as st
from utils.api_client import auth_api

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
            try:
                result = auth_api.login(email, password)

                token = result.get("access_token") or result.get("metrics", {}).get("access_token")
                if not token:
                    st.error(f"access_token이 없어요: {result}")
                    st.stop()

                st.session_state.token = token
                st.session_state.user = None  # ✅ me가 없으니 비워둠

                st.success("로그인 성공!")
                st.info("프로필 설정 페이지로 이동합니다...")
                st.switch_page("pages/4_👤_온보딩.py")


            except Exception as e:
                st.error(f"로그인 실패: {str(e)}")


st.markdown("---")
st.markdown("계정이 없으신가요? [회원가입 페이지로 이동](pages/2_📝_회원가입.py)")
