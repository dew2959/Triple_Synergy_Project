import streamlit as st
from utils.api_client import session_api, report_api
from datetime import datetime
import pandas as pd

# 1. 로그인 체크
if not st.session_state.get('token'):
    st.warning("로그인이 필요합니다.")
    if st.button("로그인 페이지로 이동"):
        st.switch_page("pages/3_🔐_로그인.py")
    st.stop()

st.title("📊 면접 결과 리포트")

# 2. 세션 목록 불러오기
try:
    sessions = session_api.get_my_sessions(st.session_state.token)
except Exception as e:
    st.error(f"세션 목록을 불러오지 못했습니다: {e}")
    st.stop()

if not sessions:
    st.info("아직 진행한 면접이 없습니다. '면접 진행' 페이지에서 모의면접을 시작해보세요!")
    if st.button("면접 하러 가기"):
        st.switch_page("pages/7_📹_면접진행.py")
    st.stop()

# 3. 세션 선택 UI (Selectbox)
# 보기 좋은 형식으로 변환: "2023-10-25 Tech Corp - Backend Developer (COMPLETED)"
session_options = {
    s['session_id']: f"[{s['created_at'][:10]}] {s.get('company_name')} - {s.get('job_role')} ({s['status']})"
    for s in sessions
}

selected_session_id = st.selectbox(
    "📄 분석할 면접 세션을 선택하세요",
    options=list(session_options.keys()),
    format_func=lambda x: session_options[x]
)

# 4. 리포트 데이터 가져오기
full_data = None
if selected_session_id:
    with st.spinner("리포트를 분석하고 불러오는 중입니다..."):
        try:
            full_data = report_api.get_full_report(selected_session_id, st.session_state.token)
        except Exception as e:
            st.error(f"데이터 조회 중 오류: {e}")

# 5. 리포트 렌더링
if full_data:
    final_report = full_data.get('final_report')
    answers = full_data.get('answers', [])

    # (A) 아직 분석이 안 끝난 경우
    if not final_report:
        st.warning("⚠️ 아직 종합 리포트가 생성되지 않았습니다.")
        st.write("모든 답변에 대한 AI분석이 완료되면 리포트가 생성됩니다.")
        
        # 개별 답변 진행 상황 표시
        st.subheader("답변 분석 현황")
        for ans in answers:
            status = "분석 대기/진행 중"
            if ans.get('visual') and ans.get('voice'): # 간단 체크
                status = "✅ 완료"
            st.write(f"- **{ans['question_content']}**: {status}")
            
    # (B) 분석 완료 -> 리포트 표시
    else:
        # --- 종합 평가 섹션 ---
        st.markdown("---")
        st.header("🏆 종합 평가")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric("종합 점수", f"{final_report['total_score']}점")
        with col2:
            st.subheader(final_report['summary_headline'])
            st.info(final_report['overall_feedback'])

        # --- 모듈별 상세 점수 ---
        st.markdown("---")
        st.subheader("📈 영역별 분석")
        
        m_col1, m_col2, m_col3 = st.columns(3)
        
        # Visual
        with m_col1:
            st.markdown("#### 😊 비주얼 (표정/시선)")
            v_score = final_report['visual']['avg_score']
            st.progress(v_score / 100)
            st.write(f"**{v_score}점**")
            if final_report['visual'].get('summary'):
                st.caption(final_report['visual']['summary'])
                
        # Voice
        with m_col2:
            st.markdown("#### 🎤 음성 (발음/속도)")
            a_score = final_report['voice']['avg_score']
            st.progress(a_score / 100)
            st.write(f"**{a_score}점**")
            if final_report['voice'].get('summary'):
                st.caption(final_report['voice']['summary'])

        # Content
        with m_col3:
            st.markdown("#### 📝 내용 (논리/적합성)")
            c_score = final_report['content']['avg_score']
            st.progress(c_score / 100)
            st.write(f"**{c_score}점**")
            if final_report['content'].get('summary'):
                st.caption(final_report['content']['summary'])

        # --- 강점 & 약점 ---
        st.markdown("---")
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("👍 Best Points")
            # 통합된 강점이 있다면 그것을, 없으면 각 모듈별 강점 나열
            # 여기서는 DB 구조상 각 모듈별 json 리스트가 있음
            
            # visual
            for p in final_report.get('visual_points', {}).get('strengths', []):
                st.write(f"- (비주얼) {p}")
            # voice
            for p in final_report.get('voice_points', {}).get('strengths', []):
                st.write(f"- (음성) {p}")
            # content
            for p in final_report.get('content_points', {}).get('strengths', []):
                st.write(f"- (내용) {p}")

        with c2:
            st.subheader("💡 Improvement Needed")
            # visual
            for p in final_report.get('visual_points', {}).get('weaknesses', []):
                st.write(f"- (비주얼) {p}")
            # voice
            for p in final_report.get('voice_points', {}).get('weaknesses', []):
                st.write(f"- (음성) {p}")
            # content
            for p in final_report.get('content_points', {}).get('weaknesses', []):
                st.write(f"- (내용) {p}")

        # --- 액션 플랜 ---
        if final_report.get('action_plans'):
            st.markdown("---")
            st.subheader("🚀 Next Action Plan")
            for plan in final_report['action_plans']:
                with st.expander(f"📌 {plan['title']}", expanded=True):
                    st.write(plan['description'])

        # --- 질문별 상세 보기 ---
        st.markdown("---")
        st.subheader("💬 질문별 상세 리포트")
        
        for i, ans in enumerate(answers):
            with st.expander(f"Q{i+1}. {ans['question_content']}", expanded=False):
                # 영상 재생 (경로가 있다면)
                # 주의: 로컬 파일 경로면 streamlit에서 바로 재생 안 될 수 있음 (static serving 필요)
                # 여기서는 UI 구성만 보여줌
                
                tab1, tab2, tab3 = st.tabs(["비주얼 분석", "음성 분석", "내용 분석"])
                
                # 1. 비주얼
                with tab1:
                    if ans.get('visual'):
                        res = ans['visual']
                        st.write(f"**점수:** {res['score']}점")
                        st.info(res['feedback'])
                        if res.get('bad_points_json'):
                            st.write("**아쉬운 점:**")
                            for bp in res['bad_points_json']:
                                st.write(f"- {bp}")
                    else:
                        st.caption("분석 결과가 없습니다.")

                # 2. 음성
                with tab2:
                    if ans.get('voice'):
                        res = ans['voice']
                        st.write(f"**점수:** {res['score']}점")

                        metrics = res.get('metrics', res)

                        # 1. 기존 메트릭 표시
                        c1, c2, c3 = st.columns(3)

                        # .get()을 사용해 값이 없어도 에러가 나지 않도록 방어
                        # DB에 avg_cps 컬럼이 없다면 0.0으로 나올 수 있습니다.
                        avg_cps = metrics.get('avg_cps', metrics.get('avg_wpm', 0) / 60 * 3)

                        silence_count = metrics.get('silence_count', 0)
                        duration_sec = metrics.get('duration_sec', metrics.get('duration', 0))
                        
                        c1.metric("평균 속도", f"{metrics.get('avg_cps', 0):.1f} CPS")
                        c2.metric("침묵 횟수", f"{metrics.get('silence_count', 0)}회")
                        c3.metric("전체 길이", f"{metrics.get('duration_sec', metrics.get('duration', 0)):.1f}초")

                        st.divider()

                        # 2. 🌊 말하기 속도 변화 그래프 (NEW!)
                        charts = res.get('charts', res.get('charts_json', {}))

                        if charts and 'speed_flow' in charts:
                            st.markdown("##### 📈 말하기 속도 흐름")
                            
                            speed_data = charts['speed_flow']
                            
                            if speed_data:
                                # 데이터프레임으로 변환
                                df_speed = pd.DataFrame(speed_data)
                                
                                # 차트 그리기 (Altair나 Streamlit native chart 사용)
                                # X축: time, Y축: cps
                                st.line_chart(df_speed, x="time", y="cps", color="#FF4B4B")
                                
                                st.caption("""
                                - **가로축(X):** 답변 시간 (초)
                                - **세로축(Y):** 순간 말하기 속도 (CPS)
                                - 그래프가 **너무 높게 치솟으면** 급하게 말한 구간, **바닥에 닿으면** 침묵하거나 버벅인 구간입니다.
                                """)
                            else:
                                st.info("그래프를 그릴 충분한 데이터가 없습니다.")
                                
                        st.info(res['feedback'])

                    else:
                        st.caption("분석 결과가 없습니다.")

                # 3. 내용
                with tab3:
                    if ans.get('content'):
                        res = ans['content']

                        # 1. 실제 STT 텍스트 표시 (피드백 위쪽에 배치)
                        st.markdown("##### 💬 실제 답변 내용 (STT)")
                        st.code(ans.get('stt_text', "답변 텍스트를 불러올 수 없습니다."), language=None)

                        st.divider() # 구분선 추가
                        
                        # 2. 기존 점수 및 피드백 정보
                        if 'score' in res and res['score'] is not None:
                            final_score = res['score']
                        else:
                            # 0점 방지를 위해 get(..., 0) 사용
                            l_score = res.get('logic_score', 0)
                            j_score = res.get('job_fit_score', 0)
                            t_score = res.get('time_management_score', 0)
                            final_score = int((l_score + j_score + t_score) / 3)

                        st.write(f"**종합 점수:** {final_score}점")
                        st.write(f"**논리성:** {res.get('logic_score', 0)} / **직무적합도:** {res.get('job_fit_score', 0)} / **시간관리:** {res.get('time_management_score', 0)}")
                        
                        st.markdown("**AI 피드백**")
                        st.info(res.get('feedback', '피드백이 없습니다.'))
                        
                        if res.get('model_answer'):
                            st.success(f"**💡 모범 답안 제안:**\n\n{res['model_answer']}")
                    else:
                        st.caption("분석 결과가 없습니다.")