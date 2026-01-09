# final report


import json
from typing import Any, Dict, Optional, List

from app.schemas.report import (
    FinalReportDBPayload,
    FinalReportResult,
    ModuleScoreSummary,
    StrengthWeakness,
    ActionPlan,
)
from app.repositories.final_report_repo import final_report_repo


def _safe_int(x) -> Optional[int]:
    try:
        if x is None:
            return None
        return int(round(float(x)))
    except Exception:
        return None


def _compute_scores(visual_out: Dict[str, Any], voice_out: Dict[str, Any], content_out: Dict[str, Any]):
    v = _safe_int((visual_out.get("metrics") or {}).get("score"))
    a = _safe_int((voice_out.get("metrics") or {}).get("score"))
    c = _safe_int((content_out.get("metrics") or {}).get("score"))

    scores = [s for s in [v, a, c] if isinstance(s, int)]
    total = int(round(sum(scores) / len(scores))) if scores else None
    return v, a, c, total


def _build_compact(visual_out, voice_out, content_out) -> Dict[str, Any]:
    # LLM에 핵심만 넣기 (너무 많이 넣으면 흔들림)
    return {
        "visual": {
            "metrics": visual_out.get("metrics", {}),
            "events": (visual_out.get("events", [])[:10]),
        },
        "voice": {
            "metrics": voice_out.get("metrics", {}),
            "events": (voice_out.get("events", [])[:10]),
        },
        "content": {
            "metrics": content_out.get("metrics", {}),
            "events": (content_out.get("events", [])[:10]),
            # content가 별도 텍스트 피드백 키를 갖고 있으면 여기에 같이 넣어도 됨
        },
    }


def _build_prompt(compact: Dict[str, Any]) -> str:
    # 너희 DB 컬럼/스키마에 바로 매핑되는 형태로 JSON만 출력하도록 강제
    return f"""
너는 면접 피드백 리포트를 '정리'하는 편집자다.
규칙:
- 입력에 없는 사실/수치를 절대 만들지 마라.
- 출력은 반드시 JSON만(설명/마크다운 금지).
- strengths/weaknesses는 각 2~4개.
- action_plans_json은 3~7개, title/description만.

반드시 아래 스키마 그대로 출력:
{{
  "summary_headline": "한 줄 요약",
  "overall_feedback": "전체 피드백(문단)",

  "visual_summary": "visual 요약(짧게)",
  "voice_summary": "voice 요약(짧게)",
  "content_summary": "content 요약(짧게)",

  "visual_strengths_json": ["...", "..."],
  "visual_weaknesses_json": ["...", "..."],
  "voice_strengths_json": ["...", "..."],
  "voice_weaknesses_json": ["...", "..."],
  "content_strengths_json": ["...", "..."],
  "content_weaknesses_json": ["...", "..."],

  "action_plans_json": [
    {{"title":"...", "description":"..."}},
    {{"title":"...", "description":"..."}}
  ]
}}

입력:
{compact}
""".strip()


def _fallback_llm_payload() -> Dict[str, Any]:
    return {
        "summary_headline": "면접 피드백 요약",
        "overall_feedback": "분석 결과를 기반으로 핵심 개선 포인트를 정리했습니다.",
        "visual_summary": None,
        "voice_summary": None,
        "content_summary": None,
        "visual_strengths_json": [],
        "visual_weaknesses_json": [],
        "voice_strengths_json": [],
        "voice_weaknesses_json": [],
        "content_strengths_json": [],
        "content_weaknesses_json": [],
        "action_plans_json": [],
    }


class FinalReportService:
    def __init__(self, llm_client):
        self.llm = llm_client

    def create_or_upsert(
        self,
        conn,
        session_id: int,
        visual_out: Dict[str, Any],
        voice_out: Dict[str, Any],
        content_out: Dict[str, Any],
    ) -> FinalReportResult:

        v, a, c, total = _compute_scores(visual_out, voice_out, content_out)
        compact = _build_compact(visual_out, voice_out, content_out)

        # 1) LLM 호출 (실패하면 fallback)
        try:
            raw = self.llm.generate(_build_prompt(compact), temperature=0.2)  # 너희 클라이언트 함수명에 맞게
            llm_json = json.loads(raw)
        except Exception:
            llm_json = _fallback_llm_payload()

        # 2) 점수가 없으면 임시로 0 처리 (스키마가 int 필수라면)
        #    ✅ 스키마를 Optional로 바꾸면 이 블록은 제거 가능
        v_db = v if v is not None else 0
        a_db = a if a is not None else 0
        c_db = c if c is not None else 0
        total_db = total if total is not None else int(round((v_db + a_db + c_db) / 3))

        db_payload = FinalReportDBPayload(
            session_id=session_id,
            total_score=total_db,
            summary_headline=llm_json.get("summary_headline") or "면접 피드백 요약",
            overall_feedback=llm_json.get("overall_feedback") or "",

            avg_visual_score=v_db,
            avg_voice_score=a_db,
            avg_content_score=c_db,

            visual_strengths_json=llm_json.get("visual_strengths_json") or [],
            visual_weaknesses_json=llm_json.get("visual_weaknesses_json") or [],
            voice_strengths_json=llm_json.get("voice_strengths_json") or [],
            voice_weaknesses_json=llm_json.get("voice_weaknesses_json") or [],
            content_strengths_json=llm_json.get("content_strengths_json") or [],
            content_weaknesses_json=llm_json.get("content_weaknesses_json") or [],

            action_plans_json=llm_json.get("action_plans_json") or [],
        )

        # 3) upsert
        row = final_report_repo.upsert_final_report(conn, db_payload.model_dump())

        # 4) API 응답 모델로 변환
        return FinalReportResult(
            session_id=row["session_id"],
            total_score=row["total_score"],
            summary_headline=row.get("summary_headline") or "",
            overall_feedback=row.get("overall_feedback") or "",

            visual=ModuleScoreSummary(avg_score=row["avg_visual_score"], summary=llm_json.get("visual_summary")),
            voice=ModuleScoreSummary(avg_score=row["avg_voice_score"], summary=llm_json.get("voice_summary")),
            content=ModuleScoreSummary(avg_score=row["avg_content_score"], summary=llm_json.get("content_summary")),

            visual_points=StrengthWeakness(
                strengths=row.get("visual_strengths_json") or [],
                weaknesses=row.get("visual_weaknesses_json") or [],
            ),
            voice_points=StrengthWeakness(
                strengths=row.get("voice_strengths_json") or [],
                weaknesses=row.get("voice_weaknesses_json") or [],
            ),
            content_points=StrengthWeakness(
                strengths=row.get("content_strengths_json") or [],
                weaknesses=row.get("content_weaknesses_json") or [],
            ),

            action_plans=[ActionPlan(**ap) for ap in (row.get("action_plans_json") or [])],
            created_at=str(row.get("created_at")) if row.get("created_at") else None,
        )

