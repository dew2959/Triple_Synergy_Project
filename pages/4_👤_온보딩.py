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
if "resume_data" not in st.session_state:
    st.session_state.resume_data = {}

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
    st.session_state.resume_data = get_empty_resume()
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
                        if st.button("상세보기", key=f"btn_view_{res['resume_id']}"):
                            handle_view_detail(res)
    except Exception as e:
        st.error(f"이력서를 불러오는 중 오류가 발생했습니다: {e}")

    st.divider()
    
    # 하단: 새 이력서 작성하기 버튼
    if st.button("➕ 새 이력서 작성하기", use_container_width=True, type="primary"):
        handle_write_new()

# [MODE: VIEW] 이력서 상세보기
elif st.session_state.mode == "view":
    res = st.session_state.get('selected_resume', {})
    st.title(f"📄 {res.get('job_title')} - 상세 보기")
    
    if st.button("← 목록으로 돌아가기"):
        handle_back_to_list()

    st.markdown("---")  # 구분선
        
    # 기본 정보
    st.subheader("기본 정보")
    st.write(f"**지원 직무:** {res.get('job_title', '정보 없음')}")
    st.write(f"**지원 회사:** {res.get('target_company', '정보 없음')}")

    st.markdown("---")

    # 학력
    st.subheader("학력")
    if res.get('education'):
        for edu in res['education']:
            st.write(f"- **{edu.get('school', '학교명 없음')}** ({edu.get('status', '-')}) | {edu.get('major', '-')}")
    else:
        st.write("정보 없음")

    st.markdown("---")

    # 경력
    st.subheader("경력")
    if res.get('experience'):
        for exp in res['experience']:
            st.write(f"- **{exp.get('company', '회사명 없음')}** - {exp.get('position', '-')}")
    else:
        st.write("정보 없음")

    st.markdown("---")

    # 프로젝트
    st.subheader("프로젝트")
    if res.get('projects'):
        for proj in res['projects']:
            st.write(f"- **{proj.get('name', '프로젝트명 없음')}** - {proj.get('role', '-')}")
            if proj.get('description'):
                st.write(f"  > {proj['description']}")
    else:
        st.write("정보 없음")

    st.markdown("---")

    # 수상 내역
    st.subheader("수상 내역")
    if res.get('awards'):
        for award in res['awards']:
            st.write(f"- **{award.get('title', '수상명 없음')}** - {award.get('organization', '-')}")
    else:
        st.write("정보 없음")

    st.markdown("---")

    # 자격증
    st.subheader("자격증")
    if res.get('certifications'):
        for cert in res['certifications']:
            st.write(f"- **{cert.get('name', '자격증명 없음')}** - {cert.get('organization', '-')}")
    else:
        st.write("정보 없음")

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
        st.session_state.resume_data['job_title'] = st.text_input(
            "지원 직무*", value=st.session_state.resume_data.get('job_title', '')
        )
        st.session_state.resume_data['target_company'] = st.text_input(
            "지원 회사", value=st.session_state.resume_data.get('target_company', '')
        )

    # Tab 2: 학력 (동적 리스트 로직)
    with tab2:
        if st.button("➕ 학력 추가"):
            st.session_state.resume_data['education'].append({'school': '', 'major': '', 'degree': '학사', 'start_date': '', 'end_date': '', 'status': '졸업'})
            st.rerun()
        
        for i, edu in enumerate(st.session_state.resume_data['education']):
            with st.expander(f"학력 {i+1}", expanded=True):

                edu['school'] = st.text_input("학교명*", value=edu['school'], key=f"edu_school_{i}")
                edu['major'] = st.text_input("전공*", value=edu['major'], key=f"edu_major_{i}")
                edu['degree'] = st.selectbox("학위*", ["학사", "석사", "박사", "전문학사"],
                                           index=["학사", "석사", "박사", "전문학사"].index(edu['degree']) if edu['degree'] in ["학사", "석사", "박사", "전문학사"] else 0,
                                           key=f"edu_degree_{i}")
                edu['start_date'] = st.text_input("입학일*", value=edu['start_date'], placeholder="YYYY-MM", key=f"edu_start_{i}")
                edu['end_date'] = st.text_input("졸업일", value=edu['end_date'], placeholder="YYYY-MM", key=f"edu_end_{i}")
                edu['status'] = st.selectbox("상태*", ["졸업", "재학", "휴학", "수료"],
                                           index=["졸업", "재학", "휴학", "수료"].index(edu['status']) if edu['status'] in ["졸업", "재학", "휴학", "수료"] else 0,
                                           key=f"edu_status_{i}")

                if st.button(f"삭제", key=f"del_edu_{i}"):
                    st.session_state.resume_data['education'].pop(i)
                    st.rerun()


    # Tab 3: 경력 
    with tab3:
        if st.button("➕ 경력 추가"):
            st.session_state.resume_data['experience'].append({
                'company': '', 'position': '', 'department': '', 'start_date': '', 'end_date': '', 'description': '', 'achievements': '' })

        for i, exp in enumerate(st.session_state.resume_data['experience']):
            with st.expander(f"경력 {i+1}", expanded=True):
                exp['company'] = st.text_input("회사명*", value=exp['company'], key=f"exp_company_{i}")
                exp['position'] = st.text_input("직책*", value=exp['position'], key=f"exp_position_{i}")
                exp['department'] = st.text_input("부서", value=exp['department'], key=f"exp_dept_{i}")
                exp['start_date'] = st.text_input("입사일*", value=exp['start_date'], placeholder="YYYY-MM", key=f"exp_start_{i}")
                exp['end_date'] = st.text_input("퇴사일", value=exp['end_date'], placeholder="YYYY-MM", key=f"exp_end_{i}")
                exp['description'] = st.text_area("주요 업무*", value=exp['description'], key=f"exp_desc_{i}", height=100)
                exp['achievements'] = st.text_area("주요 성과", value=exp['achievements'], key=f"exp_ach_{i}", height=100)

                if st.button(f"🗑️ 삭제", key=f"del_exp_{i}"):
                    st.session_state.resume_data['experience'].pop(i)
                    st.rerun()


    # Tab 4: 프로젝트 
    with tab4:
        if st.button("➕ 프로젝트 추가"):
            st.session_state.resume_data['projects'].append({
                'name': '', 'role': '', 'start_date': '', 'end_date': '', 'description': '', 'technologies': '' , 'achievements': ''})

        for i, proj in enumerate(st.session_state.resume_data['projects']):
            with st.expander(f"프로젝트 {i+1}", expanded=True):
                proj['name'] = st.text_input("프로젝트명*", value=proj['name'], key=f"proj_name_{i}")
                proj['role'] = st.text_input("역할*", value=proj['role'], key=f"proj_role_{i}")
                proj['start_date'] = st.text_input("시작일*", value=proj['start_date'], placeholder="YYYY-MM", key=f"proj_start_{i}")
                proj['end_date'] = st.text_input("종료일", value=proj['end_date'], placeholder="YYYY-MM", key=f"proj_end_{i}")
                proj['description'] = st.text_area("프로젝트 설명*", value=proj['description'], key=f"proj_desc_{i}", height=100)
                proj['technologies'] = st.text_input("사용 기술", value=proj['technologies'], key=f"proj_tech_{i}")
                proj['achievements'] = st.text_area("주요 성과", value=proj['achievements'], key=f"proj_ach_{i}", height=100)

                if st.button(f"🗑️ 삭제", key=f"del_proj_{i}"):
                    st.session_state.resume_data['projects'].pop(i)
                    st.rerun()

    # Tab 5: 수상
    with tab5:
        if st.button("➕ 수상 내역 추가"):
            st.session_state.resume_data['awards'].append({
                'title': '', 'organization': '', 'date': '', 'description': '' })

        for i, award in enumerate(st.session_state.resume_data['awards']):
            with st.expander(f"수상 {i+1}", expanded=True):
                award['title'] = st.text_input("수상명*", value=award['title'], key=f"award_title_{i}")
                award['organization'] = st.text_input("수여기관", value=award['organization'], key=f"award_organization_{i}")
                award['date'] = st.text_input("수상일", value=award['date'], placeholder="YYYY-MM", key=f"award_date_{i}")
                award['description'] = st.text_area("설명", value=award['description'], key=f"award_desc_{i}", height=100)

                if st.button(f"🗑️ 삭제", key=f"del_award_{i}"):
                    st.session_state.resume_data['awards'].pop(i)
                    st.rerun() 


    # Tab 6: 자격증
    with tab6:
        if st.button("➕ 자격증 추가"):
            st.session_state.resume_data['certifications'].append({
                'name': '', 'organization': '', 'date': '', 'valid_until': '', 'description': '' })
            
        for i, cert in enumerate(st.session_state.resume_data['certifications']):
            with st.expander(f"자격증 {i+1}", expanded=True):
                cert['name'] = st.text_input("자격증명*", value=cert['name'], key=f"cert_name_{i}")
                cert['organization'] = st.text_input("발급기관", value=cert['organization'], key=f"cert_org_{i}")
                cert['date'] = st.text_input("취득일", value=cert['date'], placeholder="YYYY-MM", key=f"cert_date_{i}")
                cert['valid_until'] = st.text_input("유효기간", value=cert['valid_until'], placeholder="YYYY-MM", key=f"cert_valid_{i}")
                cert['description'] = st.text_area("설명", value=cert['description'], key=f"cert_desc_{i}", height=100)

                if st.button(f"🗑️ 삭제", key=f"del_cert_{i}"):
                    st.session_state.resume_data['certifications'].pop(i)
                    st.rerun()

    st.divider()
    
    # 최종 저장 버튼
    if st.button("💾 이력서 저장", use_container_width=True, type="primary"):
        if not st.session_state.resume_data.get('job_title'):
            st.error("지원 직무는 필수입니다.")
        else:
            try:
                # resume_api를 통한 POST 요청
                # skills_text 처리 등 전처리 포함
                payload = st.session_state.resume_data
                response = resume_api.create_resume(st.session_state.token, payload)
                
                if response:
                    st.success("✅ DB에 이력서가 성공적으로 저장되었습니다!")
                    st.balloons()
                    st.session_state.mode = "list"
                    st.rerun()
            except Exception as e:
                st.error(f"저장 중 오류 발생: {e}")