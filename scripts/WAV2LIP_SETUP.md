```md
# Wav2Lip 립싱크 기능 공유 문서 (팀원용)

우리 프로젝트에서 **TTS 오디오 + 면접관 아바타 이미지(URL)**로 **립싱크 mp4**를 생성하기 위해 Wav2Lip을 추가했습니다.  
팀원이 로컬에서 동일하게 실행할 수 있도록 **폴더 구조 / 설치 / 실행 / 주의사항**을 한 번에 정리합니다.

---

## 1) 한 줄 요약

- FastAPI가 `third_party/Wav2Lip/inference.py`를 subprocess로 실행해 **mp4를 생성**하고, Streamlit이 그 mp4를 **재생**합니다.
- 팀원 PC에도 Wav2Lip repo + 체크포인트 + face detector 파일이 **반드시** 있어야 합니다.
- 이 파일들은 `scripts/fetch_wav2lip_assets.py`로 자동 다운로드합니다.

---

## 2) 프로젝트 폴더 구조 (추가된 것)

프로젝트 루트 기준:



TRIPLE_SYNERGY_PROJECT/
├─ app/
├─ pages/
├─ uploads/
├─ temp/
├─ scripts/
│ └─ fetch_wav2lip_assets.py # ✅ Wav2Lip + 모델 파일 자동 다운로드 스크립트
├─ third_party/
│ └─ Wav2Lip/ # ✅ Wav2Lip repo (git clone 위치)
│ ├─ inference.py # 립싱크 추론 실행 파일
│ ├─ audio.py # mel-spectrogram 관련
│ ├─ checkpoints/
│ │ └─ wav2lip_gan.pth # ✅ 립싱크 모델 체크포인트 (약 416MB)
│ └─ face_detection/
│ └─ detection/
│ └─ sfd/
│ └─ s3fd.pth # ✅ face detector (약 86MB)
├─ environment.yml
├─ streamlit-app.py
├─ main.py
└─ ...

````

---

## 3) 팀원이 해야 할 세팅(필수)

### Step 0. 가상환경 세팅 (기존대로)
```bash
conda env create -f environment.yml
conda activate triple   # (실제 env 이름에 맞게)
````

### Step 1. ffmpeg 설치 확인 (필수)

FastAPI가 오디오를 16k mono wav로 변환하고, (옵션) mp4 후처리에도 ffmpeg를 씁니다.

```bash
ffmpeg -version
```

* 안 되면:

  * conda 사용 시: `conda install -c conda-forge ffmpeg`
  * 또는 시스템 설치 후 PATH 등록

### Step 2. Wav2Lip 자산 다운로드 (필수)

프로젝트 루트에서 실행:

```bash
python scripts/fetch_wav2lip_assets.py
```

성공 시 생성되는 파일(중요):

* `third_party/Wav2Lip/` (repo clone)
* `third_party/Wav2Lip/checkpoints/wav2lip_gan.pth`
* `third_party/Wav2Lip/face_detection/detection/sfd/s3fd.pth`

---

## 4) 실행 흐름 (우리 코드 기준)

### Streamlit

* 질문 텍스트 → `/api/v1/interview/tts`로 mp3 생성
* 생성된 mp3 bytes + avatar_url을 `/api/v1/interview/lipsync`로 전송
* 응답 mp4 bytes를 `st.video()`로 재생
* 실패하면 `st.audio()`로 fallback

### FastAPI (lipsync endpoint)

1. `avatar_url` 이미지 다운로드
2. 업로드된 오디오 저장
3. `ffmpeg`로 16k mono wav 변환
4. `third_party/Wav2Lip/inference.py` 실행 → `result.mp4` 생성
5. (옵션) `ffmpeg` 후처리(업스케일 + 샤픈) → `result_enhanced.mp4`
6. 최종 mp4 bytes 반환

---

## 5) 중요한 주의사항(자주 실수)

### (A) avatar_url은 “웹 이미지 파일 URL”만 가능

FastAPI는 서버에서 `requests.get(avatar_url)`로 이미지를 받습니다.

* ✅ 가능: `https://....something.jpg` / `https://....something.png`
* ❌ 불가: `C:\Users\...\image.jpg` (로컬 경로)
* ❌ 불가: `https://freepik.com/...htm` (웹페이지 HTML 링크)

> 페이지 링크가 아니라 **이미지 파일 자체 링크(.jpg/.png)**여야 합니다.

---

## 6) 디버깅 / 에러 확인

립싱크 실패 시 FastAPI 응답에 temp 폴더 경로가 포함됩니다:

예)
`wav2lip inference failed. See logs in: C:\Users\...\Temp\wav2lip_xxxxx`

해당 폴더에서 확인:

* `wav2lip_stderr.txt`
* `wav2lip_stdout.txt`
* `ffmpeg_stderr.txt`
* `ffmpeg_stdout.txt`
* (후처리 시) `enhance_stderr.txt`, `enhance_stdout.txt`

---

## 7) Git 관리(필수 권장)

모델 파일이 매우 큽니다. 레포에 커밋하지 않도록 `.gitignore`에 추가 권장:

```
third_party/Wav2Lip/checkpoints/*.pth
third_party/Wav2Lip/face_detection/**/s3fd.pth
third_party/Wav2Lip/*.pth
```

팀원은 대신 `python scripts/fetch_wav2lip_assets.py`로 받는 구조를 유지합니다.

---

## 8) 체크리스트 (팀원용)

* [ ] `conda activate triple` (프로젝트 env 활성화)
* [ ] `ffmpeg -version` 정상 출력
* [ ] `python scripts/fetch_wav2lip_assets.py` 실행 완료
* [ ] `third_party/Wav2Lip/checkpoints/wav2lip_gan.pth` 존재
* [ ] `third_party/Wav2Lip/face_detection/detection/sfd/s3fd.pth` 존재
* [ ] FastAPI 실행 → Streamlit 실행 → lipsync 동작 확인

끝.

```
::contentReference[oaicite:0]{index=0}
```
