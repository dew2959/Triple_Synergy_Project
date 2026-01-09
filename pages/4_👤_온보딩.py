"""
온보딩 프로필 설정 페이지 - 이력서 입력
"""
import streamlit as st
import requests
import json
from datetime import datetime

# 1. 상수 정의 (가장 상단으로 이동)
API_BASE = "http://localhost:8000"

# 로그인 체크
if not st.session_state.get('token'):
    st.warning("로그인이 필요합니다.")
    if st.button("로그인 페이지로 이동"):
        st.switch_page("pages/3_🔐_로그인.py")
    st.stop()

# 2. 백엔드에서 실시간으로 사용자 정보를 가져오는 함수
def fetch_user_data():
    try:
        headers = {"Authorization": f"Bearer {st.session_state.get('token')}"}
        response = requests.get(f"{API_BASE}/api/v1/auth/me", headers=headers)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"사용자 정보를 가져오는 중 오류 발생: {e}")
    return None

# 3. 사용자 정보 로드 로직
if 'user' not in st.session_state:
    st.session_state.user = {}

if not st.session_state.user.get('name'):
    with st.spinner("사용자 정보를 불러오는 중..."):
        user_data = fetch_user_data()
        if user_data:
            st.session_state.user.update(user_data)

user_info = st.session_state.get('user', {})
default_name = user_info.get('name', '')
default_email = user_info.get('email', '')

# 4. 세션 상태 초기화 (DB 필드에 맞춰 phone/birth_date 제거)
if 'resume_data' not in st.session_state:
    st.session_state.resume_data = {
        'name': default_name,
        'email': default_email,
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

st.title("👤 이력서 작성")
st.markdown("면접 준비를 위한 상세 이력서 정보를 입력해주세요")

# 탭으로 섹션 분리
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📋 기본 정보", "🎓 학력", "💼 경력", "🚀 프로젝트", "🏆 수상", "📜 자격증", "💾 저장"
])

# --- Tab 1: 기본 정보 ---
with tab1:
    st.header("📋 기본 및 지원 정보")
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.text_input("이름", value=default_name, disabled=True)
    with col_info2:
        st.text_input("이메일", value=default_email, disabled=True)
        
    st.divider()
    st.subheader("🎯 지원 목표")
    job_title = st.text_input("지원 직무*", 
                             placeholder="예: 백엔드 개발자, 서비스 기획자", 
                             value=st.session_state.resume_data.get('job_title', ''))
    target_company = st.text_input("지원 회사 (선택)", 
                                  placeholder="지원을 희망하는 회사명을 입력하세요", 
                                  value=st.session_state.resume_data.get('target_company', ''))
    
    # 실시간 세션 업데이트
    st.session_state.resume_data.update({
        'job_title': job_title,
        'target_company': target_company
    })

# --- Tab 2 ~ 6: 학력/경력/프로젝트/수상/자격증 (기존 코드 유지) ---
# 학력 탭
with tab2:

    st.header("🎓 학력")

   

    if 'education' not in st.session_state.resume_data:

        st.session_state.resume_data['education'] = []

   

    education_count = len(st.session_state.resume_data['education'])

   

    if st.button("➕ 학력 추가"):

        st.session_state.resume_data['education'].append({

            'school': '',

            'major': '',

            'degree': '',

            'start_date': '',

            'end_date': '',

            'status': ''

        })

   

    for i, edu in enumerate(st.session_state.resume_data['education']):

        with st.expander(f"학력 {i+1}"):

            col1, col2 = st.columns(2)

            with col1:

                edu['school'] = st.text_input("학교명*", value=edu['school'], key=f"edu_school_{i}")

                edu['major'] = st.text_input("전공*", value=edu['major'], key=f"edu_major_{i}")

                edu['degree'] = st.selectbox("학위*", ["학사", "석사", "박사", "전문학사"],

                                           index=["학사", "석사", "박사", "전문학사"].index(edu['degree']) if edu['degree'] in ["학사", "석사", "박사", "전문학사"] else 0,

                                           key=f"edu_degree_{i}")

            with col2:

                edu['start_date'] = st.text_input("입학일*", value=edu['start_date'],

                                                placeholder="YYYY-MM", key=f"edu_start_{i}")

                edu['end_date'] = st.text_input("졸업일", value=edu['end_date'],

                                              placeholder="YYYY-MM", key=f"edu_end_{i}")

                edu['status'] = st.selectbox("상태*", ["졸업", "재학", "휴학", "수료"],

                                           index=["졸업", "재학", "휴학", "수료"].index(edu['status']) if edu['status'] in ["졸업", "재학", "휴학", "수료"] else 0,

                                           key=f"edu_status_{i}")

           

            if st.button(f"🗑️ 삭제", key=f"del_edu_{i}"):

                st.session_state.resume_data['education'].pop(i)

                st.rerun()



# 경력 탭

with tab3:

    st.header("💼 경력")

   

    if 'experience' not in st.session_state.resume_data:

        st.session_state.resume_data['experience'] = []

   

    if st.button("➕ 경력 추가"):

        st.session_state.resume_data['experience'].append({

            'company': '',

            'position': '',

            'department': '',

            'start_date': '',

            'end_date': '',

            'description': '',

            'achievements': ''

        })

   

    for i, exp in enumerate(st.session_state.resume_data['experience']):

        with st.expander(f"경력 {i+1}"):

            col1, col2 = st.columns(2)

            with col1:

                exp['company'] = st.text_input("회사명*", value=exp['company'], key=f"exp_company_{i}")

                exp['position'] = st.text_input("직책*", value=exp['position'], key=f"exp_position_{i}")

                exp['department'] = st.text_input("부서", value=exp['department'], key=f"exp_dept_{i}")

            with col2:

                exp['start_date'] = st.text_input("입사일*", value=exp['start_date'],

                                                placeholder="YYYY-MM", key=f"exp_start_{i}")

                exp['end_date'] = st.text_input("퇴사일", value=exp['end_date'],

                                              placeholder="YYYY-MM", key=f"exp_end_{i}")

           

            exp['description'] = st.text_area("주요 업무*", value=exp['description'],

                                            key=f"exp_desc_{i}", height=100)

            exp['achievements'] = st.text_area("주요 성과", value=exp['achievements'],

                                             key=f"exp_ach_{i}", height=100)

           

            if st.button(f"🗑️ 삭제", key=f"del_exp_{i}"):

                st.session_state.resume_data['experience'].pop(i)

                st.rerun()



# 프로젝트 탭

with tab4:

    st.header("🚀 프로젝트 경험")

   

    if 'projects' not in st.session_state.resume_data:

        st.session_state.resume_data['projects'] = []

   

    if st.button("➕ 프로젝트 추가"):

        st.session_state.resume_data['projects'].append({

            'name': '',

            'role': '',

            'start_date': '',

            'end_date': '',

            'description': '',

            'technologies': '',

            'achievements': ''

        })

   

    for i, proj in enumerate(st.session_state.resume_data['projects']):

        with st.expander(f"프로젝트 {i+1}"):

            col1, col2 = st.columns(2)

            with col1:

                proj['name'] = st.text_input("프로젝트명*", value=proj['name'], key=f"proj_name_{i}")

                proj['role'] = st.text_input("역할*", value=proj['role'], key=f"proj_role_{i}")

                proj['start_date'] = st.text_input("시작일*", value=proj['start_date'],

                                                  placeholder="YYYY-MM", key=f"proj_start_{i}")

            with col2:

                proj['end_date'] = st.text_input("종료일", value=proj['end_date'],

                                               placeholder="YYYY-MM", key=f"proj_end_{i}")

                proj['technologies'] = st.text_input("사용 기술", value=proj['technologies'],

                                                   placeholder="쉼표로 구분", key=f"proj_tech_{i}")

           

            proj['description'] = st.text_area("프로젝트 설명*", value=proj['description'],

                                             key=f"proj_desc_{i}", height=100)

            proj['achievements'] = st.text_area("성과", value=proj['achievements'],

                                             key=f"proj_ach_{i}", height=100)

           

            if st.button(f"🗑️ 삭제", key=f"del_proj_{i}"):

                st.session_state.resume_data['projects'].pop(i)

                st.rerun()



# 수상 탭

with tab5:

    st.header("🏆 수상 경력")

   

    if 'awards' not in st.session_state.resume_data:

        st.session_state.resume_data['awards'] = []

   

    if st.button("➕ 수상 내역 추가"):

        st.session_state.resume_data['awards'].append({

            'name': '',

            'organization': '',

            'date': '',

            'description': ''

        })

   

    for i, award in enumerate(st.session_state.resume_data['awards']):

        with st.expander(f"수상 {i+1}"):

            col1, col2 = st.columns(2)

            with col1:

                award['name'] = st.text_input("수상명*", value=award['name'], key=f"award_name_{i}")

                award['organization'] = st.text_input("수여 기관*", value=award['organization'],

                                                    key=f"award_org_{i}")

            with col2:

                award['date'] = st.text_input("수상일*", value=award['date'],

                                           placeholder="YYYY-MM-DD", key=f"award_date_{i}")

           

            award['description'] = st.text_area("수상 내용", value=award['description'],

                                              key=f"award_desc_{i}", height=80)

           

            if st.button(f"🗑️ 삭제", key=f"del_award_{i}"):

                st.session_state.resume_data['awards'].pop(i)

                st.rerun()



# 자격증 탭

with tab6:

    st.header("📜 자격증/교육")

   

    if 'certifications' not in st.session_state.resume_data:

        st.session_state.resume_data['certifications'] = []

   

    if st.button("➕ 자격증/교육 추가"):

        st.session_state.resume_data['certifications'].append({

            'name': '',

            'organization': '',

            'date': '',

            'valid_until': '',

            'description': ''

        })

   

    for i, cert in enumerate(st.session_state.resume_data['certifications']):

        with st.expander(f"자격증/교육 {i+1}"):

            col1, col2 = st.columns(2)

            with col1:

                cert['name'] = st.text_input("자격증/교육명*", value=cert['name'], key=f"cert_name_{i}")

                cert['organization'] = st.text_input("발급 기관*", value=cert['organization'],

                                                   key=f"cert_org_{i}")

            with col2:

                cert['date'] = st.text_input("취득일*", value=cert['date'],

                                           placeholder="YYYY-MM-DD", key=f"cert_date_{i}")

                cert['valid_until'] = st.text_input("만료일", value=cert['valid_until'],

                                                  placeholder="YYYY-MM-DD", key=f"cert_valid_{i}")

           

            cert['description'] = st.text_area("설명", value=cert['description'],

                                              key=f"cert_desc_{i}", height=80)

           

            if st.button(f"🗑️ 삭제", key=f"del_cert_{i}"):

                st.session_state.resume_data['certifications'].pop(i)

                st.rerun()

# --- Tab 7: 저장 (최종 재구성) ---
with tab7:
    st.header("💾 이력서 저장")
    st.markdown("### 입력 내용 확인")
    
    # 요약 정보 표시
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**👤 이름:** {default_name}")
            st.write(f"**📧 이메일:** {default_email}")
        with c2:
            st.write(f"**🎯 직무:** {st.session_state.resume_data.get('job_title')}")
            st.write(f"**🏢 회사:** {st.session_state.resume_data.get('target_company', '미입력')}")
    
    # 항목 수 요약
    st.write("#### 📊 입력 항목 요약")
    col_m = st.columns(5)
    col_m[0].metric("학력", len(st.session_state.resume_data.get('education', [])))
    col_m[1].metric("경력", len(st.session_state.resume_data.get('experience', [])))
    col_m[2].metric("프로젝트", len(st.session_state.resume_data.get('projects', [])))
    col_m[3].metric("수상", len(st.session_state.resume_data.get('awards', [])))
    col_m[4].metric("자격증", len(st.session_state.resume_data.get('certifications', [])))
    
    st.divider()
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🗑️ 임시 저장", use_container_width=True):
            st.info("세션에 임시 저장되었습니다.")
    
    with col_btn2:
        if st.button("💾 최종 저장", use_container_width=True, type="primary"):
            if not st.session_state.resume_data.get('job_title'):
                st.error("지원 직무는 필수입니다.")
                st.stop()
            
            # 최종 페이로드 구성 (DB 스키마 resumes 테이블에 맞춰 구성)
            final_payload = {
                "name": default_name,
                "email": default_email,
                "job_title": st.session_state.resume_data.get('job_title'),
                "target_company": st.session_state.resume_data.get('target_company'),
                "education": st.session_state.resume_data.get('education', []),
                "experience": st.session_state.resume_data.get('experience', []),
                "projects": st.session_state.resume_data.get('projects', []),
                "awards": st.session_state.resume_data.get('awards', []),
                "certifications": st.session_state.resume_data.get('certifications', []),
                "skills": [s.strip() for s in st.session_state.resume_data.get('skills_text', '').split(',') if s.strip()],
                "introduction": st.session_state.resume_data.get('introduction', '')
            }
            
            try:
                headers = {"Authorization": f"Bearer {st.session_state.get('token')}"}
                # 엔드포인트를 복수형 /api/v1/resumes/ 로 권장
                response = requests.post(f"{API_BASE}/api/v1/resumes/", json=final_payload, headers=headers)
                
                if response.status_code in [200, 201]:
                    st.success("✅ 이력서가 성공적으로 저장되었습니다!")
                    st.balloons()
                    if st.button("메인으로 이동"):
                        st.switch_page("pages/1_🏠_랜딩.py")
                else:
                    st.error(f"저장 실패: {response.text}")
            except Exception as e:
                st.error(f"API 연결 오류: {str(e)}")

# 사이드바 팁
st.sidebar.info("💡 모든 항목을 채울 필요는 없지만, **지원 직무**는 AI 면접 질문 생성을 위해 꼭 필요합니다!")