"""Request accountant.

Every LLM call is logged with model, purpose, latency and token estimate.
Cache hits are logged too, with billed=False, so we can prove how many
requests the cache saved. The daily count drives the warning at 60 percent
and is surfaced in the UI trace panel.
"""

from __future__ import annotations

import json
import threading
from datetime import date
from pathlib import Path

LOG_PATH = Path(".cache/llm/budget.jsonl")

# Free-tier daily ceilings. Gemini is the scarce one, it is the only provider
# whose exhaustion breaks the demo.
DAILY_LIMITS = {"gemini": 1500, "groq": 14400, "ollama": 10**9}
WARN_AT = 0.60

_lock = threading.Lock()


def _provider(model: str) -> str:
    m = model.lower()
    if "gemini" in m:
        return "gemini"
    if "llama-3.3" in m or "groq/" in m or "openai/" in m:
        return "groq"
    return "ollama"


def record(
    *,
    model: str,
    purpose: str,
    billed: bool,
    latency_ms: int,
    prompt_chars: int = 0,
    completion_chars: int = 0,
    ok: bool = True,
) -> None:
    entry = {
        "day": date.today().isoformat(),
        "provider": _provider(model),
        "model": model,
        "purpose": purpose,
        "billed": billed,
        "latency_ms": latency_ms,
        "prompt_tokens_est": prompt_chars // 4,
        "completion_tokens_est": completion_chars // 4,
        "ok": ok,
    }
    with _lock:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    _warn_if_near_limit(entry["provider"])


def _entries(day: str | None = None) -> list[dict]:
    if not LOG_PATH.exists():
        return []
    day = day or date.today().isoformat()
    out = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("day") == day:
            out.append(e)
    return out


def today() -> dict:
    """Per-provider billed/cached counts for the trace panel."""
    entries = _entries()
    summary: dict[str, dict] = {}
    for e in entries:
        s = summary.setdefault(
            e["provider"], {"billed": 0, "cached": 0, "limit": DAILY_LIMITS.get(e["provider"], 0)}
        )
        s["billed" if e["billed"] else "cached"] += 1
    for p, s in summary.items():
        s["remaining"] = max(0, s["limit"] - s["billed"])
        s["pct_used"] = round(s["billed"] / s["limit"] * 100, 1) if s["limit"] else 0.0
    total_billed = sum(s["billed"] for s in summary.values())
    total_cached = sum(s["cached"] for s in summary.values())
    return {
        "day": date.today().isoformat(),
        "providers": summary,
        "billed_total": total_billed,
        "cached_total": total_cached,
        "requests_saved_by_cache": total_cached,
    }


def _warn_if_near_limit(provider: str) -> None:
    limit = DAILY_LIMITS.get(provider)
    if not limit:
        return
    used = sum(1 for e in _entries() if e["provider"] == provider and e["billed"])
    if used >= limit * WARN_AT:
        print(
            f"[budget] WARNING {provider}: {used}/{limit} requests used "
            f"({used / limit * 100:.0f}%)"
        )
