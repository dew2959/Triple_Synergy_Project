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


# =========================================================
# ✅ 0️⃣ (추가) 이력서 리스트 불러오기 + 이번 면접에 사용할 이력서 선택
# =========================================================
st.subheader("📄 이력서 선택")

def fetch_resumes():
    urls = [
        f"{API_BASE}/api/v1/resume/",
    ]
    last_err = None
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 404:
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_err = e
    raise last_err if last_err else RuntimeError("이력서 목록을 불러오지 못했습니다.")

@st.cache_data(show_spinner=False, ttl=30)
def load_resumes_cached(token: str):
    return fetch_resumes()

try:
    with st.spinner("이력서 목록 불러오는 중..."):
        resumes_payload = load_resumes_cached(st.session_state.get("token", ""))
except Exception as e:
    st.error(f"이력서 목록 조회 실패: {e}")
    st.stop()

# 응답 형태 흡수
if isinstance(resumes_payload, dict):
    resumes = resumes_payload.get("items") or resumes_payload.get("resumes") or resumes_payload.get("data") or []
elif isinstance(resumes_payload, list):
    resumes = resumes_payload
else:
    resumes = []

if not resumes:
    st.warning("등록된 이력서가 없습니다. 먼저 이력서를 등록해주세요.")
    st.stop()

def pick_first(d: dict, keys: list, default=None):
    for k in keys:
        if k in d and d.get(k) not in (None, ""):
            return d.get(k)
    return default

def get_resume_id(r: dict):
    return pick_first(r, ["id", "resume_id", "uuid"])

def get_resume_label(r: dict):
    # ✅ 너가 원하는 표시 요소: 직무 / 회사 / 작성날짜
    title = pick_first(r, ["name"], default=f"Resume {get_resume_id(r)}")
    role = pick_first(r, ["job_title"], default="직무 미기재")  
    company = pick_first(r, ["target_company"], default="회사 미기재") 
    created = pick_first(r, ["created_at", "createdAt"], default=None)

    # 날짜 포맷이 길면 앞부분만 잘라서 보기 좋게 (예: 2026-01-14T12:34:56 -> 2026-01-14)
    if isinstance(created, str) and len(created) >= 10:
        created = created[:10]

    # 예: "PD 이력서(방송) · PD · MBC · 2026-01-14"
    return f"{title} · {role} · {company} · {created}"

options = []
for r in resumes:
    rid = get_resume_id(r)
    if rid is None:
        continue
    options.append((rid, get_resume_label(r)))

if not options:
    st.error("이력서 목록에서 id를 찾지 못했습니다. (응답 필드 확인 필요)")
    st.stop()

# 이전 선택 유지
default_idx = 0
prev_selected = st.session_state.get("selected_resume_id")
if prev_selected is not None:
    for i, (rid, _) in enumerate(options):
        if str(rid) == str(prev_selected):
            default_idx = i
            break

selected_resume_id, selected_resume_label = st.selectbox(
    "이번 면접에 사용할 이력서를 선택하세요",
    options=options,
    index=default_idx,
    format_func=lambda x: x[1],
)

st.session_state["selected_resume_id"] = selected_resume_id
st.caption(f"선택됨: {selected_resume_label}")


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
    if not selected_resume_id:
        st.warning("이력서를 선택해주세요.")
        st.stop()

    if not question_text.strip():
        st.warning("질문을 입력해주세요.")
        st.stop()

    if video_file is None:
        st.warning("답변 영상을 업로드해주세요.")
        st.stop()

    # 분석 상태 UI
    with st.status("AI 분석을 준비 중입니다...", expanded=True) as status_ui:
        try:
            # =========================
            # 1) 업로드 (answer_id 받기)
            # =========================
            status_ui.write("📤 서버로 영상 업로드 중...")

            files = {
                "file": (video_file.name, video_file.getvalue(), video_file.type)
            }

            upload_res = requests.post(
                f"{API_BASE}/api/v1/interview/upload",
                headers=headers,
                files=files,
                data={
                    "question_id": question_text,         # ✅ 백엔드가 upload에서 받으면 사용
                    "resume_id": selected_resume_id,   # ✅ 백엔드가 upload에서 받으면 사용
                },
                timeout=300,
            )

            if upload_res.status_code != 200:
                status_ui.update(label="❌ 업로드 실패", state="error")
                st.error(f"업로드 실패 (status={upload_res.status_code})")
                st.code(upload_res.text)
                st.stop()

            upload_result = upload_res.json()
            answer_id = upload_result.get("answer_id") or upload_result.get("id")

            if not answer_id:
                status_ui.update(label="❌ 업로드 응답 오류", state="error")
                st.error("업로드는 성공했지만 answer_id를 받지 못했습니다.")
                st.json(upload_result)
                st.stop()

            # =========================
            # 2) 분석 시작
            # =========================
            status_ui.write("🧠 AI 분석 요청 중 (STT / Visual / Voice)...")

            analyze_res = requests.post(
                f"{API_BASE}/api/v1/interview/{answer_id}/analyze",
                headers=headers,
                data={
                    "question": question_text,         # ✅ 백엔드가 analyze에서 받으면 사용
                    "resume_id": selected_resume_id,   # ✅ 백엔드가 analyze에서 받으면 사용
                },
                timeout=300,
            )

            if analyze_res.status_code != 200:
                status_ui.update(label="❌ 분석 요청 실패", state="error")
                st.error(f"분석 요청 실패 (status={analyze_res.status_code})")
                st.code(analyze_res.text)
                st.stop()

            status_ui.update(label="✅ 분석 요청 완료!", state="complete", expanded=False)

            st.toast("AI 분석이 시작되었습니다!", icon="🎉")
            st.caption(f"답변 ID: {answer_id}")

        except Exception as e:
            status_ui.update(label="⚠️ 시스템 오류", state="error")
            st.error(str(e))