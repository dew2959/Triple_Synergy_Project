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
    with st.status("AI 면접 프로세스를 진행 중입니다...", expanded=True) as status_ui:
        try:
            # =========================
            # 1단계: 세션 생성
            # =========================
            status_ui.write("1️⃣ 면접 세션을 생성하고 있습니다...")
            
            session_payload = {
                "resume_id": int(selected_resume_id) # 이력서 ID 기반 세션 생성
            }
            
            session_res = requests.post(
                f"{API_BASE}/api/v1/session/",
                headers=headers,
                json=session_payload,
                timeout=10
            )

            if session_res.status_code != 200:
                status_ui.update(label="❌ 세션 생성 실패", state="error")
                st.error(f"세션 생성 오류: {session_res.text}")
                st.stop()
            
            session_data = session_res.json()
            session_id = session_data.get("session_id")
            status_ui.write(f"✅ 세션 생성 완료 (ID: {session_id})")


            # =========================
            # 2단계: 질문 등록
            # =========================
            status_ui.write("2️⃣ 질문을 등록하고 있습니다...")
            
            question_payload = {
                "session_id": session_id,
                "content": question_text,
                "category": "GENERAL", # 기본값 설정
                "order_index": 1
            }

            question_res = requests.post(
                f"{API_BASE}/api/v1/question/",
                headers=headers,
                json=question_payload,
                timeout=10
            )

            if question_res.status_code != 200:
                status_ui.update(label="❌ 질문 등록 실패", state="error")
                st.error(f"질문 등록 오류: {question_res.text}")
                st.stop()
            
            question_data = question_res.json()
            question_id = question_data.get("question_id")
            status_ui.write(f"✅ 질문 등록 완료 (ID: {question_id})")


            # =========================
            # 3단계: 영상 업로드 (답변 등록)
            # =========================
            status_ui.write("3️⃣ 답변 영상을 업로드하고 있습니다...")

            # 파일 포인터를 처음으로 되돌림 (혹시 모를 에러 방지)
            video_file.seek(0)
            
            files = {
                "file": (video_file.name, video_file.getvalue(), video_file.type)
            }
            # question_id는 form-data로 전송
            data = {
                "question_id": str(question_id) 
            }

            upload_res = requests.post(
                f"{API_BASE}/api/v1/answer/upload",
                headers=headers, # Authorization 헤더 포함
                files=files,
                data=data,
                timeout=300 # 업로드는 시간이 걸릴 수 있음
            )

            if upload_res.status_code != 200:
                status_ui.update(label="❌ 영상 업로드 실패", state="error")
                st.error(f"업로드 오류: {upload_res.text}")
                st.stop()

            answer_data = upload_res.json()
            answer_id = answer_data.get("answer_id")
            status_ui.write(f"✅ 영상 업로드 완료 (Answer ID: {answer_id})")


            # =========================
            # 4단계: AI 분석 요청 (백그라운드)
            # =========================
            status_ui.write("4️⃣ AI 분석을 요청하고 있습니다...")

            analyze_res = requests.post(
                f"{API_BASE}/api/v1/analysis/session/{session_id}",
                headers=headers,
                timeout=10
            )

            if analyze_res.status_code != 200:
                status_ui.update(label="❌ 분석 요청 실패", state="error")
                st.error(f"분석 요청 오류: {analyze_res.text}")
                st.stop()

            # 모든 과정 성공
            status_ui.update(label="🎉 모든 요청이 완료되었습니다!", state="complete", expanded=False)
            
            st.success("분석이 시작되었습니다! '리포트' 페이지에서 결과를 확인하세요.")
            
            # 리포트 페이지로 이동 버튼
            if st.button("📊 결과 리포트 보러가기"):
                st.switch_page("pages/6_📊_리포트.py")

        except Exception as e:
            status_ui.update(label="⚠️ 시스템 오류", state="error")
            st.error(f"진행 중 오류 발생: {str(e)}")