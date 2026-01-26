import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import requests
import time
import threading # [필수 추가] 쓰레딩 모듈
import queue     # [필수 추가] 큐 모듈
from app.utils.camera_utils import FaceGuideTransformer
from app.utils.save_utils import save_muxed_video

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
        if st.button("🔄 분석 다시 시도", width="stretch"):
            st.rerun()
    with col2:
        if st.button("📹 답변 다시 하기", width="stretch", type="primary"):
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
if "recorded_video" not in st.session_state:
    st.session_state.recorded_video = None
if "recording_active" not in st.session_state:
    st.session_state.recording_active = False
if "recording_done" not in st.session_state:
    st.session_state.recording_done = False
if "video_path" not in st.session_state:
    st.session_state.video_path = None
if "audio_path" not in st.session_state:
    st.session_state.audio_path = None
if "video_frames" not in st.session_state:
    st.session_state.video_frames = []
if "audio_frames" not in st.session_state:
    st.session_state.audio_frames = []



# ==============================================================================
# 4. [면접 시작 전] 이력서 선택 및 세션 생성 화면
# ==============================================================================
if st.session_state.interview_session_id is None:
    st.subheader("📌 면접 준비 ")
    
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
        st.info("얼굴을 중앙 원 안에 맞추세요. 초록색이면 적절합니다.")

        rtc_configuration = {
            "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
        }

        webrtc_streamer(
            key="camera_test",
            mode=WebRtcMode.SENDRECV,
            video_processor_factory=FaceGuideTransformer,
            media_stream_constraints={"video": True, "audio": False},
            rtc_configuration=rtc_configuration,
            async_processing=True,
            desired_playing_state=True
        )

    # ---------------------------------------------------------
    # (4) 면접 시작 버튼
    # ---------------------------------------------------------
    if st.button("🚀 준비 완료 - 면접 시작", type="primary", width="stretch"):
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

# ==============================================================================
# 백그라운드 녹화용 쓰레드 클래스 정의
# 별도의 thread를 사용해서 백그라운드에서 녹화
# 버튼 클릭 가능한지 test 요구.
# (by ddu, Gemini 3 Pro)
# ==============================================================================
class RecorderThread(threading.Thread):
    def __init__(self, webrtc_ctx):
        super().__init__()
        self.webrtc_ctx = webrtc_ctx
        self.running = True
        self.video_frames = []
        self.audio_frames = []

    def run(self):
        while self.running:
            if self.webrtc_ctx.video_receiver:
                try:
                    # 타임아웃을 줘서 블로킹 방지
                    v_frame = self.webrtc_ctx.video_receiver.get_frame(timeout=0.05)
                    if v_frame:
                        self.video_frames.append(v_frame)
                except queue.Empty:
                    pass
            
            if self.webrtc_ctx.audio_receiver:
                try:
                    a_frame = self.webrtc_ctx.audio_receiver.get_frame(timeout=0.05)
                    if a_frame:
                        self.audio_frames.append(a_frame)
                except queue.Empty:
                    pass

    def stop(self):
        self.running = False
# ==============================================================================

if idx < len(questions):
    current_q = questions[idx]
    
    # ---------------------------------------------------------
    # 🎯 화면 상단: 진행률 및 질문 정보
    # ---------------------------------------------------------
    progress = (idx) / len(questions)
    st.progress(progress, text=f"진행률 {idx + 1}/{len(questions)}")
    
    st.divider()

    # ---------------------------------------------------------
    # 🎯 화면 2분할 (왼쪽: AI 면접관 / 오른쪽: 내 모습)
    # ---------------------------------------------------------
    # (2) 질문 텍스트 표시
    st.info(f"🗣️ **Q{idx+1}.** {current_q['content']}")
    st.caption(f"유형: {current_q['category']}")
    col_ai, col_user = st.columns([1, 1], gap="medium")

    # ==========================
    # [왼쪽] AI 면접관 영역
    # ==========================
    with col_ai:
        st.markdown("### 👩‍💼 AI 면접관")
        
        # ✅ 7_면접 진행.py (with col_ai 블록 안) : TTS -> Wav2Lip(lipsync) -> video 재생
        # - interviewer_img(URL) 그대로 백엔드에 전달
        # - 질문별로 mp3/mp4를 session_state에 캐시해서 중복 생성 방지

        # (1) 면접관 이미지 (이미 너 코드에 있던 거)
        interviewer_img = "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxzZWFyY2h8M3x8JUVDJTk2JUJDJUVBJUI1JUI0fGVufDB8fDB8fHww"
        #st.image(interviewer_img, caption="AI 면접관", width="stretch")



        # (3) TTS 생성(이미 있던 로직 유지) + 캐시 키
        tts_key = f"tts_audio_{current_q['question_id']}"
        if tts_key not in st.session_state:
            with st.spinner("면접관이 질문을 읽는 중입니다..."):
                try:
                    tts_res = requests.post(
                        f"{API_BASE}/api/v1/interview/tts",
                        headers=headers,
                        json={"text": current_q["content"], "voice": "nova"},
                        timeout=30,
                    )
                    if tts_res.status_code == 200:
                        st.session_state[tts_key] = tts_res.content  # mp3 bytes
                    else:
                        st.warning("음성 데이터를 불러오지 못했습니다.")

                except Exception as e:
                    st.warning(f"TTS Error: {e}")

        # (4) ✅ Wav2Lip(mp4) 생성 + 캐시
        lipsync_key = f"lipsync_mp4_{current_q['question_id']}"
        if tts_key in st.session_state and lipsync_key not in st.session_state:
            with st.spinner("면접관 립싱크 영상을 생성 중입니다..."):
                try:
                    files = {
                        "audio": ("tts.mp3", st.session_state[tts_key], "audio/mpeg")
                    }
                    data = {
                        "avatar_url": interviewer_img,  # ✅ 여기!
                        "resize_factor": "1",
                        "nosmooth": "false",
                    }

                    ls_res = requests.post(
                        f"{API_BASE}/api/v1/interview/lipsync",
                        headers=headers,
                        files=files,
                        data=data,
                        timeout=180,
                    )

                    if ls_res.status_code == 200:
                        st.session_state[lipsync_key] = ls_res.content  # mp4 bytes
                    else:
                        st.warning(f"립싱크 실패: {ls_res.status_code} {ls_res.text[:300]}")
                except Exception as e:
                    st.warning(f"립싱크 Error: {e}")

        # (5) ✅ mp4 있으면 영상 재생, 없으면 오디오 fallback
        if lipsync_key in st.session_state:
            st.video(st.session_state[lipsync_key], format="video/mp4", autoplay=True)
        elif tts_key in st.session_state:
            st.audio(st.session_state[tts_key], format="audio/mp3", autoplay=True)
        else:
            st.warning("오디오/영상 생성에 실패했습니다.")


# ==============================================================================
# 녹화가 끝나도 화면이 갱신 X 
# -> "다음 질문" 버튼 안보임?
# or
# -> 버튼 눌러도 화면 전환 실패 
# "다음 질문" 버튼을 누르면 st.rerun()으로 스크립트 재시작 추가
#
# (by ddu, Gemini 3 Pro)
# ==============================================================================
    # ==========================
    # [오른쪽] 지원자(나) 녹화 영역
    # ==========================
    with col_user:
        st.markdown("### 🎙️ 답변 녹화")

        # 1. WebRTC 스트리머
        webrtc_ctx = webrtc_streamer(
            key=f"user_record_{idx}", # 키가 바뀌면 컴포넌트가 리셋되므로 질문마다 바뀜
            mode=WebRtcMode.SENDRECV,
            video_processor_factory=FaceGuideTransformer,
            media_stream_constraints={"video": True, "audio": True},
            rtc_configuration={
                "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
            },
            async_processing=True,
            desired_playing_state=True,
        )

        # ---------------------------
        # 녹화 상태 UI & 로직
        # ---------------------------
        
        # A. 녹화 완료 상태 (다음 질문 넘어가기)
        if st.session_state.recording_done:
            st.success("✅ 녹화가 완료되었습니다.")
            
            # 다음 질문 버튼
            if st.button("➡️ 다음 질문으로", type="primary", use_container_width=True):
                # 상태 초기화
                st.session_state.recording_done = False
                st.session_state.recording_active = False
                st.session_state.video_frames = []
                st.session_state.audio_frames = []
                st.session_state.video_path = None
                
                # 인덱스 증가
                st.session_state.current_question_idx += 1
                
                # [핵심] 리런을 해서 페이지를 새로고침해야 다음 질문이 로드됨
                st.rerun()

        # B. 녹화 중 상태
        elif st.session_state.recording_active:
            st.warning("🔴 녹화 중입니다... (카메라를 응시하세요)")
            
            # 쓰레드가 없으면 시작 (최초 1회)
            if "recorder_thread" not in st.session_state or not st.session_state.recorder_thread.is_alive():
                if webrtc_ctx.state.playing:
                    recorder = RecorderThread(webrtc_ctx)
                    recorder.start()
                    st.session_state.recorder_thread = recorder
            
            # 녹화 종료 버튼
            if st.button("⏹️ 녹화 종료", type="primary", use_container_width=True):
                st.session_state.recording_active = False
                
                # 쓰레드 정지 및 데이터 회수
                if "recorder_thread" in st.session_state:
                    recorder = st.session_state.recorder_thread
                    recorder.stop()
                    recorder.join() # 쓰레드 종료 대기

                    # 데이터 수집
                    v_frames = recorder.video_frames
                    a_frames = recorder.audio_frames  
                    
                    # 수집된 프레임 세션으로 이동
                    # st.session_state.video_frames = recorder.video_frames
                    # st.session_state.audio_frames = recorder.audio_frames
                    
                    # 쓰레드 제거
                    del st.session_state.recorder_thread

                    # [중요] 즉시 처리 후 상태 업데이트
                    if v_frames:
                        with st.spinner("영상을 병합하여 저장 중입니다..."):
                            merged_path = save_muxed_video(v_frames, a_frames)
                            if merged_path:
                                st.session_state.video_path = merged_path
                                st.session_state.recording_done = True      # 완료 플래그 ON
                                st.session_state.recording_active = False    # 활성 플래그 OFF
                                st.rerun() # 상태 반영을 위해 재실행
                            else:
                                st.error("영상 저장에 실패했습니다.")
                    else:
                        st.error("녹화된 프레임이 없습니다.")
                        st.session_state.recording_active = False
                        st.rerun()

        # C. 녹화 대기 상태
        else:
            # 카메라가 켜져있을 때만 녹화 시작 버튼 활성화
            if webrtc_ctx.state.playing:
                if st.button("🎥 녹화 시작", type="primary", use_container_width=True):
                    st.session_state.recording_active = True
                    st.session_state.recording_done = False # 명시적 초기화
                    st.rerun()
            else:
                st.info("카메라 로딩 중... (잠시만 기다려주세요)")


    # ==========================
    # [하단] 제출 버튼 (업로드 로직 수정)
    # ==========================
    if st.session_state.get("video_path") and st.session_state.recording_done:
        st.divider()
        
        # 버튼 텍스트 결정 (마지막 질문 여부)
        is_last_question = (idx == len(questions) - 1)
        btn_label = "🏁 면접 종료 및 결과 분석" if is_last_question else "➡ 제출하고 다음 질문으로 이동"
        
        if st.button(btn_label, type="primary", use_container_width=True):
            with st.spinner("답변을 업로드 중입니다..."):
                try:
                    # 합쳐진(Muxed) 파일 업로드
                    with open(st.session_state.video_path, "rb") as f:
                        files = {"file": ("answer.mp4", f, "video/mp4")}
                        data = {
                            "question_id": str(current_q["question_id"]),
                            "has_audio": "true", # 이제 진짜 오디오 있음
                            "fps": "30",
                            "source": "webrtc"
                        }
                        
                        res = requests.post(
                            f"{API_BASE}/api/v1/answer/upload",
                            headers=headers,
                            files=files,
                            data=data
                        )

                    if res.status_code in (200, 201):
                        st.toast("답변 저장 성공!", icon="💾")
                        
                        # 마지막 질문이면 리포트 분석 요청
                        if is_last_question:
                            st.info("종합 분석을 요청합니다...")
                            session_id = st.session_state.interview_session_id
                            requests.post(
                                f"{API_BASE}/api/v1/analysis/session/{session_id}",
                                headers=headers,
                                timeout=5 # Timeout 짧게 줘서 바로 넘어감
                            )
                            st.success("분석 시작! 리포트 페이지로 이동합니다.")
                            time.sleep(1)
                            st.switch_page("pages/6_📊_리포트.py")
                        
                        # 중간 질문이면 다음 질문으로 (UI 리셋은 위쪽 로직에서 처리됨)
                        else:
                            # 녹화 상태 초기화하고 다음 인덱스로
                            st.session_state.recording_done = False
                            st.session_state.video_path = None
                            st.session_state.current_question_idx += 1
                            st.rerun()
                            
                    else:
                        st.error(f"업로드 실패: {res.text}")

                except Exception as e:
                    st.error(f"오류 발생: {e}")
# ==============================================================================

else:
    # -----------------------------
    # 6. 모든 질문 종료 시
    # -----------------------------
    st.balloons()
    st.success("🎉 모든 면접 질문이 종료되었습니다!")
    st.markdown("### 수고하셨습니다!")
    st.info("AI가 전체 면접 내용을 바탕으로 종합 리포트를 생성합니다.")
    
    if st.button("📊 결과 리포트 확인하기", type="primary", width="stretch"):
        # (선택) 여기서 세션 전체 분석 트리거 API를 호출할 수도 있음
        # requests.post(f"{API_BASE}/api/v1/analysis/session/{st.session_state.interview_session_id}", headers=headers)
        st.switch_page("pages/6_📊_리포트.py")
    st.stop()

