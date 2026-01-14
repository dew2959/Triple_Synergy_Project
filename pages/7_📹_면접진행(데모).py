import streamlit as st
import requests
import time

# 1. 로그인 및 세션 체크
if not st.session_state.get('user'):
    st.warning("로그인이 필요한 서비스입니다.")

    if st.button("🔐 로그인 페이지로 이동", use_container_width=True):
        st.switch_page("pages/3_🔐_로그인.py")

    st.stop()

st.title("📹 AI 모의면접")
st.info("질문을 입력하고 답변 영상을 업로드한 후 분석을 시작하세요.")

API_BASE = "http://localhost:8000"
headers = {"Authorization": f"Bearer {st.session_state.get('token')}"}

# -------------------------
# 1️⃣ 질문 입력
# -------------------------
question_text = st.text_area(
    "📝 질문 입력하기",
    placeholder="예: 자기소개를 해주세요",
    height=100
)

# -------------------------
# 2️⃣ 영상 업로드
# -------------------------
video_file = st.file_uploader(
    "🎥 답변 영상 업로드",
    type=["mp4", "mov", "avi"]
)

# -------------------------
# 3️⃣ 분석 버튼
# -------------------------
if st.button("🚀 분석 시작하기", type="primary", use_container_width=True):

    # 입력 검증
    if not question_text.strip():
        st.warning("질문을 입력해주세요.")
        st.stop()

    if video_file is None:
        st.warning("답변 영상을 업로드해주세요.")
        st.stop()

    # 분석 상태 UI
    with st.status("AI 분석을 준비 중입니다...", expanded=True) as status_ui:
        try:
            status_ui.write("📤 서버로 데이터 전송 중...")

            res = requests.post(
                f"{API_BASE}/api/v1/interview/analyze",
                headers=headers,
                files={"video": video_file},
                data={"question": question_text}
            )

            if res.status_code != 200:
                status_ui.update(label="❌ 서버 오류", state="error")
                st.error("분석 요청에 실패했습니다.")
                st.stop()

            result = res.json()
            answer_id = result.get("answer_id")

            status_ui.write("🧠 AI 분석 진행 중 (STT / Visual / Voice)...")
            time.sleep(2)  # UX용

            status_ui.update(
                label="✅ 분석 요청 완료!",
                state="complete",
                expanded=False
            )

            st.toast("AI 분석이 시작되었습니다!", icon="🎉")
            st.caption(f"답변 ID: {answer_id}")

        except Exception as e:
            status_ui.update(label="⚠️ 시스템 오류", state="error")
            st.error(str(e))