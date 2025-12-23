# 🚀 Triple Synergy Project

이 프로젝트는 Python 3.11 환경에서 동작하며, `Whisper`, `Mediapipe`, `Librosa`, `MoviePy` 등을 사용합니다.
팀원 간 환경 충돌(DLL 오류, 버전 호환성 등)을 방지하기 위해 **반드시 아래 가이드에 따라 설치**해 주세요.

## 🛠️ 사전 준비 (Prerequisites)
* **Anaconda (또는 Miniconda)** 가 설치되어 있어야 합니다.
* 설치 시 `Skip registration`으로 가입 없이 설치 가능합니다.

---

## 💻 환경 설정 가이드 (Installation)

### 1. 가상환경 생성 (Anaconda Prompt 사용)
**주의:** 반드시 `conda-forge` 채널을 사용하여 생성해야 충돌이 없습니다.

```bash
# 가상환경 이름: triple, 파이썬 버전: 3.11
conda create -n triple -c conda-forge python=3.11 -y
```
### 2. 가상환경 활성화 
```bash
conda activate triple
```
### 3. 시스템 라이브러리 설치 (DLL 오류 방지)
```bash
conda install -c conda-forge ffmpeg glib gettext libffi gdk-pixbuf -y
```
### 4. 파이썬 라이브러리 설치 (requirements.txt 이용)
```bash
#(깃허브에서 프로젝트 받은 폴더로 이동한 뒤 실행)
pip install -r requirements.txt

##만약 requirements.txt로 설치 실패하면 이렇게 강제로 지정해서 설치하면 됨 
pip install moviepy==1.0.3 decorator==4.4.2 "numpy<2.4" openai-whisper mediapipe librosa opencv-python supabase requests openai python-dotenv
```
<br />
<br />
     
## 앞으로 라이브러리가 추가될 때는 규칙을 따라주세요 
### 1. 설치한 사람 : 설치하고 나서 requirments.txt를 업데이트해서 깃허브에 올립니다. 
```bash
pip install pandas
pip freeze > requirements.txt
```
### 2. 나머지 팀원 : 깃허브에서 변경 사항을 받고, 다시 설치 명령어를 한 번 실행해 줍니다.
```bash
git pull
pip install -r requirements.txt
```
<br />
<br />

## .gitignore 를 준수해주세요 
### 아래 파일들은 절대 GitHub에 올리지 않습니다. 
- triple/, venv/, .venv/ (가상환경 폴더)
- .env (API Key)
- .vscode/ (개인 설정)
- __pycache__/
- 대용량 미디어 파일 (.mp4, .mp3 등)

