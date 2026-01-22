import streamlit as st
import requests
import time

import cv2
import numpy as np


# -----------------------------
# 1. 로그인 체크
# -----------------------------
if not st.session_state.get('user') or not st.session_state.get('token'):
    st.warning("로그인이 필요한 서비스입니다.")
    st.switch_page("pages/3_🔐_로그인.py")
    st.stop()

# -----------------------------
# 2. 분석 실패 UI 함수
# -----------------------------
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



# -----------------------------
# 3. API 및 세션 초기화
# -----------------------------
API_BASE = "http://localhost:8000"
headers = {"Authorization": f"Bearer {st.session_state.get('token')}"}

st.title("📹 AI 실시간 모의면접")

# 면접 상태 초기화
if 'current_question_idx' not in st.session_state:
    st.session_state.current_question_idx = 0
if 'interview_session_id' not in st.session_state:
    st.session_state.interview_session_id = None
if 'questions' not in st.session_state:
    st.session_state.questions = []

# -----------------------------
# 4. Haar Cascade 초기화
# -----------------------------
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# -----------------------------
# 4. 면접 시작 전 가이드 화면
# -----------------------------
if st.session_state.interview_session_id is None:
    st.subheader("📌 면접 가이드라인")
    st.info("""
    1. 밝은 조명을 유지하세요 
    2. 얼굴을 화면 중앙에 두고 카메라를 바라보세요.
    3. 답변은 1~2분 내외로 간결하게 말해주세요.
    4. 말하는 속도와 발음을 또렷하게 유지해주세요.
    5. 준비가 완료되면 버튼을 눌러 면접을 시작합니다.
    """)

    # 웹캠 + 얼굴 위치 가이드
    camera_input = st.camera_input("📷 카메라 테스트")
    if camera_input:
        # OpenCV로 변환
        file_bytes = np.asarray(bytearray(camera_input.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 얼굴 검출
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)

        # 영상 중앙 가이드 박스
        h, w, _ = img.shape
        guide_w, guide_h = int(w*0.3), int(h*0.5)
        guide_x, guide_y = w//2 - guide_w//2, h//2 - guide_h//2
        cv2.rectangle(img, (guide_x, guide_y), (guide_x+guide_w, guide_y+guide_h), (0,255,0), 2)

        # 얼굴 위치 표시
        for (x, y, fw, fh) in faces:
            cv2.rectangle(img, (x, y), (x+fw, y+fh), (255,0,0), 2)

        st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), use_column_width=True, caption="얼굴 위치 가이드")


    # 면접 시작 버튼
    if st.button("준비 완료 - 면접 시작", type="primary", use_container_width=True):
        try:
            response = requests.post(
                f"{API_BASE}/api/v1/session/",
                json={"job_role": "Backend Developer", "company_name": "Tech Corp"},
                headers=headers
            )
            if response.status_code == 201:
                data = response.json()
                st.session_state.interview_session_id = data['session_id']
                st.session_state.questions = data['questions']
                st.session_state.current_question_idx = 0
                st.rerun()
            else:
                st.error(f"세션 생성 실패: {response.status_code}")
        except Exception as e:
            st.error(f"세션 생성 실패: {e}")
    st.stop()

# -----------------------------
# 5. 질문 진행 및 답변 녹화
# -----------------------------
questions = st.session_state.questions
idx = st.session_state.current_question_idx

if idx < len(questions):
    current_q = questions[idx]
    st.subheader(f"Q{idx+1}. {current_q['content']}")
    st.caption(f"카테고리: {current_q['category']}")

    # 얼굴 가이드 포함 카메라 입력
    video_file = st.camera_input(f"Q{idx+1} 답변 촬영 (얼굴을 중앙에 맞춰주세요)")
    if video_file:
        file_bytes = np.asarray(bytearray(video_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)

        h, w, _ = img.shape
        guide_w, guide_h = int(w*0.3), int(h*0.5)
        guide_x, guide_y = w//2 - guide_w//2, h//2 - guide_h//2
        cv2.rectangle(img, (guide_x, guide_y), (guide_x+guide_w, guide_y+guide_h), (0,255,0), 2)
        for (x, y, fw, fh) in faces:
            cv2.rectangle(img, (x, y), (x+fw, y+fh), (255,0,0), 2)

        st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), use_column_width=True, caption="얼굴 위치 가이드")

        # 제출 버튼
        if st.button(f"제출 - Q{idx+1}", use_container_width=True, type="primary"):
            with st.status("🚀 AI 분석 중...", expanded=True) as status_ui:
                try:
                    # 서버 업로드
                    res = requests.post(
                        f"{API_BASE}/api/v1/interview/upload",
                        files={"file": video_file},
                        data={"question_id": current_q['question_id']},
                        headers=headers
                    )

                    if res.status_code in (200, 201):
                        result = res.json()
                        st.write("✅ 영상 업로드 완료")
                        st.write("🧠 AI 분석 진행 중...")
                        time.sleep(2)

                        if result.get("analysis_status") == "FAILED":
                            status_ui.update(label="❌ 분석 실패", state="error", expanded=True)
                            display_analysis_failure(result.get("answer_id"), result.get("message"))
                        else:
                            status_ui.update(label="✅ 분석 완료", state="complete", expanded=False)
                            st.toast("답변이 성공적으로 기록되었습니다!", icon="🎉")
                            st.session_state.current_question_idx += 1
                            st.rerun()
                    else:
                        st.error(f"서버 응답 오류: {res.status_code}")

                except Exception as e:
                    status_ui.update(label="⚠️ 시스템 오류", state="error")
                    display_analysis_failure("N/A", str(e))

# -----------------------------
# 6. 모든 질문 종료 시
# -----------------------------
else:
    st.balloons()
    st.success("모든 면접 질문이 종료되었습니다!")
    if st.button("📊 결과 리포트 보기", type="primary", use_container_width=True):
        st.switch_page("pages/6_📊_리포트.py")