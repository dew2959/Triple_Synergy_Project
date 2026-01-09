import streamlit as st
import requests
import time
import os
import sys

# [수정] 파이썬이 app 패키지를 찾을 수 있도록 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# [수정] models 팩키지의 __init__.py 에러를 피하기 위해 직접 경로에서 가져오기
from app.models.enums import SessionStatus

# 1. 필수 세션 데이터 체크
if not st.session_state.get('interview_session_id'):
    st.warning("진행 중인 면접 세션 정보가 없습니다.")
    st.switch_page("pages/1_🏠_랜딩.py")
    st.stop()

st.title("📝 면접 응시 요약")
st.markdown("### 수고하셨습니다! 모든 답변이 제출되었습니다.")

# API 설정
API_BASE = "http://localhost:8000"
headers = {"Authorization": f"Bearer {st.session_state.get('token')}"}
session_id = st.session_state.interview_session_id

# 2. 면접 요약 정보 레이아웃
st.divider()

col1, col2 = st.columns(2)
with col1:
    st.info(f"**직무:** {st.session_state.get('job_role', 'Backend Developer')}")
with col2:
    st.info(f"**회사:** {st.session_state.get('company_name', 'Tech Corp')}")

# 3. 답변 제출 현황 리스트 (SessionResponse 구조 활용)
st.subheader("✅ 답변 제출 현황")

questions = st.session_state.get('questions', [])
for i, q in enumerate(questions):
    with st.container():
        c1, c2, c3 = st.columns([1, 4, 2])
        c1.write(f"**Q{i+1}**")
        c2.write(q['content'])
        # [팁] constants.py의 ANSWER_STATUS_DONE 등의 변수와 연동하면 좋습니다
        c3.success("제출 완료") 

st.divider()

# 4. 전체 종합 분석 프로그레스 (이 부분에 자동 리다이렉션 추가)
st.subheader("🤖 AI 종합 리포트 생성 중")
progress_bar = st.progress(0)
status_text = st.empty()

analysis_steps = [
    "각 문항별 점수 집계 중...",
    "비언어적 요소(표정, 음성) 종합 분석 중...",
    "답변 내용의 논리성 및 직무 적합도 평가 중...",
    "최종 개선 제안(Action Plan) 생성 중...",
    "리포트 구성 완료!"
]

for i, step in enumerate(analysis_steps):
    progress = (i + 1) / len(analysis_steps)
    progress_bar.progress(progress)
    status_text.write(f"현재 단계: {step}")
    time.sleep(1.2) 

# 5. 자동 이동 기능 추가
st.balloons()
st.success("🎉 모든 분석이 완료되었습니다! 리포트로 이동합니다.")
time.sleep(2) # 성공 메시지를 보여줄 여유 시간
st.switch_page("pages/6_📊_리포트.py")