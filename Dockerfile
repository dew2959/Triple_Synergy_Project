# 1. 베이스 이미지 설정 (Python 3.10 사용)
FROM python:3.11-slim

# 2. 시스템 패키지 설치 (OpenCV, FFmpeg, 빌드 도구, PostgreSQL 빌드 도구)
# 🟢 libpq-dev 가 추가되었습니다.
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    gcc \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# 3. 작업 디렉토리 설정
WORKDIR /app

# 4. 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --upgrade pip "setuptools<70.0.0" wheel && \
    pip install --no-cache-dir numpy scipy

# 2. 나머지 패키지 설치 (--no-build-isolation 옵션 추가)
# (이 옵션이 있어야 격리된 환경에서 최신 setuptools를 몰래 다운로드하는 것을 막습니다)
RUN pip install --no-build-isolation --no-cache-dir -r requirements.txt

# 5. 프로젝트 전체 코드 복사
COPY . .

# 6. 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app