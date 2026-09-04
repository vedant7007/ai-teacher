"""Disk cache for LLM responses, keyed by SHA256 of (prompt, model, params).

A repeated call costs zero API requests. This exists so that development,
tests and re-runs of the demo never touch the daily quota.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

CACHE_DIR = Path(".cache/llm")


def key_for(prompt: str, model: str, params: dict) -> str:
    blob = json.dumps(
        {"prompt": prompt, "model": model, "params": params},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def get(cache_key: str) -> str | None:
    path = CACHE_DIR / f"{cache_key}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))["text"]
    except (json.JSONDecodeError, KeyError, OSError):
        # A truncated or corrupt entry must never break a lesson, just miss.
        return None


def put(cache_key: str, text: str, model: str, purpose: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"text": text, "model": model, "purpose": purpose, "at": time.time()}
    path = CACHE_DIR / f"{cache_key}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)  # atomic, so a killed run cannot leave a half-written entry


def stats() -> dict:
    if not CACHE_DIR.exists():
        return {"entries": 0, "bytes": 0}
    files = list(CACHE_DIR.glob("*.json"))
    return {"entries": len(files), "bytes": sum(f.stat().st_size for f in files)}
