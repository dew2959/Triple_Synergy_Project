# AWS GPU 분리 런북 (STT + GPU 가속 라이브러리)

작성일: 2026-02-20

## 1) 현재 코드 기준 GPU 분리 대상

### 1순위 (즉시 분리)
1. **STT (Whisper)**  
   - 위치: `app/engines/stt/engine.py`  
   - 근거: `openai-whisper`, `whisper.load_model()`, `transcribe()` 사용
2. **LipSync (Wav2Lip)**  
   - 위치: `app/api/v1/interview.py` (`/lipsync`)  
   - 근거: `third_party/Wav2Lip/inference.py` subprocess 실행, batch/fps 파라미터 존재

### 2순위 (상황 따라 선택)
3. **Visual 분석 (MediaPipe/OpenCV)**  
   - 위치: `app/engines/visual/engine.py`  
   - 근거: 프레임 단위 비디오 처리(CPU 부하 큼), GPU 효과는 환경/빌드에 따라 편차 큼

### 분리 비권장 (현 단계)
- `app/engines/voice/engine.py` (librosa 기반 전처리/통계): CPU로 충분
- `app/engines/llm/engine.py` (OpenAI API 호출): 원격 API 기반이라 로컬 GPU 직접 이득 제한적
- 인증/세션/DB CRUD/FastAPI 라우팅

---

## 2) 권장 아키텍처

- **App API (현재 FastAPI)**: 인증, 세션, DB, 오케스트레이션
- **GPU Worker API (AWS, 신규)**: `/stt`, `/lipsync` 전담
- **비동기 큐**: SQS(권장) 또는 Redis/RQ
- **스토리지**: S3 (입력 오디오/이미지, 출력 mp4)

### 요청 흐름
1. App API가 업로드 파일을 S3에 저장
2. Job 메시지를 큐에 push (`job_id`, `task_type`, `s3_input`)
3. GPU Worker가 poll 후 처리
4. 결과를 S3 + DB 상태 업데이트 (`queued -> running -> done/failed`)
5. App/Streamlit은 `job_id`로 폴링

> 동기 HTTP 직결보다 큐 기반이 타임아웃/장애 전파를 줄임.

---

## 3) AWS 인프라 최소안 (MVP)

- **GPU 인스턴스**: `g5.xlarge` 우선 (초기 PoC), 대안 `g4dn.xlarge`
- **Container Runtime**: NVIDIA Container Toolkit + Docker
- **Queue**: SQS standard
- **Storage**: S3 + presigned URL
- **관측**: CloudWatch logs + 에러율 알람

---

## 4) 서비스 계약(초안)

### STT Job
- input: `audio_s3_uri`, `language=ko`, `model_name=small`
- output: `text`, `segments`, `confidence_proxy`, `elapsed_ms`

### LipSync Job
- input: `audio_s3_uri`, `avatar_image_s3_uri|url`, `resize_factor`, `nosmooth`
- output: `video_s3_uri`, `elapsed_ms`, `stderr_log_uri(optional)`

### 공통 상태
- `queued | running | done | failed`
- 실패 시 `error_code`, `error_message`, `trace_id`

---

## 5) 1주 마이그레이션 체크리스트

## Day 1: 경계 정의 + 스키마 고정
- [ ] `stt`, `lipsync`을 원격 잡으로 분리하는 API 계약(JSON) 문서화
- [ ] `job_id` 상태 테이블(또는 기존 결과 테이블 확장) 정의
- [ ] `.env` 키 확정 (`GPU_WORKER_BASE_URL`, `GPU_QUEUE_MODE`, `AWS_S3_BUCKET` 등)

## Day 2: GPU Worker 스켈레톤
- [ ] AWS GPU 인스턴스에 Docker + NVIDIA runtime 구성
- [ ] Worker FastAPI 생성 (`/health`, `/stt`, `/lipsync`)
- [ ] Whisper 모델 pre-warm, Wav2Lip 체크포인트 부팅 시 검증

## Day 3: App API 연동
- [ ] 현재 `app/api/v1/interview.py`의 `/lipsync` 경로를 원격 job submit 방식으로 전환
- [ ] STT 호출부를 로컬 직접 실행 대신 remote adapter로 교체
- [ ] 실패 시 로컬 fallback 여부 feature flag로 제어

## Day 4: 비동기/스토리지
- [ ] S3 업로드 + presigned URL 다운로드 적용
- [ ] 큐 소비/재시도(최대 N회) + DLQ 설정
- [ ] job polling API (`GET /jobs/{job_id}`) 구현

## Day 5: 성능 튜닝
- [ ] Whisper 모델 크기(`small/medium`)별 latency 측정
- [ ] Wav2Lip batch/fps/resize_factor 기준값 재설정
- [ ] 동시 처리량(예: 5, 10, 20 동시 요청) 부하 테스트

## Day 6: 장애/보안
- [ ] 타임아웃/재시도/서킷브레이커 적용
- [ ] IAM 최소권한(S3, SQS)
- [ ] PII 로그 마스킹 + 임시파일 자동 정리

## Day 7: 전환/롤백
- [ ] 점진 전환(트래픽 10% -> 50% -> 100%)
- [ ] KPI 확인: p95 latency, 실패율, 처리 비용
- [ ] 롤백 시나리오 리허설(feature flag 즉시 원복)

---

## 6) 수용 기준(Go/No-Go)

- STT p95 latency: 기존 대비 **30% 이상 개선**
- LipSync 생성 시간: 기존 대비 **40% 이상 개선**
- 실패율: **2% 이하**
- 요청당 추정비용: 목표 예산 이내

---

## 7) 지금 바로 할 코드 작업(권장 순서)

1. `app/core/config.py`에 GPU 원격 실행용 설정 추가
2. `app/services/`에 `gpu_job_service.py` 추가 (submit/poll 추상화)
3. `app/api/v1/interview.py`의 `/lipsync`를 서비스 호출로 위임
4. STT 호출 경로를 `run_stt()` 직접 실행에서 adapter 경유로 변경
5. feature flag (`GPU_REMOTE_ENABLED=true/false`)로 안전 전환

---

## 8) 주의사항

- 현재 환경에서 `nvidia-smi` 실패 이력이 있으므로, 로컬 GPU 기준 최적화보다 AWS GPU 분리가 우선
- Wav2Lip는 모델/체크포인트 용량이 크므로 이미지 빌드와 런타임 캐시 전략 분리 필요
- 동기 API로 mp4를 직접 반환하면 타임아웃 리스크 큼 → job + S3 다운로드 방식 권장
