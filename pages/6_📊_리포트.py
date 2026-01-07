"""
결과 리포트 페이지
"""
import streamlit as st
from utils.api_client import report_api

# 로그인 체크
if not st.session_state.get('user'):
    st.warning("로그인이 필요합니다.")
    if st.button("로그인 페이지로 이동"):
        st.switch_page("pages/3_🔐_로그인.py")
    st.stop()

st.title("📊 면접 결과 리포트")

# 세션 ID 입력 (나중에 세션 목록에서 선택하도록 변경 가능)
session_id = st.number_input("세션 ID", min_value=1, value=1, step=1)

if st.button("리포트 조회", type="primary"):
    with st.spinner("리포트를 불러오는 중..."):
        try:
            report = report_api.get_report(session_id)
            display_report(report)
        except Exception as e:
            st.error(f"리포트를 불러올 수 없습니다: {str(e)}")

def display_report(report):
    """리포트 표시"""
    
    # 종합 평가
    st.markdown("---")
    st.markdown("## 종합 평가")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown(f"# {report['total_score']}점")
    
    with col2:
        st.markdown(f"### {report['summary_headline']}")
        st.markdown(report['overall_feedback'])
    
    # 종합 분석 리포트
    st.markdown("---")
    st.markdown("## 종합 분석 리포트")
    
    st.markdown(report['overall_feedback'])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 주요 강점")
        if report.get('visual_points', {}).get('strengths'):
            for strength in report['visual_points']['strengths']:
                st.markdown(f"✅ {strength}")
        if report.get('voice_points', {}).get('strengths'):
            for strength in report['voice_points']['strengths']:
                st.markdown(f"✅ {strength}")
        if report.get('content_points', {}).get('strengths'):
            for strength in report['content_points']['strengths']:
                st.markdown(f"✅ {strength}")
    
    with col2:
        st.markdown("### 개선 제안")
        if report.get('visual_points', {}).get('weaknesses'):
            for weakness in report['visual_points']['weaknesses']:
                st.markdown(f"⚠️ {weakness}")
        if report.get('voice_points', {}).get('weaknesses'):
            for weakness in report['voice_points']['weaknesses']:
                st.markdown(f"⚠️ {weakness}")
        if report.get('content_points', {}).get('weaknesses'):
            for weakness in report['content_points']['weaknesses']:
                st.markdown(f"⚠️ {weakness}")
    
    # 모듈별 점수
    st.markdown("---")
    st.markdown("## 모듈별 점수")
    
    module_col1, module_col2, module_col3 = st.columns(3)
    
    with module_col1:
        st.markdown("### 😊 표정 분석")
        visual_score = report['visual']['avg_score']
        st.metric("점수", f"{visual_score}점")
        st.progress(visual_score / 100)
        if report['visual'].get('summary'):
            st.markdown(report['visual']['summary'])
    
    with module_col2:
        st.markdown("### 🎤 음성 분석")
        voice_score = report['voice']['avg_score']
        st.metric("점수", f"{voice_score}점")
        st.progress(voice_score / 100)
        if report['voice'].get('summary'):
            st.markdown(report['voice']['summary'])
    
    with module_col3:
        st.markdown("### 💬 답변 내용")
        content_score = report['content']['avg_score']
        st.metric("점수", f"{content_score}점")
        st.progress(content_score / 100)
        if report['content'].get('summary'):
            st.markdown(report['content']['summary'])
    
    # 질문별 상세 분석 (있는 경우)
    if report.get('questions'):
        st.markdown("---")
        st.markdown("## 질문별 상세 분석")
        
        for idx, question in enumerate(report['questions'], 1):
            with st.expander(f"질문 {idx}: {question['question']}"):
                st.markdown(f"**답변:** {question['answer']}")
                
                q_col1, q_col2, q_col3 = st.columns(3)
                
                with q_col1:
                    st.markdown("#### 😊 표정 분석")
                    st.metric("점수", f"{question['visual_score']}점")
                    st.markdown(question['visual_feedback']['summary'])
                    
                    if question['visual_feedback'].get('good_points'):
                        st.markdown("**잘한 점:**")
                        for point in question['visual_feedback']['good_points']:
                            st.markdown(f"- ✅ {point}")
                    
                    # bad_points 또는 improvement_points 지원
                    improvement_points = question['visual_feedback'].get('improvement_points') or question['visual_feedback'].get('bad_points', [])
                    if improvement_points:
                        st.markdown("**개선할 점:**")
                        for point in improvement_points:
                            st.markdown(f"- ⚠️ {point}")
                
                with q_col2:
                    st.markdown("#### 🎤 음성 분석")
                    st.metric("점수", f"{question['voice_score']}점")
                    st.markdown(question['voice_feedback']['summary'])
                    
                    if question['voice_feedback'].get('good_points'):
                        st.markdown("**잘한 점:**")
                        for point in question['voice_feedback']['good_points']:
                            st.markdown(f"- ✅ {point}")
                    
                    # bad_points 또는 improvement_points 지원
                    improvement_points = question['voice_feedback'].get('improvement_points') or question['voice_feedback'].get('bad_points', [])
                    if improvement_points:
                        st.markdown("**개선할 점:**")
                        for point in improvement_points:
                            st.markdown(f"- ⚠️ {point}")
                
                with q_col3:
                    st.markdown("#### 💬 답변 내용")
                    st.metric("점수", f"{question['content_score']}점")
                    st.markdown(question['content_feedback']['summary'])
                    
                    if question['content_feedback'].get('good_points'):
                        st.markdown("**잘한 점:**")
                        for point in question['content_feedback']['good_points']:
                            st.markdown(f"- ✅ {point}")
                    
                    # bad_points 또는 improvement_points 지원
                    improvement_points = question['content_feedback'].get('improvement_points') or question['content_feedback'].get('bad_points', [])
                    if improvement_points:
                        st.markdown("**개선할 점:**")
                        for point in improvement_points:
                            st.markdown(f"- ⚠️ {point}")
    
    # 액션 플랜
    if report.get('action_plans'):
        st.markdown("---")
        st.markdown("## 다음 면접을 위한 액션 플랜")
        st.markdown("이번 분석 결과를 바탕으로 다음 면접을 더 잘 준비해보세요")
        
        for idx, plan in enumerate(report['action_plans'], 1):
            with st.container():
                st.markdown(f"### {idx}. {plan['title']}")
                st.markdown(plan['description'])
                st.markdown("---")
