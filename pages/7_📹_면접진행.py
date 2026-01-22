import streamlit as st
import requests
import time
import cv2
import numpy as np

# -----------------------------
# 1. 로그인 및 세션 체크
# -----------------------------
if not st.session_state.get('user') or not st.session_state.get('token'):
    st.warning("로그인이 필요한 서비스입니다.")
    st.switch_page("pages/3_🔐_로그인.py")
    st.stop()

# -----------------------------
# 2. 분석 실패 UI 함수
# -----------------------------
def display_analysis_failure(answer_id, error_msg="네트워크 연결이 불안정합니다."):
    st.error("⚠️ AI 분석 중 오류가 발생했습니다.")
    with st.expander("상세 에러 내용 확인"):
        st.write(f"**답변 ID:** {answer_id}")
        st.write(f"**오류 메시지:** {error_msg}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 분석 다시 시도", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("📹 답변 다시 하기", use_container_width=True, type="primary"):
            st.rerun()

# -----------------------------
# 3. API 및 세션 초기화
# -----------------------------
API_BASE = "http://localhost:8000"
headers = {"Authorization": f"Bearer {st.session_state.get('token')}"}

st.title("📹 AI 실시간 모의면접")

# 면접 상태 초기화
if 'current_question_idx' not in st.session_state:
    st.session_state.current_question_idx = 0
if 'interview_session_id' not in st.session_state:
    st.session_state.interview_session_id = None
if 'questions' not in st.session_state:
    st.session_state.questions = []

# 얼굴 인식용 Cascade (없어도 동작하도록 예외처리)
face_cascade = None
try:
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
except:
    pass


# ==============================================================================
# 4. [면접 시작 전] 이력서 선택 및 세션 생성 화면
# ==============================================================================
if st.session_state.interview_session_id is None:
    st.subheader("📌 면접 준비")
    
    # ---------------------------------------------------------
    # (1) 이력서 목록 불러오기 (캐싱 적용)
    # ---------------------------------------------------------
    @st.cache_data(show_spinner=False, ttl=60)
    def fetch_my_resumes(token):
        try:
            r = requests.get(f"{API_BASE}/api/v1/resume/", headers={"Authorization": f"Bearer {token}"}, timeout=5)
            if r.status_code == 200:
                return r.json()
            return []
        except:
            return []

    with st.spinner("내 이력서 목록을 불러오는 중..."):
        resumes_data = fetch_my_resumes(st.session_state['token'])
    
    # 데이터 정규화 (리스트로 변환)
    resumes = []
    if isinstance(resumes_data, list):
        resumes = resumes_data
    elif isinstance(resumes_data, dict):
        resumes = resumes_data.get("items") or resumes_data.get("data") or []

    # ---------------------------------------------------------
    # (2) 이력서 선택 UI
    # ---------------------------------------------------------
    selected_resume_id = None
    
    if not resumes:
        st.warning("등록된 이력서가 없습니다. '온보딩' 메뉴에서 이력서를 먼저 등록해주세요.")
        if st.button("이력서 등록하러 가기"):
            st.switch_page("pages/4_👤_온보딩.py")
        st.stop()
    else:
        # 보기 좋은 라벨 생성 함수
        def get_resume_label(r):
            job = r.get("job_title", "직무 미상")
            company = r.get("target_company", "목표 회사 미상")
            date = r.get("created_at", "")[:10]
            return f"[{date}] {job} ({company})"

        # ID와 라벨 매핑
        resume_options = {r["resume_id"]: get_resume_label(r) for r in resumes}
        
        # 선택 박스
        selected_resume_id = st.selectbox(
            "면접에 사용할 이력서를 선택하세요:",
            options=list(resume_options.keys()),
            format_func=lambda x: resume_options[x]
        )
        st.success(f"선택된 이력서: **{resume_options[selected_resume_id]}**")

    st.divider()

    # ---------------------------------------------------------
    # (3) 가이드라인 및 카메라 테스트
    # ---------------------------------------------------------
    st.info("""
    **면접 가이드라인**
    1. 밝은 조명을 유지하고 얼굴을 화면 중앙에 맞춰주세요.
    2. 질문당 답변 시간은 1분 내외가 적당합니다.
    3. 준비가 완료되면 아래 버튼을 눌러 면접을 시작합니다.
    """)

    # 카메라 테스트 (공간 차지하므로 접을 수 있게)
    with st.expander("📷 카메라 테스트 열기", expanded=False):
        camera_test = st.camera_input("카메라 작동 확인")
        if camera_test and face_cascade:
            # 얼굴 인식 가이드 오버레이 (테스트용)
            bytes_data = camera_test.getvalue()
            img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            for (x, y, w, h) in faces:
                cv2.rectangle(img, (x, y), (x+w, y+h), (255, 0, 0), 2)
            st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), caption="얼굴 인식 테스트")

    # ---------------------------------------------------------
    # (4) 면접 시작 버튼
    # ---------------------------------------------------------
    if st.button("🚀 준비 완료 - 면접 시작", type="primary", use_container_width=True):
        if not selected_resume_id:
            st.error("이력서를 선택해야 합니다.")
        else:
            with st.status("면접 세션을 생성하고 질문을 준비 중입니다...", expanded=True) as status:
                try:
                    # 1. 세션 생성 (이력서 ID 포함)
                    payload = {"resume_id": int(selected_resume_id)}
                    
                    res = requests.post(f"{API_BASE}/api/v1/session/", json=payload, headers=headers)
                    
                    if res.status_code in (200, 201):
                        sess_data = res.json()
                        session_id = sess_data['session_id']
                        st.session_state.interview_session_id = session_id
                        status.write("✅ 세션 생성 완료!")
                        
                        # 2. 질문 목록 조회 (생성된 세션 ID로 조회)
                        q_res = requests.get(f"{API_BASE}/api/v1/question/session/{session_id}", headers=headers)
                        
                        if q_res.status_code == 200:
                            questions = q_res.json()
                            if questions:
                                st.session_state.questions = questions
                                st.session_state.current_question_idx = 0
                                status.update(label="✅ 준비 완료! 면접 화면으로 이동합니다.", state="complete")
                                time.sleep(1)
                                st.rerun()
                            else:
                                status.update(label="⚠️ 질문 생성 실패", state="error")
                                st.error("생성된 질문이 없습니다.")
                        else:
                            status.update(label="⚠️ 질문 조회 실패", state="error")
                            st.error(f"질문 목록 로드 실패: {q_res.status_code}")
                    else:
                        status.update(label="❌ 세션 생성 실패", state="error")
                        st.error(f"오류: {res.text}")
                        
                except Exception as e:
                    status.update(label="⚠️ 시스템 오류", state="error")
                    st.error(f"접속 오류: {e}")

    st.stop() # 면접 시작 전에는 아래 코드를 실행하지 않음


# ==============================================================================
# 5. [면접 진행] 질문 표시, AI 면접관(TTS), 답변 녹화
# ==============================================================================
questions = st.session_state.questions
idx = st.session_state.current_question_idx

if idx < len(questions):
    current_q = questions[idx]
    
    # 상단 진행률 바
    progress = (idx) / len(questions)
    st.progress(progress, text=f"진행률 {idx + 1}/{len(questions)}")
    
    st.divider()

    # ---------------------------------------------------------
    # 🎯 화면 2분할 (왼쪽: AI 면접관 / 오른쪽: 내 모습)
    # ---------------------------------------------------------
    col_ai, col_user = st.columns([1, 1], gap="medium")

    # [왼쪽] AI 면접관 영역
    with col_ai:
        st.markdown("### 👩‍💼 AI 면접관")
        
        # 1. 면접관 이미지 (무료 스톡 이미지 예시)
        # 실제로는 로컬 파일(assets/interviewer.png)을 쓰거나 다른 URL로 교체 가능
        interviewer_img = "https://cdn.pixabay.com/photo/2021/05/04/13/29/portrait-6228705_1280.jpg"
        st.image(interviewer_img, caption="AI 면접관", use_container_width=True)

        # 2. TTS 음성 생성 및 재생 로직
        # (세션 상태를 활용해 질문당 1번만 API 호출하도록 처리)
        tts_key = f"tts_audio_{current_q['question_id']}"
        
        if tts_key not in st.session_state:
            with st.spinner("면접관이 질문을 준비 중입니다..."):
                try:
                    # 백엔드 TTS API 호출
                    tts_res = requests.post(
                        f"{API_BASE}/api/v1/interview/tts",
                        headers=headers,
                        json={
                            "text": current_q['content'],
                            "voice": "nova"  # 목소리 톤 (alloy, echo, fable, onyx, nova, shimmer)
                        },
                        timeout=10
                    )
                    if tts_res.status_code == 200:
                        st.session_state[tts_key] = tts_res.content
                    else:
                        st.warning("음성 데이터를 불러오지 못했습니다.")
                except Exception as e:
                    # TTS 실패해도 면접은 진행되어야 하므로 에러만 찍고 넘어감
                    print(f"TTS Error: {e}")

        # 3. 질문 텍스트 및 오디오 재생
        st.info(f"🗣️ **Q{idx+1}.** {current_q['content']}")
        
        # 오디오 데이터가 있으면 재생 (autoplay=True)
        if tts_key in st.session_state:
            st.audio(st.session_state[tts_key], format="audio/mp3", autoplay=True)
        
        st.caption(f"유형: {current_q['category']}")


    # [오른쪽] 지원자(나) 영역
    with col_user:
        st.markdown("### 🧑‍💻 지원자 (나)")

        # 1. 카메라 입력
        video_file = st.camera_input(
            f"Q{idx+1} 답변 촬영", 
            key=f"cam_{idx}", 
            label_visibility="collapsed" # 라벨 숨김 (깔끔하게)
        )
        
        # 2. 얼굴 가이드 (선택 사항)
        # (카메라가 켜졌을 때만 작동)
        if video_file is not None and face_cascade is not None:
             # 사용자 경험을 위해 매 프레임 분석은 Streamlit에서 느릴 수 있어 생략하거나
             # 필요시 여기에 cv2 로직 추가
             pass

        # 3. 제출 버튼
        if video_file:
            st.success("영상 기록 완료! 제출 버튼을 눌러주세요.")
            
            if st.button(f"📤 답변 제출 (Q{idx+1})", use_container_width=True, type="primary"):
                with st.status("🚀 답변을 전송하고 AI 분석을 요청합니다...", expanded=True) as status:
                    try:
                        # 파일 포인터 리셋
                        video_file.seek(0)
                        files = {"file": (video_file.name, video_file.getvalue(), video_file.type)}
                        data = {"question_id": str(current_q['question_id'])}

                        # 업로드 요청
                        res = requests.post(
                            f"{API_BASE}/api/v1/interview/upload",
                            headers=headers,
                            files=files,
                            data=data
                        )
                        
                        if res.status_code in (200, 201):
                            status.update(label="✅ 제출 성공!", state="complete")
                            st.toast("답변이 기록되었습니다.", icon="✅")
                            time.sleep(1)
                            
                            # 다음 질문으로 이동
                            st.session_state.current_question_idx += 1
                            st.rerun()
                        else:
                            status.update(label="❌ 제출 실패", state="error")
                            res_json = res.json()
                            display_analysis_failure(res_json.get('answer_id', 'Unknown'), res_json.get('message', res.text))
                            
                    except Exception as e:
                        status.update(label="⚠️ 전송 오류", state="error")
                        st.error(f"에러 발생: {e}")

else:
    # -----------------------------
    # 6. 모든 질문 종료 시
    # -----------------------------
    st.balloons()
    st.success("🎉 모든 면접 질문이 종료되었습니다!")
    st.markdown("### 수고하셨습니다!")
    st.info("AI가 전체 면접 내용을 바탕으로 종합 리포트를 생성합니다.")
    
    if st.button("📊 결과 리포트 확인하기", type="primary", use_container_width=True):
        # (선택) 여기서 세션 전체 분석 트리거 API를 호출할 수도 있음
        # requests.post(f"{API_BASE}/api/v1/analysis/session/{st.session_state.interview_session_id}", headers=headers)
        st.switch_page("pages/6_📊_리포트.py")