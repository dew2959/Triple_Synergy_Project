"""
서비스 상세 설명 페이지
"""
import streamlit as st

st.title("📖 AI 모의면접 서비스")
st.markdown("### AI 기반 종합 면접 분석으로 완벽한 면접 준비를 지원합니다")

if st.button("← 돌아가기"):
    st.switch_page("pages/1_🏠_랜딩.py")

st.markdown("---")

st.header("서비스 소개")
st.markdown("""
AI 모의면접은 면접 영상을 업로드하면 AI가 표정, 음성, 답변 내용을 종합적으로 분석하여 
상세한 피드백을 제공하는 서비스입니다. 실제 면접에서 중요한 비언어적 커뮤니케이션과 
언어적 표현을 모두 평가하여 면접 역량을 한 단계 업그레이드할 수 있습니다.
""")

st.markdown("---")

st.header("주요 기능")

st.subheader("1️⃣ 표정 분석 (Visual Analysis)")
st.markdown("""
- 얼굴 표정, 미소, 아이컨택, 자세 등을 분석하여 면접관에게 주는 첫인상을 평가합니다.
- 자신감 있는 표정과 안정적인 비언어적 커뮤니케이션을 위한 구체적인 피드백을 제공합니다.
""")

st.subheader("2️⃣ 음성 분석 (Voice Analysis)")
st.markdown("""
- 발음 명확도, 말 속도, 목소리 톤, 볼륨, 필러 워드 등을 분석합니다.
- 효과적인 의사소통을 위한 음성 퍼포먼스 개선 방안을 제시합니다.
""")

st.subheader("3️⃣ 답변 내용 분석 (Content Analysis)")
st.markdown("""
- 답변의 구조, 논리성, 구체성, STAR 기법 활용 등을 평가합니다.
- 설득력 있고 체계적인 답변을 위한 개선 제안을 제공합니다.
""")

st.subheader("4️⃣ 종합 리포트")
st.markdown("""
- 전체 면접 퍼포먼스를 점수화하고, 각 질문별 상세 분석 결과를 제공합니다.
- 주요 강점과 개선점을 명확히 파악하고, 다음 면접을 위한 액션 플랜을 제시합니다.
""")

st.markdown("---")

st.header("분석 프로세스")

process_col1, process_col2, process_col3 = st.columns(3)

with process_col1:
    st.markdown("""
    **1. 면접 영상 업로드**
    
    📹
    
    면접 답변 영상을 업로드합니다
    """)

with process_col2:
    st.markdown("""
    **2. AI 분석 진행**
    
    🤖
    
    표정, 음성, 내용을 종합 분석합니다
    """)

with process_col3:
    st.markdown("""
    **3. 리포트 확인**
    
    📊
    
    상세한 분석 결과를 확인합니다
    """)

st.markdown("---")

st.header("이런 분께 추천합니다")
st.markdown("""
- ✅ 취업 준비생 및 이직 준비자
- ✅ 면접에 자신감이 없는 분
- ✅ 면접 퍼포먼스를 객관적으로 평가받고 싶은 분
- ✅ 비언어적 커뮤니케이션을 개선하고 싶은 분
- ✅ 체계적인 면접 준비가 필요한 분
""")

st.markdown("---")

if st.button("지금 시작하기", type="primary", use_container_width=True):
    if st.session_state.get('user'):
        st.switch_page("pages/1_🏠_랜딩.py")
    else:
        st.switch_page("pages/2_📝_회원가입.py")
