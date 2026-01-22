import streamlit as st
import streamlit.components.v1 as components
import requests
import time
import cv2
import numpy as np

import base64

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
        components.html(
        """
        <style>
            #container {
                position: relative;
                width: 100%;
                max-width: 640px;
                margin: 0 auto;
            }
            video {
                width: 100%;
                height: auto;
                transform: scaleX(-1); /* 거울 모드 */
                border-radius: 10px;
            }
            canvas {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                pointer-events: none;
                transform: scaleX(-1); /* 캔버스도 거울 모드 */
            }
            #status {
                position: absolute;
                bottom: 10px;
                left: 50%;
                transform: translateX(-50%);
                background: rgba(0,0,0,0.6);
                color: white;
                padding: 5px 10px;
                border-radius: 5px;
                font-family: sans-serif;
                font-size: 14px;
                display: none; /* JS 로딩 전엔 숨김 */
            }
        </style>

        <div id="container">
            <video id="video" autoplay muted playsinline></video>
            <canvas id="overlay"></canvas>
            <div id="status">AI 모델 로딩 중...</div>
        </div>

        <script type="module">
            import {
                FaceDetector,
                FilesetResolver
            } from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.0/+esm";

            const video = document.getElementById("video");
            const canvas = document.getElementById("overlay");
            const ctx = canvas.getContext("2d");
            const statusDiv = document.getElementById("status");
            
            let faceDetector;
            let runningMode = "VIDEO";
            let lastVideoTime = -1;

            // 1. MediaPipe FaceDetector 초기화
            async function initializeFaceDetector() {
                const vision = await FilesetResolver.forVisionTasks(
                    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.0/wasm"
                );
                
                faceDetector = await FaceDetector.createFromOptions(vision, {
                    baseOptions: {
                        modelAssetPath: `https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite`,
                        delegate: "GPU"
                    },
                    runningMode: runningMode
                });
                
                statusDiv.style.display = "block";
                statusDiv.innerText = "카메라 준비 중...";
                startCamera();
            }

            // 2. 웹캠 시작
            function startCamera() {
                navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } })
                .then(stream => {
                    video.srcObject = stream;
                    video.addEventListener("loadeddata", predictWebcam);
                    statusDiv.innerText = "얼굴을 원 안에 맞춰주세요.";
                })
                .catch(err => {
                    statusDiv.innerText = "카메라 권한이 필요합니다.";
                    console.error(err);
                });
            }

            // 3. 실시간 감지 및 그리기 루프
            async function predictWebcam() {
                // 캔버스 크기를 비디오 실제 크기에 맞춤
                if (video.videoWidth > 0 && canvas.width !== video.videoWidth) {
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                }

                let startTimeMs = performance.now();

                // 비디오 프레임이 변했을 때만 감지 수행
                if (video.currentTime !== lastVideoTime) {
                    lastVideoTime = video.currentTime;
                    
                    if (faceDetector) {
                        const detections = faceDetector.detectForVideo(video, startTimeMs).detections;
                        drawGuideAndFace(detections);
                    }
                }

                window.requestAnimationFrame(predictWebcam);
            }

            // 4. 그리기 로직 (원 그리기 + 판정)
            function drawGuideAndFace(detections) {
                ctx.clearRect(0, 0, canvas.width, canvas.height);

                // 가이드 원 설정
                const centerX = canvas.width / 2;
                const centerY = canvas.height * 0.45; // 화면 약간 상단
                const radius = canvas.width * 0.18;   // 원 크기

                let isInside = false;

                // 얼굴이 감지되었는지 확인
                if (detections && detections.length > 0) {
                    const face = detections[0].boundingBox;
                    
                    // 얼굴 중심점 계산
                    const faceX = face.originX + (face.width / 2);
                    const faceY = face.originY + (face.height / 2);

                    // 원의 중심과 얼굴 중심 사이의 거리 계산 (피타고라스)
                    const distance = Math.sqrt(
                        Math.pow(faceX - centerX, 2) + Math.pow(faceY - centerY, 2)
                    );

                    // 판정: 거리가 허용 오차(예: 반지름의 40%) 이내인지
                    // 즉, 얼굴이 원의 중심에 가깝게 들어왔는지 확인
                    if (distance < radius * 0.5) {
                        isInside = true;
                    }
                }

                // 색상 결정 (안에 있으면 초록, 아니면 빨강)
                const color = isInside ? "#00FF00" : "#FF0000"; // Lime Green or Red
                const lineWidth = isInside ? 6 : 4;

                // 원 그리기
                ctx.beginPath();
                ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
                ctx.lineWidth = lineWidth;
                ctx.strokeStyle = color;
                ctx.stroke();
                
                // (선택사항) 상태 텍스트 업데이트
                if (isInside) {
                    statusDiv.innerText = "위치가 적절합니다! ✅";
                    statusDiv.style.color = "#00FF00";
                } else {
                    statusDiv.innerText = "얼굴을 원 안으로 이동해주세요 🟥";
                    statusDiv.style.color = "#FFcccc";
                }
            }

            // 시작
            initializeFaceDetector();
        </script>
        """,
        height=550 # 비디오 비율에 맞춰 넉넉하게
        )

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
        # st.image(interviewer_img, caption="AI 면접관", use_container_width=True)



        # (3) TTS 생성(이미 있던 로직 유지) + 캐시 키
        tts_key = f"tts_audio_{current_q['question_id']}"
        if tts_key not in st.session_state:
            with st.spinner("면접관이 질문을 읽어주는 중입니다..."):
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
                        st.warning(f"TTS 실패: {tts_res.status_code} {tts_res.text[:200]}")
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

    # ==========================
    # [오른쪽] 지원자(나) 녹화 영역
    # ==========================
    with col_user:
        st.markdown("### 🎙️ 답변 녹화")

        if "recorded_video" not in st.session_state:
            st.session_state.recorded_video = None

        # 커스텀 JS 녹화 컴포넌트
        video_base64 = components.html(
        """
        <style>
        body { margin: 0; padding: 0; overflow: hidden; }
        #video-wrapper {
            position: relative;
            width: 100%;
            aspect-ratio: {ASPECT_W}/{ASPECT_H};
            background: #000;
            border-radius: 12px;
            overflow: hidden;
        }
        video {
            width: 100%;
            height: 100%;             /* ✅ wrapper 높이를 꽉 채움 */
            height: auto;
            object-fit: cover;        /* ✅ 비율 맞추면서 크롭 */
            transform: scaleX(-1); /* 거울 모드 */
        }
        #controls {
            margin-top: 10px;
            display: flex;
            justify-content: center;
            gap: 10px;
        }
        button {
            font-size: 14px;
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            color: white;
        }
        #startBtn { background-color: #28a745; }
        #startBtn:disabled { background-color: #ccc; cursor: not-allowed; }
        #stopBtn { background-color: #dc3545; }
        #stopBtn:disabled { background-color: #ccc; cursor: not-allowed; }
        
        .timer-box {
            text-align: center;
            font-size: 18px;
            font-family: monospace;
            margin-top: 5px;
            color: #333;
        }
        #warning { color: red; font-weight: bold; font-size: 14px; height: 20px; text-align: center; }
        </style>

        <div id="video-wrapper">
            <video id="preview" autoplay muted playsinline></video>
        </div>

        <div class="timer-box">
            ⏱ <span id="timer">00:00</span> / 02:00
        </div>
        <div id="warning"></div>

        <div id="controls">
            <button id="startBtn" onclick="startRecording()">▶ 녹화 시작</button>
            <button id="stopBtn" onclick="stopRecording()" disabled>■ 녹화 종료</button>
        </div>

        <script>
        let mediaRecorder;
        let recordedChunks = [];
        let timerInterval;
        let elapsed = 0;
        let stream;

        const MAX_TIME = 120;
        const WARNING_TIME = 105;

        // 카메라 권한 요청 및 미리보기 시작
        navigator.mediaDevices.getUserMedia({ video: true, audio: true })
        .then(s => {
            stream = s;
            document.getElementById("preview").srcObject = stream;
        })
        .catch(err => {
            document.getElementById("warning").innerText = "카메라/마이크 권한이 필요합니다.";
        });

        function formatTime(sec) {
            const m = String(Math.floor(sec / 60)).padStart(2, "0");
            const s = String(sec % 60).padStart(2, "0");
            return `${m}:${s}`;
        }

        function startRecording() {
            if (!stream) return;
            
            document.getElementById("startBtn").disabled = true;
            document.getElementById("stopBtn").disabled = false;

            elapsed = 0;
            recordedChunks = [];
            document.getElementById("timer").innerText = "00:00";
            document.getElementById("warning").innerText = "";

            mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm' });

            mediaRecorder.ondataavailable = e => {
                if (e.data.size > 0) recordedChunks.push(e.data);
            };

            mediaRecorder.start();

            timerInterval = setInterval(() => {
                elapsed++;
                document.getElementById("timer").innerText = formatTime(elapsed);

                if (elapsed === WARNING_TIME) {
                    document.getElementById("warning").innerText = "⚠️ 15초 남았습니다!";
                }

                if (elapsed >= MAX_TIME) {
                    stopRecording();
                }
            }, 1000);
        }

        function stopRecording() {
            document.getElementById("stopBtn").disabled = true;

            if (!mediaRecorder || mediaRecorder.state === "inactive") return;

            clearInterval(timerInterval);
            mediaRecorder.stop();

            mediaRecorder.onstop = () => {
                document.getElementById("startBtn").disabled = false;

                const blob = new Blob(recordedChunks, { type: "video/webm" });
                const reader = new FileReader();

                reader.onloadend = () => {
                    // base64 문자열만 추출하여 Streamlit으로 전송
                    const base64data = reader.result.split(",")[1];
                    window.parent.postMessage({
                        type: "streamlit:setComponentValue",
                        value: base64data
                    }, "*");
                };

                reader.readAsDataURL(blob);
            };
        }
        </script>
        """,
        height=700, # 높이 조정 (너무 크면 레이아웃 깨짐)
        scrolling=False
        )

        # JS에서 값이 넘어오면 세션에 저장
        if video_base64:
            st.session_state.recorded_video = video_base64
            st.success("✅ 녹화가 완료되었습니다. 아래 버튼을 눌러 제출하세요.")


    # ==========================
    # [하단] 제출 및 이동 버튼
    # ==========================
    # 녹화된 영상이 있을 때만 버튼 활성화
    if st.session_state.get("recorded_video"):
        st.divider()
        
        # [A] 중간 질문 (1~4번) -> "다음 질문" 버튼
        if idx < 4:  # 0,1,2,3 (총 4개) -> idx < 4 이면 5번째(idx=4) 질문이 남음
            if st.button("➡ 제출하고 다음 질문으로 이동", type="primary", use_container_width=True):
                with st.spinner("답변을 업로드 중입니다..."):
                    try:
                        video_bytes = base64.b64decode(st.session_state.recorded_video)
                        files = {"file": ("answer.webm", video_bytes, "video/webm")}
                        data = {"question_id": str(current_q["question_id"])}

                        res = requests.post(
                            f"{API_BASE}/api/v1/interview/upload",
                            headers=headers,
                            files=files,
                            data=data
                        )

                        if res.status_code in (200, 201):
                            # 성공 시 상태 초기화 후 이동
                            st.session_state.recorded_video = None
                            st.session_state.current_question_idx += 1
                            st.toast("답변이 저장되었습니다.", icon="💾")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(f"업로드 실패: {res.text}")
                    except Exception as e:
                        st.error(f"오류 발생: {e}")

        # [B] 마지막 질문 (5번) -> "종료 및 분석" 버튼
        else:
            if st.button("🏁 면접 종료 및 결과 분석 시작", type="primary", use_container_width=True):
                with st.status("마지막 답변을 저장하고 분석을 시작합니다...", expanded=True) as status:
                    try:
                        # 1. 마지막 영상 업로드
                        video_bytes = base64.b64decode(st.session_state.recorded_video)
                        files = {"file": ("answer.webm", video_bytes, "video/webm")}
                        data = {"question_id": str(current_q["question_id"])}

                        res = requests.post(
                            f"{API_BASE}/api/v1/interview/upload",
                            headers=headers,
                            files=files,
                            data=data
                        )
                        
                        if res.status_code not in (200, 201):
                            status.update(label="❌ 마지막 영상 업로드 실패", state="error")
                            st.error(res.text)
                            st.stop()
                        
                        status.write("✅ 답변 저장 완료")

                        # 2. 분석 요청 (세션 단위)
                        # 세션 ID가 필요하므로 session_state나 current_q에서 가져옴
                        session_id = st.session_state.interview_session_id
                        
                        analyze_res = requests.post(
                            f"{API_BASE}/api/v1/analysis/session/{session_id}",
                            headers=headers,
                            timeout=10 # 트리거만 하므로 짧게
                        )
                        
                        if analyze_res.status_code == 200:
                            status.update(label="🚀 분석 시작됨!", state="complete")
                            time.sleep(1)
                            st.switch_page("pages/6_📊_리포트.py")
                        else:
                            status.update(label="⚠️ 분석 요청 실패", state="error")
                            st.error(analyze_res.text)
                            
                    except Exception as e:
                        st.error(f"오류: {e}")


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