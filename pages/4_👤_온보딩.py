import streamlit as st
from utils.api_client import resume_api  # resume_api 불러오기
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="이력서 관리", layout="wide")

# 2. 로그인 체크
if not st.session_state.get('token'):
    st.warning("로그인이 필요합니다.")
    if st.button("로그인 페이지로 이동"):
        st.switch_page("pages/3_🔐_로그인.py")
    st.stop()

# 3. 세션 상태 초기화
if "mode" not in st.session_state:
    st.session_state.mode = "list"  # list | write | view
if "selected_resume" not in st.session_state:
    st.session_state.selected_resume = None
if "resume_form_data" not in st.session_state:
    st.session_state.resume_form_data = {}

# 초기 입력 폼 데이터 스켈레톤
def get_empty_resume():
    user_info = st.session_state.get('user', {})
    return {
        'name': user_info.get('name', ''),
        'email': user_info.get('email', ''),
        'job_title': '',
        'target_company': '',
        'education': [],
        'experience': [],
        'projects': [],
        'awards': [],
        'certifications': [],
        'skills_text': '',
        'introduction': ''
    }

# --- 로직 함수들 ---
def handle_write_new():
    st.session_state.resume_form_data = get_empty_resume()
    st.session_state.mode = "write"
    st.rerun()

def handle_view_detail(resume):
    st.session_state.selected_resume = resume
    st.session_state.mode = "view"
    st.rerun()

def handle_back_to_list():
    st.session_state.mode = "list"
    st.session_state.selected_resume = None
    st.rerun()

# --- 화면 렌더링 ---

# [MODE: LIST] 이력서 목록 보기
if st.session_state.mode == "list":
    st.title("👤 이력서 관리")
    
    # 상단: 기존 이력서 목록
    st.subheader("내 이력서 목록")
    try:
        # resume_api를 통한 목록 조회 (get_resumes 함수가 있다고 가정)
        resumes = resume_api.get_resumes(st.session_state.token)
        
        if not resumes:
            st.info("작성된 이력서가 없습니다. 아래 버튼을 눌러 첫 이력서를 작성해보세요!")
        else:
            for res in resumes:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([4, 2, 1])
                    with col1:
                        st.markdown(f"**[{res.get('job_title')}]** {res.get('target_company', '일반 이력서')}")
                        st.caption(f"최종 수정일: {res.get('updated_at', '정보 없음')}")
                    with col3:
                        if st.button("상세보기", key=f"btn_view_{res.get('id')}"):
                            handle_view_detail(res)
    except Exception as e:
        st.error(f"이력서를 불러오는 중 오류가 발생했습니다: {e}")

    st.divider()
    
    # 하단: 새 이력서 작성하기 버튼
    if st.button("➕ 새 이력서 작성하기", use_container_width=True, type="primary"):
        handle_write_new()

# [MODE: VIEW] 이력서 상세보기
elif st.session_state.mode == "view":
    res = st.session_state.selected_resume
    st.title(f"📄 {res.get('job_title')} - 상세 보기")
    
    if st.button("← 목록으로 돌아가기"):
        handle_back_to_list()
        
    with st.expander("기본 정보", expanded=True):
        st.write(f"**지원 직무:** {res.get('job_title')}")
        st.write(f"**지원 회사:** {res.get('target_company')}")
    
    if res.get('education'):
        with st.expander("학력"):
            for edu in res['education']:
                st.write(f"**{edu['school']}** ({edu['status']}) | {edu['major']}")
                
    # ... 기타 항목(경력, 프로젝트 등) 표시 로직 ...
    st.json(res) # 전체 데이터를 JSON 형태로 우선 확인

# [MODE: WRITE] 이력서 작성하기 (기존 코드 통합)
elif st.session_state.mode == "write":
    st.title("✍️ 새 이력서 작성")
    if st.button("← 작성 취소"):
        handle_back_to_list()

    # 탭 구성
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📋 기본 정보", "🎓 학력", "💼 경력", "🚀 프로젝트", "🏆 수상", "📜 자격증"
    ])

    # Tab 1: 기본 정보
    with tab1:
        st.session_state.resume_form_data['job_title'] = st.text_input(
            "지원 직무*", value=st.session_state.resume_form_data.get('job_title', '')
        )
        st.session_state.resume_form_data['target_company'] = st.text_input(
            "지원 회사", value=st.session_state.resume_form_data.get('target_company', '')
        )

    # Tab 2: 학력 (동적 리스트 로직)
    with tab2:
        if st.button("➕ 학력 추가"):
            st.session_state.resume_form_data['education'].append({'school': '', 'major': '', 'degree': '학사', 'start_date': '', 'end_date': '', 'status': '졸업'})
            st.rerun()
        
        for i, edu in enumerate(st.session_state.resume_form_data['education']):
            with st.expander(f"학력 {i+1}", expanded=True):
                edu['school'] = st.text_input("학교명", value=edu['school'], key=f"edu_sch_{i}")
                edu['major'] = st.text_input("전공", value=edu['major'], key=f"edu_maj_{i}")
                if st.button(f"삭제", key=f"del_edu_{i}"):
                    st.session_state.resume_form_data['education'].pop(i)
                    st.rerun()

    # ... Tab 3~6 (경력, 프로젝트 등 동일 패턴으로 구현) ...

    st.divider()
    
    # 최종 저장 버튼
    if st.button("💾 이력서 최종 저장", use_container_width=True, type="primary"):
        if not st.session_state.resume_form_data.get('job_title'):
            st.error("지원 직무는 필수입니다.")
        else:
            try:
                # resume_api를 통한 POST 요청
                # skills_text 처리 등 전처리 포함
                payload = st.session_state.resume_form_data
                response = resume_api.create_resume(st.session_state.token, payload)
                
                if response:
                    st.success("✅ DB에 이력서가 성공적으로 저장되었습니다!")
                    st.balloons()
                    st.session_state.mode = "list"
                    st.rerun()
            except Exception as e:
                st.error(f"저장 중 오류 발생: {e}")