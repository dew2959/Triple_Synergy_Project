# 프론트엔드 사용 가이드

## 🎯 현재 사용 중인 프론트엔드

### ✅ Streamlit 프론트엔드 (활성)

**위치**: 프로젝트 루트의 `pages/` 폴더 및 `streamlit_app.py`

**실행 방법**:
```bash
# 1. 의존성 설치
pip install -r streamlit_requirements.txt

# 2. 백엔드 서버 실행 (별도 터미널)
uvicorn main:app --reload --port 8000

# 3. Streamlit 앱 실행
streamlit run streamlit_app.py
```

**접속**: `http://localhost:8501`

**문서**: `streamlit_README.md` 참고

---

---

## 💡 FAQ

**Q: 어떤 프론트엔드를 사용하나요?**
A: **Streamlit**을 사용합니다. 프로젝트 루트의 `streamlit_app.py`를 실행하면 됩니다.
