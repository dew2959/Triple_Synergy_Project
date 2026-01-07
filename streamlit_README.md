# AI 모의면접 - Streamlit 프론트엔드

Python 기반 Streamlit으로 구현된 AI 모의면접 서비스 프론트엔드입니다.

## 기술 스택

- **Streamlit**: Python 기반 웹 앱 프레임워크
- **Requests**: HTTP 클라이언트
- **FastAPI 백엔드**: `http://localhost:8000`에서 실행 중이어야 함

## 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r streamlit_requirements.txt
```

또는 conda 환경에서:

```bash
conda activate triple
pip install streamlit requests
```

### 2. 백엔드 서버 실행

별도 터미널에서 FastAPI 백엔드 서버를 실행합니다:

```bash
uvicorn main:app --reload --port 8000
```

### 3. Streamlit 앱 실행

```bash
streamlit run streamlit_app.py
```

또는

```bash
streamlit run pages/1_🏠_랜딩.py
```

브라우저에서 `http://localhost:8501`로 자동 열립니다.

## 프로젝트 구조

```
.
├── streamlit_app.py          # 메인 앱 (랜딩 페이지)
├── pages/                    # Streamlit 페이지들
│   ├── 1_🏠_랜딩.py         # 랜딩 페이지
│   ├── 2_📝_회원가입.py     # 회원가입
│   ├── 3_🔐_로그인.py       # 로그인
│   ├── 4_👤_온보딩.py       # 온보딩 프로필 설정
│   ├── 5_📖_서비스상세.py   # 서비스 상세 설명
│   └── 6_📊_리포트.py       # 결과 리포트
├── utils/
│   └── api_client.py         # API 통신 유틸리티
├── .streamlit/
│   └── config.toml           # Streamlit 설정
└── streamlit_requirements.txt # 의존성 파일
```

## 페이지 설명

### 1. 랜딩 페이지 (`streamlit_app.py` 또는 `pages/1_🏠_랜딩.py`)
- AI 모의면접 서비스 소개
- 로그인/회원가입 버튼
- 주요 기능 소개

### 2. 회원가입 페이지 (`pages/2_📝_회원가입.py`)
- 신규 회원 가입
- 이메일, 비밀번호, 이름 입력

### 3. 로그인 페이지 (`pages/3_🔐_로그인.py`)
- 기존 회원 로그인
- 이메일, 비밀번호 입력
- 토큰을 세션 상태에 저장

### 4. 온보딩 페이지 (`pages/4_👤_온보딩.py`)
- 프로필 설정 (이름, 직무, 경력/학력)
- 로그인 후 자동 이동

### 5. 서비스 상세 페이지 (`pages/5_📖_서비스상세.py`)
- 서비스 기능 상세 설명
- 분석 프로세스 소개

### 6. 결과 리포트 페이지 (`pages/6_📊_리포트.py`)
- 종합 평가 점수
- 종합 분석 리포트
- 모듈별 점수 (표정, 음성, 내용)
- 질문별 상세 분석
- 액션 플랜

## 세션 상태 관리

Streamlit은 `st.session_state`를 사용하여 상태를 관리합니다:

```python
# 세션 상태 설정
st.session_state.token = "access_token"
st.session_state.user = {"user_id": 1, "email": "user@example.com"}

# 세션 상태 읽기
token = st.session_state.get('token')
user = st.session_state.get('user')
```

## API 연결

프론트엔드는 백엔드 API(`http://localhost:8000`)와 통신합니다.

### API 엔드포인트

- `POST /api/v1/auth/signup` - 회원가입
- `POST /api/v1/auth/login` - 로그인
- `GET /api/v1/auth/me` - 현재 사용자 정보
- `GET /api/v1/interview/report/:sessionId` - 리포트 조회 (구현 예정)
- `POST /api/v1/interview/upload` - 영상 업로드

### 인증

로그인 시 받은 `access_token`은 `st.session_state.token`에 저장되며, 
이후 API 요청에 자동으로 포함됩니다 (`utils/api_client.py`의 `get_headers()` 함수).

## 개발 시 주의사항

1. **백엔드 서버 실행**: Streamlit 앱을 실행하기 전에 FastAPI 백엔드 서버가 실행 중이어야 합니다.

2. **포트 충돌**: Streamlit은 기본적으로 `8501` 포트를 사용합니다. 다른 포트를 사용하려면:
   ```bash
   streamlit run streamlit_app.py --server.port 8502
   ```

3. **페이지 전환**: Streamlit은 `st.switch_page()` 또는 사이드바 자동 생성 페이지를 사용합니다.

4. **세션 상태**: 페이지를 새로고침하면 세션 상태가 초기화될 수 있습니다. 
   프로덕션 환경에서는 쿠키나 서버 세션을 사용하는 것을 권장합니다.

## 다음 단계

백엔드 팀원이 리포트 API를 구현하면 다음 엔드포인트를 추가해야 합니다:

```python
# app/api/v1/interview.py에 추가 필요
@router.get("/report/{session_id}", response_model=FinalReportResult)
def get_report(session_id: int, ...):
    # 리포트 조회 로직
    pass
```

## React 프론트엔드와의 비교

| 항목 | React | Streamlit |
|------|-------|-----------|
| 언어 | TypeScript/JavaScript | Python |
| 설정 | 복잡 (package.json, build) | 간단 (pip install) |
| 상태 관리 | 복잡 (Context API, Redux) | 간단 (session_state) |
| UI 커스터마이징 | 높음 | 중간 |
| 개발 속도 | 보통 | 빠름 |
| 프로덕션 배포 | 별도 빌드 필요 | `streamlit run` |

Streamlit은 빠른 프로토타이핑과 데이터 중심 앱에 적합하며, 
Python 개발자에게 친숙한 인터페이스를 제공합니다.
