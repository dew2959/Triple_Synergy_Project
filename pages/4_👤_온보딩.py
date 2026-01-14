"""
온보딩 이력서 입력 페이지 
"""
import streamlit as st
import requests

# 1. 상수 정의 (가장 상단으로 이동)
API_BASE = "http://localhost:8000"

# =====================================================
# 로그인 체크
# =====================================================
if not st.session_state.get('token'):
    st.warning("로그인이 필요합니다.")
    if st.button("로그인 페이지로 이동"):
        st.switch_page("pages/3_🔐_로그인.py")
    st.stop()


# =====================================================
# 세션 상태 초기화
# =====================================================
if "resume_data" not in st.session_state:
    st.session_state.resume_data = None

if "writing" not in st.session_state:
    st.session_state.writing = False

headers = {
    "Authorization": f"Bearer {st.session_state.token}"
}

# -------------------------------------------------
# 이력서 목록 불러오기
# -------------------------------------------------
def fetch_resumes():
    try:
        res = requests.get(f"{API_BASE}/api/v1/resume/", headers=headers)
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return []

# -------------------------------------------------
# 페이지 타이틀
# -------------------------------------------------
st.title("👤 이력서 온보딩")


# =====================================================
# 1️⃣ 기존 이력서 목록
# =====================================================
st.subheader("📄 내가 작성한 이력서")

resumes = fetch_resumes()

if resumes:
    for idx, r in enumerate(resumes):
        with st.container(border=True):
            st.write(f"**🎯 직무:** {r.get('job_title')}")
            st.write(f"**🏢 회사:** {r.get('target_company', '미입력')}")
            st.write(f"**📧 이메일:** {r.get('email')}")

            if st.button("📖 이력서 보기", key=f"view_{idx}"):
                st.session_state.resume_data = r
                st.session_state.writing = True
else:
    st.info("아직 작성된 이력서가 없습니다.")

st.divider()


# =====================================================
# 2️⃣ 이력서 상세 보기
# =====================================================
if "mode" not in st.session_state:
    st.session_state.mode = "list"   # list | view | edit | write

if "resumes" not in st.session_state:
    st.session_state.resumes = []

if "resume_data" not in st.session_state:
    st.session_state.resume_data = None


# =========================================================
# 기본 이력서 구조 (백엔드 입력 구조와 동일)
# =========================================================
def empty_resume():
    return {
        "name": "",
        "email": "",
        "job_title": "",
        "target_company": "",
        "education": [],
        "experience": [],
        "projects": [],
        "awards": [],
        "certifications": [],
        "skills": [],
        "introduction": "",
    }


# =========================================================
# 이력서 상세 보기 (읽기 전용)
# =========================================================
def render_resume_detail(data):
    st.subheader("📄 이력서 상세 보기")

    st.markdown(f"### 👤 이름\n{data['name']}")
    st.markdown(f"### 📧 이메일\n{data['email']}")
    st.markdown(f"### 🎯 지원 직무\n{data['job_title']}")
    st.markdown(f"### 🏢 지원 회사\n{data['target_company']}")

    st.divider()

    st.markdown("### 🎓 학력")
    for e in data["education"]:
        st.markdown(f"- **{e['school']} / {e['major']} ({e['degree']})**")

    st.markdown("### 💼 경력")
    for e in data["experience"]:
        st.markdown(f"- **{e['company']} – {e['position']}**")

    st.markdown("### 🚀 프로젝트")
    for p in data["projects"]:
        st.markdown(f"- **{p['name']}**: {p['description']}")

    st.markdown("### 🏆 수상")
    for a in data["awards"]:
        st.markdown(f"- {a['name']} ({a['organization']})")

    st.markdown("### 📜 자격증")
    for c in data["certifications"]:
        st.markdown(f"- {c['name']} ({c['organization']})")

    st.markdown("### 🛠 기술 스택")
    st.write(", ".join(data["skills"]))

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅ 목록으로"):
            st.session_state.mode = "list"
            st.session_state.resume_data = None
            st.rerun()

    with col2:
        if st.button("✏️ 수정하기"):
            st.session_state.mode = "edit"
            st.rerun()

# =====================================================
# 3️⃣ 새 이력서 작성 (전체 탭)
# =====================================================

def resume_form(data, save_callback):
    tabs = st.tabs([
        "기본 정보", "학력", "경력", "프로젝트",
        "수상", "자격증", "기술", "자기소개"
    ])

    with tabs[0]:
        data["name"] = st.text_input("이름", data["name"])
        data["email"] = st.text_input("이메일", data["email"])
        data["job_title"] = st.text_input("지원 직무", data["job_title"])
        data["target_company"] = st.text_input("지원 회사", data["target_company"])

    with tabs[1]:
        if st.button("➕ 학력 추가"):
            data["education"].append({"school": "", "major": "", "degree": ""})
        for i, edu in enumerate(data["education"]):
            st.text_input("학교", key=f"edu_s_{i}", value=edu["school"])
            st.text_input("전공", key=f"edu_m_{i}", value=edu["major"])
            st.text_input("학위", key=f"edu_d_{i}", value=edu["degree"])

    with tabs[2]:
        if st.button("➕ 경력 추가"):
            data["experience"].append({"company": "", "position": ""})
        for i, exp in enumerate(data["experience"]):
            st.text_input("회사", key=f"exp_c_{i}", value=exp["company"])
            st.text_input("직무", key=f"exp_p_{i}", value=exp["position"])

    with tabs[3]:
        if st.button("➕ 프로젝트 추가"):
            data["projects"].append({"name": "", "description": ""})
        for i, p in enumerate(data["projects"]):
            st.text_input("프로젝트명", key=f"pr_n_{i}", value=p["name"])
            st.text_area("설명", key=f"pr_d_{i}", value=p["description"])

    with tabs[4]:
        if st.button("➕ 수상 추가"):
            data["awards"].append({"name": "", "organization": ""})
        for i, a in enumerate(data["awards"]):
            st.text_input("수상명", key=f"a_n_{i}", value=a["name"])
            st.text_input("기관", key=f"a_o_{i}", value=a["organization"])

    with tabs[5]:
        if st.button("➕ 자격증 추가"):
            data["certifications"].append({"name": "", "organization": ""})
        for i, c in enumerate(data["certifications"]):
            st.text_input("자격증명", key=f"c_n_{i}", value=c["name"])
            st.text_input("기관", key=f"c_o_{i}", value=c["organization"])

    with tabs[6]:
        skills = st.text_input("기술 스택 (콤마로 구분)", ", ".join(data["skills"]))
        data["skills"] = [s.strip() for s in skills.split(",") if s.strip()]

    with tabs[7]:
        data["introduction"] = st.text_area("자기소개", data["introduction"])

    st.divider()
    if st.button("💾 저장"):
        save_callback(data)


# =========================================================
# 메인 화면
# =========================================================
st.title("🧭 이력서 온보딩")

# -------------------------
# 리스트 화면
# -------------------------
if st.session_state.mode == "list":
    st.subheader("📁 내 이력서")

    if st.button("➕ 새 이력서 작성"):
        st.session_state.resume_data = empty_resume()
        st.session_state.mode = "write"
        st.rerun()

    for idx, r in enumerate(st.session_state.resumes):
        with st.container(border=True):
            st.write(f"**{r['name']} / {r['job_title']}**")
            col1, col2 = st.columns(2)

            with col1:
                if st.button("📖 상세 보기", key=f"view_{idx}"):
                    st.session_state.resume_data = r
                    st.session_state.mode = "view"
                    st.rerun()

            with col2:
                if st.button("✏️ 수정", key=f"edit_{idx}"):
                    st.session_state.resume_data = r
                    st.session_state.mode = "edit"
                    st.rerun()

# -------------------------
# 상세 보기
# -------------------------
elif st.session_state.mode == "view":
    render_resume_detail(st.session_state.resume_data)

# -------------------------
# 작성 / 수정
# -------------------------
elif st.session_state.mode in ("write", "edit"):
    def save_resume(data):
        if st.session_state.mode == "write":
            st.session_state.resumes.append(data)
        st.session_state.mode = "list"
        st.session_state.resume_data = None
        st.success("이력서가 저장되었습니다.")
        st.rerun()

    resume_form(st.session_state.resume_data, save_resume)




# 사이드바 팁
st.sidebar.info("💡 모든 항목을 채울 필요는 없지만, **지원 직무**는 AI 면접 질문 생성을 위해 꼭 필요합니다!")