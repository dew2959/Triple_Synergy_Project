# Engine Raw Output Contract (v0)

모든 엔진(visual/voice/stt/content)은 아래 형태의 dict를 반환한다.

## Output (always)
{
  "module": "visual|voice|stt|content",
  "metrics": {},      # 없으면 {}
  "events": [],       # 없으면 []
  "error": null       # 성공: null, 실패: {"type": "...", "message": "..."}
}

## Rules
- 키(module/metrics/events/error)는 항상 존재한다.
- 실패 시에도 예외로 터뜨리지 말고 error를 채워 반환한다.
- metrics는 dict, events는 list 타입을 항상 유지한다.
- (옵션) artifacts는 필요해지면 {"video_path": "...", "audio_path": "..."} 형태로 추가 가능.
