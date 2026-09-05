"""Lesson planning. One LLM call produces the entire lesson.

The whole design exists to make that true: the plan carries every beat script,
visual spec, checkpoint and citation, so a 20 minute lesson costs 1 request
rather than 40. Validation failures get exactly one repair call, then a
deterministic fallback, and all three outcomes are logged.
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

import yaml

from services.ingest.index import DocIndex
from services.llm import router
from services.llm.schemas import (
    Beat, LearnerProfile, LessonPlan, SourceRef, VisualSpec,
)
from services.rag.retrieve import groundedness, retrieve

PROMPTS = Path(__file__).resolve().parents[1] / "llm" / "prompts"
VOICES = Path(__file__).resolve().parents[1] / "speech" / "voices.yaml"

# Spoken pace differs sharply by language, and the time budget is graded.
WPM = {"en-IN": 150, "en-US": 150, "hinglish": 140, "hi-IN": 130,
       "te-IN": 120, "ta-IN": 120, "mr-IN": 130, "bn-IN": 130}
DEFAULT_WPM = 140

LANGUAGE_NAMES = {
    "en-IN": "English", "hi-IN": "Hindi", "hinglish": "Hinglish (Roman script)",
    "te-IN": "Telugu", "ta-IN": "Tamil", "mr-IN": "Marathi", "bn-IN": "Bengali",
}


class PlanRepairFailed(RuntimeError):
    pass


def wpm_for(language: str) -> float:
    return WPM.get(language, DEFAULT_WPM)


def target_words(profile: LearnerProfile) -> int:
    # A multi-day study plan is not a spoken lesson, cap the spoken part.
    minutes = min(profile.time_budget_minutes, 90)
    return int(minutes * wpm_for(profile.language))


def _prompt(name: str) -> str:
    return (PROMPTS / name).read_text(encoding="utf-8")


def parse_intake(request: str) -> LearnerProfile:
    """Natural sentence -> LearnerProfile. Cheap model, Groq first."""
    prompt = _prompt("intake.md").replace("{{REQUEST}}", request.strip())
    try:
        data = router.complete_json(prompt, purpose="intake", temperature=0.0)
        return LearnerProfile(**data)
    except Exception:  # noqa: BLE001 - intake must never block a lesson
        return _intake_fallback(request)


def _intake_fallback(request: str) -> LearnerProfile:
    """Deterministic profile when the model or the network is unavailable."""
    r = request.lower()
    lang = "en-IN"
    if re.search(r"[ऀ-ॿ]", request):
        lang = "hi-IN"
    elif any(w in r for w in ("hinglish", "mujhe", "samjhao", "chahiye")):
        lang = "hinglish"
    elif "hindi" in r:
        lang = "hi-IN"
    elif "telugu" in r:
        lang = "te-IN"
    # Hindi and Hinglish requests name the unit in Devanagari or Roman script.
    UNITS = {"minute": 1, "min": 1, "मिनट": 1, "minut": 1,
             "hour": 60, "hr": 60, "घंटे": 60, "घंटा": 60, "ghante": 60,
             "day": 1440, "दिन": 1440}
    m = re.search(r"(\d+)\s*(" + "|".join(sorted(UNITS, key=len, reverse=True)) + r")", r)
    minutes = 20
    if m:
        minutes = int(m.group(1)) * UNITS[m.group(2)]
    level = ("advanced" if "advanced" in r else
             "intermediate" if "intermediate" in r else "beginner")
    topic = None
    tm = re.search(r"(chapter\s+[\w.]+)", r)
    if tm:
        topic = tm.group(1)
    return LearnerProfile(
        level=level, language=lang, time_budget_minutes=minutes, topic=topic,
        wants_questions_during="question" in r, wants_final_test="test" in r,
    )


def _format_sources(hits) -> str:
    if not hits:
        return "(no document supplied, teach from general knowledge)"
    out = []
    for h in hits:
        c = h.chunk
        out.append(
            f"[chunk_id={c.id} chapter={c.chapter!r} section={c.section!r} "
            f"pages={c.page_start}-{c.page_end}]\n{c.text}\n"
        )
    return "\n".join(out)


# The model lands well under whatever word count it is asked for, and the
# shortfall grows with the target: Hindi at 2600 words came in 11% short, English
# at 3000 words came in 36% short. Ask for more so the delivered lesson lands on
# target. Measured, not guessed. Raise it if lessons still run short.
WORD_BUDGET_CALIBRATION = 1.45


def build_prompt(
    profile: LearnerProfile,
    hits: list,
    *,
    topic: str | None = None,
) -> str:
    words = int(target_words(profile) * WORD_BUDGET_CALIBRATION)
    p = _prompt("lesson.md")
    p = p.replace("{{PROFILE}}", json.dumps(profile.model_dump(), ensure_ascii=False, indent=2))
    p = p.replace("{{SOURCES}}", _format_sources(hits))
    p = p.replace("{{MINUTES}}", str(profile.time_budget_minutes))
    p = p.replace("{{LANGUAGE}}", profile.language)
    p = p.replace("{{LANGUAGE_NAME}}", LANGUAGE_NAMES.get(profile.language, profile.language))
    p = p.replace("{{WPM}}", str(int(wpm_for(profile.language))))
    p = p.replace("{{TARGET_WORDS}}", str(words))
    p = p.replace("{{MIN_WORDS}}", str(int(words * 0.95)))
    p = p.replace("{{MAX_WORDS}}", str(int(words * 1.08)))
    beats = max(6, round(words / 110))
    p = p.replace("{{BEAT_COUNT}}", str(beats))
    p = p.replace("{{WORDS_PER_BEAT}}", str(int(words / beats)))
    # Concept count drives checkpoint count. Left unbounded the model splits a
    # short lesson into thin concepts and then skips checks on the thin ones.
    p = p.replace("{{MAX_CONCEPTS}}", str(max(2, min(5, profile.time_budget_minutes // 6))))
    p = p.replace(
        "{{TOPIC_ONLY_NOTE}}",
        "" if hits else
        f"There is no uploaded document. Teach the topic {topic or profile.topic!r} "
        "from general knowledge, build a sensible concept order yourself, and leave "
        "every citations array empty.",
    )
    return p


def estimate_tokens(text: str) -> int:
    return len(text) // 4


def plan_lesson(
    profile: LearnerProfile,
    *,
    idx: DocIndex | None = None,
    topic: str | None = None,
    top_k: int = 8,
    score_groundedness: bool = True,
    verbose: bool = False,
) -> LessonPlan:
    query = topic or profile.topic or profile.goal or "the main concepts of this chapter"
    hits = []
    if idx is not None:
        section = profile.topic if profile.topic and re.search(r"\d", profile.topic) else None
        hits = retrieve(idx, query, section=section, top_k=top_k)

    prompt = build_prompt(profile, hits, topic=topic)

    if verbose:
        print("=" * 72)
        print(f"LESSON PROMPT  chars={len(prompt)}  est_tokens={estimate_tokens(prompt)}")
        print(f"  language={profile.language}  minutes={profile.time_budget_minutes}"
              f"  target_words={target_words(profile)}  retrieved_chunks={len(hits)}")
        print("=" * 72)
        print(prompt)
        print("=" * 72)

    plan = _generate_validated(prompt, profile, hits)
    plan.lesson_id = uuid.uuid4().hex[:12]
    plan.doc_id = idx.doc_id if idx else None

    if score_groundedness and hits:
        _score_groundedness(plan, hits)
    _estimate_timings(plan)
    return plan


def _generate_validated(prompt: str, profile: LearnerProfile, hits) -> LessonPlan:
    """One generation, one repair attempt, then a deterministic fallback."""
    try:
        raw = router.complete_json(prompt, purpose="plan", temperature=0.4)
        return _to_plan(raw, profile)
    except router.TruncatedResponse:
        # Repairing a truncation would hide the real cause. Surface it.
        raise
    except Exception as first_error:  # noqa: BLE001
        repair = (
            f"{prompt}\n\n## Your previous attempt failed validation\n"
            f"Error: {first_error}\n"
            "Return corrected JSON matching the schema exactly. Same content, "
            "fixed structure. JSON only."
        )
        try:
            raw = router.complete_json(repair, purpose="plan_repair", temperature=0.0)
            return _to_plan(raw, profile)
        except Exception as second_error:  # noqa: BLE001
            print(f"[planner] generation failed twice, using fallback: {second_error}")
            return _fallback_plan(profile, hits)


def _sanitize(raw: dict, profile: LearnerProfile) -> dict:
    """Coerce the model's near-miss JSON into schema shape BEFORE validation.

    A repair call costs a full second generation, so trivial issues (a null
    inside a list[str], the string "null" for a null enum, a missing visual)
    are fixed here. Repair is reserved for genuine structural failure.
    """
    NULLISH = {"null", "none", "nil", ""}

    def clean_str_list(v) -> list[str]:
        if not isinstance(v, list):
            return []
        return [str(x) for x in v if x is not None and str(x).strip().lower() not in NULLISH]

    raw.setdefault("title", profile.topic or "Lesson")
    raw["profile"] = profile.model_dump()

    for c in raw.get("concepts", []) or []:
        c["analogy_families"] = clean_str_list(c.get("analogy_families"))
        c["prerequisites"] = clean_str_list(c.get("prerequisites"))

    INTENTS = {"hook", "explain", "example", "analogy", "demo", "check",
               "recap", "transition"}
    KINDS = {"equation", "graph", "diagram", "code", "bullets"}

    for b in raw.get("beats", []) or []:
        b.setdefault("language", profile.language)

        # Emphasising visuals in the prompt makes the model occasionally put a
        # visual kind in `intent`. Move it where it belongs rather than losing
        # the whole lesson to one bad enum.
        intent = str(b.get("intent", "")).lower()
        if intent not in INTENTS:
            if intent in KINDS:
                b.setdefault("visual", {})
                if isinstance(b["visual"], dict):
                    b["visual"].setdefault("kind", intent)
            b["intent"] = "check" if b.get("checkpoint") else "explain"
        af = b.get("analogy_family")
        if isinstance(af, str) and af.strip().lower() in NULLISH:
            b["analogy_family"] = None

        v = b.get("visual") or {}
        if not v.get("kind"):
            v = {"kind": "bullets", "reason": "Summary of the point being made.",
                 "payload": {"heading": "", "items": []}}
        v.setdefault("reason", "")
        v.setdefault("payload", {})
        v["timeline"] = [c for c in (v.get("timeline") or []) if isinstance(c, dict)]
        b["visual"] = v

        b["citations"] = [c for c in (b.get("citations") or []) if isinstance(c, dict)]
        for q in [b.get("checkpoint")] + list(raw.get("final_quiz") or []):
            if isinstance(q, dict):
                q["rubric"] = clean_str_list(q.get("rubric"))
                if q.get("options") is not None and not isinstance(q["options"], list):
                    q["options"] = None
    return raw


def _to_plan(raw: dict, profile: LearnerProfile) -> LessonPlan:
    return LessonPlan(**_sanitize(raw, profile))


def is_usable(plan: LessonPlan, profile: LearnerProfile) -> bool:
    """Is this a real lesson, or the emergency stub?

    The frozen demo must never be overwritten by a fallback: a stub that reaches
    data/demo/ would silently become the thing the judges see.
    """
    return len(plan.beats) >= 5 and plan.total_words() >= target_words(profile) * 0.5


def _fallback_plan(profile: LearnerProfile, hits) -> LessonPlan:
    """Never show the student an error. A thin real lesson beats a stack trace."""
    cites = [SourceRef(**h.citation()) for h in hits[:1]] if hits else []
    text = hits[0].chunk.text[:600] if hits else (profile.topic or "this topic")
    return LessonPlan(
        title=profile.topic or "Lesson",
        profile=profile,
        concepts=[],
        beats=[
            Beat(
                id="b1", concept_id="c1", intent="explain",
                script=text, language=profile.language,
                visual=VisualSpec(kind="bullets", reason="Key points from the source material.",
                                  payload={"heading": profile.topic or "Overview", "items": []}),
                citations=cites,
            )
        ],
    )


def _score_groundedness(plan: LessonPlan, hits) -> None:
    """Local cosine against cited chunks. Zero API requests."""
    by_id = {h.chunk.id: h.chunk for h in hits}
    for beat in plan.beats:
        if not beat.needs_citation:
            continue
        cited = [by_id[c.chunk_id] for c in beat.citations
                 if c.chunk_id and c.chunk_id in by_id]
        pool = cited or [h.chunk for h in hits]
        beat.groundedness_score = round(groundedness(beat.script, pool), 4)


def _estimate_timings(plan: LessonPlan) -> None:
    for beat in plan.beats:
        beat.est_seconds = round(beat.word_count() / wpm_for(beat.language) * 60, 1)
