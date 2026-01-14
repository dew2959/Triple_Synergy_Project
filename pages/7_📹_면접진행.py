import streamlit as st
import requests
import time


# 1. 로그인 및 세션 체크
if not st.session_state.get('user'):
    st.warning("로그인이 필요한 서비스입니다.")
    st.switch_page("pages/3_🔐_로그인.py")
    st.stop()

# --- 분석 실패 시 화면을 구성하는 함수 (상단에 정의) ---
def display_analysis_failure(answer_id, error_msg="네트워크 연결이 불안정합니다."):
    st.error("⚠️ AI 분석 중 오류가 발생했습니다.")
    
    with st.expander("상세 에러 내용 확인"):
        st.write(f"**상태:** ANSWER_STATUS_FAILED")
        st.write(f"**답변 ID:** {answer_id}")
        st.write(f"**오류 메시지:** {error_msg}")
    
    st.markdown("""
    분석 과정에서 일시적인 오류가 발생했습니다. 아래 버튼을 통해 조치하실 수 있습니다.
    """)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 분석 다시 시도", use_container_width=True):
            st.info("해당 답변에 대해 분석을 재요청합니다...")
            st.rerun()
            
    with col2:
        if st.button("📹 답변 다시 하기", use_container_width=True, type="primary"):
            st.rerun()

# --- 메인 UI 시작 ---
st.title("📹 AI 실시간 모의면접")
st.info("질문을 읽고 답변 영상을 업로드해주세요. AI가 당신의 인터페이스와 내용을 분석합니다.")

# API 설정
API_BASE = "http://localhost:8000"
headers = {"Authorization": f"Bearer {st.session_state.get('token')}"}

# 2. 면접 세션 상태 관리 초기화
if 'current_question_idx' not in st.session_state:
    st.session_state.current_question_idx = 0
if 'interview_session_id' not in st.session_state:
    st.session_state.interview_session_id = None
if 'questions' not in st.session_state:
    st.session_state.questions = []

# 3. 면접 시작 버튼 (최초 1회 실행)
if st.session_state.interview_session_id is None:
    if st.button("면접 시작하기", type="primary", use_container_width=True):
        try:
            response = requests.post(
                f"{API_BASE}/api/v1/interview/session",
                json={"job_role": "Backend Developer", "company_name": "Tech Corp"},
                headers=headers
            )
            if response.status_code == 201:
                data = response.json()
                st.session_state.interview_session_id = data['session_id']
                st.session_state.questions = data['questions']
                st.rerun()
        except Exception as e:
            st.error(f"세션 생성 실패: {e}")
    st.stop()

# 4. 질문 제시 및 영상 업로드 UI
questions = st.session_state.questions
idx = st.session_state.current_question_idx

if idx < len(questions):
    current_q = questions[idx]
    
    st.subheader(f"Q{idx + 1}. {current_q['content']}")
    st.caption(f"카테고리: {current_q['category']}")

    # 영상 업로드 컴포넌트
    video_file = st.file_uploader(f"질문 {idx+1}에 대한 답변 영상 업로드", type=['mp4', 'mov', 'avi'])

    if video_file:
        if st.button(f"{idx + 1}번 답변 제출", use_container_width=True, type="primary"):
            # 분석 상태창 표시
            with st.status("🚀 AI 분석 시스템 가동 중...", expanded=True) as status_ui:
                try:
                    # [Step 1] 파일 전송
                    st.write("📂 영상을 서버로 업로드 중...")
                    res = requests.post(
                        f"{API_BASE}/api/v1/interview/answer",
                        files={"video": video_file},
                        data={"question_id": current_q['question_id']},
                        headers=headers
                    )

                    if res.status_code == 201:
                        # ⚠️ 중요: 여기서 'result' 변수를 생성하여 에러를 방지합니다.
                        result = res.json()
                        
                        # [Step 2] AI 분석 시뮬레이션 및 실제 상태 체크
                        st.write("🧠 AI가 내용을 분석하고 있습니다 (STT/Visual/Voice)...")
                        time.sleep(2) 
                        
                        # API 응답 결과에 따른 화면 처리
                        if result.get("status") == "FAILED":
                            status_ui.update(label="❌ 분석 실패", state="error", expanded=True)
                            display_analysis_failure(result.get("answer_id"), result.get("message"))
                        else:
                            # 성공 시 로직
                            status_ui.update(label="✅ 분석 완료!", state="complete", expanded=False)
                            st.toast("답변이 성공적으로 기록되었습니다!", icon="🎉")
                            time.sleep(1)
                            st.session_state.current_question_idx += 1
                            st.rerun()
                    else:
                        st.error(f"서버 응답 오류: {res.status_code}")
                        
                except Exception as e:
                    # 시스템 레벨 에러 발생 시 (네트워크 단절 등)
                    status_ui.update(label="⚠️ 시스템 오류 발생", state="error")
                    display_analysis_failure("N/A", str(e))

# 5. 모든 면접 종료 시
else:
    st.balloons()
    st.success("모든 면접 질문이 끝났습니다! AI 분석이 완료될 때까지 잠시만 기다려주세요.")
    if st.button("결과 리포트 보러가기", type="primary", use_container_width=True):
        st.switch_page("pages/6_📊_리포트.py")