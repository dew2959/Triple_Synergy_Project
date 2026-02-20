# GPU Worker 최소 실행 가이드

## 1) .env 확인

아래 값이 설정되어 있어야 합니다.

- `GPU_REMOTE_ENABLED=true`
- `GPU_BASE_URL=http://gpu_worker:8100`
- `GPU_TIMEOUT_SEC=180`

## 2) 컨테이너 실행

프로젝트 루트에서:

- `docker-compose up --build -d`

## 2-1) 최적화 포인트

- `gpu_worker`는 이제 `Dockerfile.gpu_worker` + `requirements.gpu_worker.txt`를 사용합니다.
- 기존 전체 백엔드 의존성 대신, STT/LipSync에 필요한 최소 의존성만 설치합니다.

## 3) 헬스체크

- Worker: `http://localhost:8100/health`
- Backend: `http://localhost:8000/`
- GPU 확인: `http://localhost:8100/health/gpu`

## 4) 동작 방식

- Backend는 STT/LipSync 호출 시 **원격 GPU worker를 우선 호출**합니다.
- 원격 호출 실패 시 기존 로컬 경로로 fallback 합니다.

## 5) 바로 롤백하는 방법

- `.env`에서 `GPU_REMOTE_ENABLED=false`
- Backend 재시작

## 7) AWS/로컬 분리 실행 명령 (가장 쉬운 방식)

### A. AWS 서버(=GPU worker 서버)에서

1. 코드 받기
  - `git clone <repo-url>`
  - `cd Triple_Synergy_Project`
2. AWS 서버 `.env`에서 최소 설정
  - `OPENAI_API_KEY=...`
  - `GPU_REMOTE_ENABLED=false`
3. GPU worker만 실행
  - `docker-compose up -d --build gpu_worker`
4. 헬스체크
  - `curl http://localhost:8100/health`
5. GPU 사용 가능 여부 확인
  - `curl http://localhost:8100/health/gpu`
  - 기대값: `torch_cuda_available: true`, `torch_device_count: 1 이상`, `nvidia_smi_ok: true`

### B. 로컬(=앱 서버)에서

1. 로컬 `.env` 설정
  - `GPU_REMOTE_ENABLED=true`
  - `GPU_BASE_URL=http://<AWS_PUBLIC_IP_OR_DOMAIN>:8100`
  - `GPU_TIMEOUT_SEC=180`
2. 로컬은 앱만 실행 (gpu_worker는 실행 안 함)
  - `docker-compose up -d backend frontend db`
3. 앱이 STT/LipSync 요청 시 AWS GPU worker로 직접 호출

### C. 로컬 테스트만 할 때(같은 compose 내부)

- `GPU_BASE_URL=http://gpu_worker:8100`
- `docker-compose up -d --build gpu_worker backend frontend db`

## 6) 엔드포인트 계약(현재)

### POST /stt
- multipart form:
  - `audio`(file)
  - `model_name`(optional, default: `small`)
  - `language`(optional, default: `ko`)
- response: 기존 `run_stt()`의 v0 JSON

### POST /lipsync
- multipart form:
  - `audio`(file)
  - `avatar_url`(string)
  - `resize_factor`(int)
  - `nosmooth`(bool)
- response: `video/mp4` bytes
