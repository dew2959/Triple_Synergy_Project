"""
온보딩 프로필 설정 페이지 - 이력서 입력
"""
import streamlit as st
import requests
import json
from datetime import datetime

# 로그인 체크
if not st.session_state.get('user'):
    st.warning("로그인이 필요합니다.")
    if st.button("로그인 페이지로 이동"):
        st.switch_page("pages/3_🔐_로그인.py")
    st.stop()

st.title("👤 이력서 작성")
st.markdown("면접 준비를 위한 상세 이력서 정보를 입력해주세요")

# API 기본 URL
API_BASE = "http://localhost:8000"

# 세션 상태 초기화
if 'resume_data' not in st.session_state:
    st.session_state.resume_data = {}

# 탭으로 섹션 분리
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📋 기본 정보", "🎓 학력", "💼 경력", "🚀 프로젝트", "🏆 수상", "📜 자격증", "💾 저장"
])

# 기본 정보 탭
with tab1:
    st.header("📋 기본 정보")
    
    name = st.text_input("이름*", value=st.session_state.resume_data.get('name', ''))
    email = st.text_input("이메일*", value=st.session_state.resume_data.get('email', ''))
    phone = st.text_input("연락처", value=st.session_state.resume_data.get('phone', ''))
    birth_date = st.text_input("생년월일", placeholder="YYYY-MM-DD", 
                              value=st.session_state.resume_data.get('birth_date', ''))
    
    skills = st.text_area("기술 스택", placeholder="사용 가능한 기술을 쉼표로 구분하여 입력하세요 (예: Python, JavaScript, React)",
                         value=st.session_state.resume_data.get('skills_text', ''))
    
    introduction = st.text_area("자기소개", placeholder="자신을 소개하는 내용을 입력하세요",
                               value=st.session_state.resume_data.get('introduction', ''), height=150)
    
    # 데이터 저장
    st.session_state.resume_data.update({
        'name': name,
        'email': email,
        'phone': phone,
        'birth_date': birth_date,
        'skills_text': skills,
        'introduction': introduction
    })

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

# 저장 탭
with tab7:
    st.header("💾 이력서 저장")
    
    st.markdown("### 입력 내용 확인")
    
    # 기본 정보 요약
    st.subheader("📋 기본 정보")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**이름:** {st.session_state.resume_data.get('name', '')}")
        st.write(f"**이메일:** {st.session_state.resume_data.get('email', '')}")
    with col2:
        st.write(f"**연락처:** {st.session_state.resume_data.get('phone', '')}")
        st.write(f"**생년월일:** {st.session_state.resume_data.get('birth_date', '')}")
    with col3:
        skills_list = [skill.strip() for skill in st.session_state.resume_data.get('skills_text', '').split(',') if skill.strip()]
        st.write(f"**기술 스택:** {', '.join(skills_list) if skills_list else '없음'}")
    
    # 항목 수 요약
    st.subheader("📊 입력 항목 요약")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("학력", len(st.session_state.resume_data.get('education', [])))
    with col2:
        st.metric("경력", len(st.session_state.resume_data.get('experience', [])))
    with col3:
        st.metric("프로젝트", len(st.session_state.resume_data.get('projects', [])))
    with col4:
        st.metric("수상", len(st.session_state.resume_data.get('awards', [])))
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ 임시 저장", use_container_width=True):
            st.info("임시 저장되었습니다. 계속 작성할 수 있습니다.")
    
    with col2:
        if st.button("💾 최종 저장", use_container_width=True, type="primary"):
            # 유효성 검사
            if not st.session_state.resume_data.get('name') or not st.session_state.resume_data.get('email'):
                st.error("이름과 이메일은 필수 항목입니다.")
                st.stop()
            
            # API 요청 데이터 준비
            resume_data = {
                "name": st.session_state.resume_data.get('name'),
                "email": st.session_state.resume_data.get('email'),
                "phone": st.session_state.resume_data.get('phone'),
                "birth_date": st.session_state.resume_data.get('birth_date'),
                "education": st.session_state.resume_data.get('education', []),
                "experience": st.session_state.resume_data.get('experience', []),
                "projects": [{
                    **proj,
                    "technologies": [tech.strip() for tech in proj.get('technologies', '').split(',') if tech.strip()]
                } for proj in st.session_state.resume_data.get('projects', [])],
                "awards": st.session_state.resume_data.get('awards', []),
                "certifications": st.session_state.resume_data.get('certifications', []),
                "skills": [skill.strip() for skill in st.session_state.resume_data.get('skills_text', '').split(',') if skill.strip()],
                "introduction": st.session_state.resume_data.get('introduction')
            }
            
            # API 호출
            try:
                headers = {"Authorization": f"Bearer {st.session_state.get('token')}"}
                response = requests.post(
                    f"{API_BASE}/api/v1/resume/",
                    json=resume_data,
                    headers=headers
                )
                
                if response.status_code == 201:
                    st.success("✅ 이력서가 성공적으로 저장되었습니다!")
                    st.session_state.resume_data = {}  # 데이터 초기화
                    if st.button("메인 페이지로 이동"):
                        st.switch_page("pages/1_🏠_랜딩.py")
                else:
                    st.error(f"저장 실패: {response.text}")
                    
            except requests.exceptions.RequestException as e:
                st.error(f"API 연결 오류: {str(e)}")
                st.info("서버가 실행 중인지 확인해주세요 (localhost:8000)")

st.sidebar.markdown("---")
st.sidebar.markdown("### 💡 팁")
st.sidebar.info("""
- 모든 항목은 필수가 아닙니다
- *표시는 필수 입력 항목입니다
- 임시 저장으로 작업 내용을 보관할 수 있습니다
- 최종 저장 후에는 수정이 가능합니다
""")
