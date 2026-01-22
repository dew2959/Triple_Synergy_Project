import re
import json
from typing import Any, Dict, List

_RE_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_RE_PHONE = re.compile(r"\b01[016789]-?\d{3,4}-?\d{4}\b")

# ⚠️ 팀 합의된 최소 패턴만 넣는 걸 추천
_BANNED = []

_MAX_CHARS = 10000 

def sanitize_text(text: str) -> str:
    t = (text or "").strip()
    t = _RE_EMAIL.sub("[REDACTED_EMAIL]", t)
    t = _RE_PHONE.sub("[REDACTED_PHONE]", t)
    if len(t) > _MAX_CHARS:
        t = t[:_MAX_CHARS] + "\n...[TRUNCATED]..."
    return t

def filter_or_raise(text: str, where: str = "prompt") -> None:
    for pat in _BANNED:
        if pat.search(text):
            raise ValueError(f"PromptBlocked: banned content in {where}")


