"""Tiered LLM router. Every LLM call in this project goes through complete().

Tiers, by purpose:
  plan, report          -> Gemini Flash   (big structured generation, 1 per lesson)
  intake, grade, reexplain -> Groq        (cheap, frequent, low latency)
  anything, --offline   -> Ollama llama3.1:8b (fallback and offline mode)

Order of operations is always: cache -> provider -> budget log. A cache hit
never reaches a provider and never counts against the daily quota.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import httpx

from . import budget, cache

# --- config -----------------------------------------------------------------


def _load_dotenv(path: str = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("'\""))


_load_dotenv()

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b-instruct-q4_K_M")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")

OFFLINE = os.environ.get("AI_TEACHER_OFFLINE", "0") == "1"

BIG_PURPOSES = {"plan", "report"}


class AllProvidersFailed(RuntimeError):
    pass


def _chain(purpose: str) -> list[str]:
    """Provider preference for a purpose, best first."""
    if OFFLINE:
        return ["ollama"]
    if purpose in BIG_PURPOSES:
        return ["gemini", "groq", "ollama"]
    return ["groq", "gemini", "ollama"]


# --- providers --------------------------------------------------------------


def _call_gemini(prompt: str, model: str, json_mode: bool, temperature: float) -> str:
    from google import genai
    from google.genai import types

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set")
    client = genai.Client(api_key=key)
    cfg = types.GenerateContentConfig(temperature=temperature)
    if json_mode:
        cfg.response_mime_type = "application/json"
    resp = client.models.generate_content(model=model, contents=prompt, config=cfg)
    return resp.text or ""


def _call_groq(prompt: str, model: str, json_mode: bool, temperature: float) -> str:
    from groq import Groq

    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY not set")
    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
    resp = Groq(api_key=key).chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        **kwargs,
    )
    return resp.choices[0].message.content or ""


def _call_ollama(prompt: str, model: str, json_mode: bool, temperature: float) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if json_mode:
        payload["format"] = "json"
    r = httpx.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=300.0)
    r.raise_for_status()
    return r.json().get("response", "")


_PROVIDERS = {
    "gemini": (_call_gemini, lambda: GEMINI_MODEL),
    "groq": (_call_groq, lambda: GROQ_MODEL),
    "ollama": (_call_ollama, lambda: OLLAMA_MODEL),
}


# --- public API -------------------------------------------------------------


def complete(
    prompt: str,
    *,
    purpose: str,
    json_mode: bool = False,
    temperature: float = 0.3,
    use_cache: bool = True,
    force_provider: str | None = None,
) -> str:
    """Run a completion through cache, then the provider chain for `purpose`.

    Raises AllProvidersFailed only if every provider in the chain errored.
    """
    chain = [force_provider] if force_provider else _chain(purpose)
    errors: list[str] = []

    for provider in chain:
        call, model_of = _PROVIDERS[provider]
        model = model_of()
        params = {"json_mode": json_mode, "temperature": temperature}
        ck = cache.key_for(prompt, model, params)

        if use_cache:
            hit = cache.get(ck)
            if hit is not None:
                budget.record(
                    model=model, purpose=purpose, billed=False, latency_ms=0,
                    prompt_chars=len(prompt), completion_chars=len(hit),
                )
                return hit

        started = time.perf_counter()
        try:
            text = call(prompt, model, json_mode, temperature)
        except Exception as exc:  # noqa: BLE001 - any provider error falls through
            budget.record(
                model=model, purpose=purpose, billed=True,
                latency_ms=int((time.perf_counter() - started) * 1000),
                prompt_chars=len(prompt), ok=False,
            )
            errors.append(f"{provider}: {type(exc).__name__}: {exc}")
            continue

        budget.record(
            model=model, purpose=purpose, billed=True,
            latency_ms=int((time.perf_counter() - started) * 1000),
            prompt_chars=len(prompt), completion_chars=len(text),
        )
        if use_cache:
            cache.put(ck, text, model, purpose)
        return text

    raise AllProvidersFailed("; ".join(errors))


def complete_json(prompt: str, *, purpose: str, **kw) -> dict:
    """complete() plus a tolerant JSON parse. Models like to wrap JSON in prose."""
    raw = complete(prompt, purpose=purpose, json_mode=True, **kw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end > start:
            return json.loads(raw[start : end + 1])
        raise


def available() -> dict[str, bool]:
    """Which providers are usable right now. Shown at startup and in /health."""
    ollama_up = False
    try:
        ollama_up = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=2.0).status_code == 200
    except Exception:  # noqa: BLE001
        pass
    return {
        "gemini": bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")),
        "groq": bool(os.environ.get("GROQ_API_KEY")),
        "ollama": ollama_up,
        "offline_mode": OFFLINE,
    }
