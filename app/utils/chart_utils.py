#차트 데이터를 계산하는 로직
def calculate_cps_flow(segments: list) -> list:
    """
    Whisper 세그먼트를 받아서 시간대별 CPS(초당 글자수) 리스트로 변환
    """
    chart_data = []
    if not segments:
        return chart_data

    for seg in segments:
        start = seg.get('start', 0)
        end = seg.get('end', 0)
        text = seg.get('text', '').strip()
        
        duration = end - start
        char_count = len(text.replace(" ", "")) # 공백 제외
        
        # 0.5초 이상 말한 구간만 유효 데이터로 인정 (노이즈 필터링)
        if duration > 0.5:
            cps = round(char_count / duration, 2)
            mid_time = round((start + end) / 2, 2)
            
            chart_data.append({
                "time": mid_time,
                "cps": cps,
                "text": text  # 툴팁용 (선택사항)
            })
            
    return chart_data