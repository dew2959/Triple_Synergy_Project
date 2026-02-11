"""
AI 모의면접 - 메인 Streamlit 앱
"""
import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="AI 모의면접",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 세션 상태 초기화
if 'user' not in st.session_state:
    st.session_state.user = None
if 'token' not in st.session_state:
    st.session_state.token = None
if 'page' not in st.session_state:
    st.session_state.page = 'landing'

# 메인 랜딩 페이지
def main():
    st.title("🎯 AI 모의면접")
    st.markdown("### AI 기반 면접 분석으로 더 나은 면접 준비를 시작하세요")
    
    st.markdown("""
    표정, 음성, 답변 내용을 종합적으로 분석하여 면접 퍼포먼스를 개선할 수 있습니다.
    실시간 피드백과 상세한 리포트로 면접 역량을 향상시켜보세요.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("회원가입", use_container_width=True, type="primary"):
            st.switch_page("pages/3_📝_회원가입.py")
    
    with col2:
        if st.button("로그인", use_container_width=True):
            st.switch_page("pages/4_🔐_로그인.py")
    
    st.markdown("---")
    st.markdown("### 주요 기능")
    
    features_col1, features_col2, features_col3, features_col4 = st.columns(4)
    
    with features_col1:
        st.markdown("""
        **😊 표정 분석**
        
        자신감 있는 표정과 안정적인 아이컨택을 분석합니다
        """)
    
    with features_col2:
        st.markdown("""
        **🎤 음성 분석**
        
        명확한 발음과 적절한 말 속도를 평가합니다
        """)
    
    with features_col3:
        st.markdown("""
        **💬 답변 내용 분석**
        
        구조적이고 설득력 있는 답변을 검토합니다
        """)
    
    with features_col4:
        st.markdown("""
        **📊 종합 리포트**
        
        상세한 분석 결과와 개선 제안을 제공합니다
        """)
    
    st.markdown("---")
    if st.button("서비스 자세히 알아보기 →"):
        st.switch_page("pages/2_📖서비스상세_.py")

if __name__ == "__main__":
    main()
