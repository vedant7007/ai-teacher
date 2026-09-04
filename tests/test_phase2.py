"""Phase 2 acceptance test.

Runs against the frozen demo lesson in data/demo/, so it costs zero API requests
and cannot flake on a model's mood. The generation that produced it is recorded
in docs/EVALUATION.md.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from services.llm.schemas import LearnerProfile, LessonPlan
from services.pedagogy.planner import _intake_fallback, target_words, wpm_for

DEMO = Path("data/demo/lesson_ohms_law_hi.json")
DEVANAGARI = re.compile(r"[ऀ-ॿ]")


@pytest.fixture(scope="module")
def plan() -> LessonPlan:
    return LessonPlan(**json.loads(DEMO.read_text(encoding="utf-8")))


def test_hits_the_time_budget(plan):
    target = target_words(plan.profile)
    delta = abs(plan.total_words() - target) / target
    assert delta <= 0.10, (
        f"{plan.total_words()} words vs target {target} ({delta:.1%} off, max 10%)"
    )


def test_duration_matches_request(plan):
    minutes = plan.est_minutes(wpm_for(plan.profile.language))
    requested = plan.profile.time_budget_minutes
    assert abs(minutes - requested) / requested <= 0.10


def test_written_in_requested_language(plan):
    assert plan.profile.language == "hi-IN"
    for beat in plan.beats:
        assert DEVANAGARI.search(beat.script), f"{beat.id} is not Devanagari"


def test_every_concept_has_a_checkpoint(plan):
    checks = [b for b in plan.beats if b.intent == "check"]
    assert len(checks) >= len(plan.concepts)
    assert all(b.checkpoint is not None for b in checks)
    for b in checks:
        assert b.checkpoint.rubric, f"{b.id} checkpoint has no rubric to grade against"


def test_every_fact_beat_is_cited(plan):
    assert plan.uncited_fact_beats() == []


def test_citations_point_at_real_pages(plan):
    for beat in plan.beats:
        for c in beat.citations:
            assert 1 <= c.page_start <= c.page_end <= 24, f"{beat.id} cites page {c.page_start}"
            assert c.doc_id


def test_only_supported_visual_kinds(plan):
    allowed = {"equation", "graph", "diagram", "code", "bullets"}
    for beat in plan.beats:
        assert beat.visual.kind in allowed
        assert beat.visual.reason.strip(), f"{beat.id} visual has no stated reason"


def test_visuals_are_animated_not_static(plan):
    """Timeline cues are what make this a lesson rather than a slideshow."""
    cued = [b for b in plan.beats if b.visual.timeline]
    assert len(cued) / len(plan.beats) >= 0.5


def test_final_quiz_covers_the_lesson(plan):
    assert len(plan.final_quiz) >= 4
    assert all(q.rubric or q.options for q in plan.final_quiz)


def test_groundedness_scored_locally(plan):
    scored = [b for b in plan.beats if b.groundedness_score is not None]
    assert scored, "no beat was scored for groundedness"
    assert plan.mean_groundedness() > 0.0


def test_schema_carries_language_switch_support(plan):
    """The mid-lesson switch must be representable before Phase 6 builds it."""
    assert hasattr(plan, "language_switches")
    assert all(hasattr(b, "language") for b in plan.beats)


@pytest.mark.parametrize(
    "request_text,expect_lang,expect_minutes",
    [
        ("I am a beginner. Teach me Chapter 4 in 20 minutes. Explain it in Hindi "
         "using simple examples. Ask me questions during the lesson and test me at "
         "the end.", "hi-IN", 20),
        ("Mujhe ye Hinglish mein simple example ke saath samjhao, 10 minute mein.",
         "hinglish", 10),
        ("मुझे विद्युत धारा 15 मिनट में समझाओ", "hi-IN", 15),
    ],
)
def test_intake_fallback_is_offline_safe(request_text, expect_lang, expect_minutes):
    """The deterministic path must work with no network at all."""
    p = _intake_fallback(request_text)
    assert p.language == expect_lang
    assert p.time_budget_minutes == expect_minutes
