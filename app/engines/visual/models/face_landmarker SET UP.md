# FaceLandmarker model (MediaPipe) 다운로드 안내

이 프로젝트의 Visual 엔진은 아래 모델 파일이 필요합니다:

- `app/engines/visual/models/face_landmarker.task`

VS Code에서 `.task` 파일이 “binary라서 표시 안 됨” 경고가 떠도 정상입니다.

---

## 1) Windows (PowerShell)

프로젝트 루트(`Triple_Synergy_Project`)에서 실행:

```powershell
mkdir app\engines\visual\models -Force

Invoke-WebRequest `
  -Uri "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task" `
  -OutFile "app\engines\visual\models\face_landmarker.task"
```
## 다운로드 확인
Get-Item app\engines\visual\models\face_landmarker.task | Select-Object FullName, Length
