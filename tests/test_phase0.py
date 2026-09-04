"""Phase 0 acceptance test.

Asserts the two things Phase 0 promises:
  1. /health returns ok
  2. a repeated LLM call is served from disk cache and costs 0 extra requests

Runs against Ollama so it never spends Gemini or Groq quota.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from services.api.main import app
from services.llm import budget, router

client = TestClient(app)


def _ollama_up() -> bool:
    try:
        return httpx.get(f"{router.OLLAMA_URL}/api/tags", timeout=2.0).status_code == 200
    except Exception:  # noqa: BLE001
        return False


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "providers" in body and "budget" in body


@pytest.mark.skipif(not _ollama_up(), reason="ollama not running")
def test_cache_makes_repeat_call_free():
    prompt = "Reply with exactly one word: electricity"

    before = budget.today()["billed_total"]

    first = router.complete(prompt, purpose="test", force_provider="ollama", temperature=0.0)
    after_first = budget.today()
    assert after_first["billed_total"] == before + 1, "first call must be billed once"

    second = router.complete(prompt, purpose="test", force_provider="ollama", temperature=0.0)
    after_second = budget.today()

    assert second == first, "cache must return the identical response"
    assert after_second["billed_total"] == after_first["billed_total"], (
        "repeat call must cost 0 requests"
    )
    assert after_second["cached_total"] == after_first["cached_total"] + 1, (
        "repeat call must be logged as a cache hit"
    )
