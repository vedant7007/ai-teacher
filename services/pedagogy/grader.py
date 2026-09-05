"""Grading and re-explanation.

Deterministic first: the taxonomy decides whether an answer betrays a known
misconception, and the taxonomy entry itself supplies the correct model, a
different-family analogy and a fresh diagnostic question. The LLM is consulted
only when nothing matches, or to enrich wording when it is available.

That ordering is deliberate. It means the whole adaptive loop, including the
five assertions that carry the 20-mark category, runs offline and instantly.
"""

from __future__ import annotations

import re
import uuid

from services.llm import router
from services.llm.schemas import (
    Beat, GradedAnswer, Question, VisualSpec,
)
from services.pedagogy import misconceptions as tax
from services.pedagogy.bkt import ConceptState, decide_action


def _looks_correct(answer: str, question: Question) -> bool:
    """Cheap correctness signal used when no misconception pattern fires."""
    a = (answer or "").strip().lower()
    if not a:
        return False
    key = (question.answer_key or "").strip().lower()

    if question.options and key:
        # MCQ: accept the option text or its letter.
        if key in a or a in key:
            return True
        for i, opt in enumerate(question.options):
            if opt.strip().lower() == key and a in {chr(97 + i), str(i + 1)}:
                return True
        return False

    if key:
        # Numeric answers compare by value, not by string.
        nums_key = re.findall(r"-?\d+\.?\d*", key)
        nums_ans = re.findall(r"-?\d+\.?\d*", a)
        if nums_key and nums_ans:
            try:
                return abs(float(nums_key[0]) - float(nums_ans[0])) < 0.01
            except ValueError:
                pass
        if key in a:
            return True

    # Fall back to rubric keyword coverage.
    if question.rubric:
        words = {w for r in question.rubric for w in re.findall(r"\w{4,}", r.lower())}
        if words:
            hit = sum(1 for w in words if w in a)
            return hit / len(words) >= 0.4
    return False


def grade(
    answer: str,
    question: Question,
    state: ConceptState,
    *,
    use_llm: bool = True,
    has_prereq: bool = False,
) -> GradedAnswer:
    """Grade one answer. Never simply says 'incorrect'."""
    hit = tax.match(answer, concept_id=question.concept_id)

    if hit:
        m = hit.misconception
        return GradedAnswer(
            correct=False,
            confidence=0.95,
            misconception_id=m.id,
            feedback=(
                f"That is a really common way to think about it, and it is worth "
                f"naming: {m.summary} Here is what is actually going on. {m.correct_model}"
            ),
            recommended_action=decide_action(state, correct=False, has_prereq=has_prereq),
            matched_by="taxonomy",
        )

    correct = _looks_correct(answer, question)
    if correct:
        return GradedAnswer(
            correct=True,
            confidence=0.8,
            misconception_id=None,
            feedback="That is right, and your reasoning matches the rubric.",
            recommended_action=decide_action(state, correct=True),
            matched_by="taxonomy",
        )

    if use_llm:
        llm = _grade_with_llm(answer, question, state, has_prereq=has_prereq)
        if llm is not None:
            return llm

    return GradedAnswer(
        correct=False,
        confidence=0.4,
        misconception_id="novel_misconception",
        feedback=(
            "That is not quite it, and I want to understand how you got there "
            "before moving on. Let me explain it a different way."
        ),
        recommended_action=decide_action(state, correct=False, has_prereq=has_prereq),
        matched_by="default",
    )


def _grade_with_llm(
    answer: str, question: Question, state: ConceptState, *, has_prereq: bool
) -> GradedAnswer | None:
    known = ", ".join(m.id for m in tax.for_concept(question.concept_id)) or "none"
    prompt = (
        "You are grading one student answer. Return ONLY JSON.\n\n"
        f"Question: {question.prompt}\n"
        f"Expected answer: {question.answer_key}\n"
        f"Rubric: {question.rubric}\n"
        f"Student answer: {answer}\n\n"
        f"Known misconceptions for this concept: {known}\n\n"
        "Fields: correct (bool), confidence (0-1), misconception_id (one of the "
        "known ids, or a new snake_case id you invent describing the specific "
        "error, or null if correct), feedback (2 sentences, name what the student "
        "was thinking, never just say incorrect).\n"
        '{"correct":false,"confidence":0.8,"misconception_id":"...","feedback":"..."}'
    )
    try:
        data = router.complete_json(prompt, purpose="grade", temperature=0.0)
    except Exception:  # noqa: BLE001 - grading must never block the lesson
        return None
    return GradedAnswer(
        correct=bool(data.get("correct")),
        confidence=float(data.get("confidence", 0.6)),
        misconception_id=data.get("misconception_id") or None,
        feedback=str(data.get("feedback") or "Let me explain that differently."),
        recommended_action=decide_action(
            state, correct=bool(data.get("correct")), has_prereq=has_prereq
        ),
        matched_by="llm",
    )


def reexplain(
    original: Beat,
    graded: GradedAnswer,
    *,
    language: str | None = None,
    used_families: set[str] | None = None,
) -> tuple[Beat, Question]:
    """Build a re-explanation beat plus a NEW diagnostic question.

    The analogy family must differ from the one the original beat used, so the
    student hears a genuinely different explanation rather than the same words
    rearranged. Both come from the taxonomy, so this needs no network.
    """
    lang = language or original.language
    entry = tax.load().get(graded.misconception_id or "")

    # Switch away from EVERY family already used to teach this concept, not just
    # the one on the beat that carried the question. A check beat often has no
    # analogy of its own, so using it alone would let us reuse the explanation's.
    used = {f for f in (used_families or set()) if f}
    if original.analogy_family:
        used.add(original.analogy_family)

    family = next(
        (f for f in ["everyday", "mechanical", "computational", "biological", "financial"]
         if f not in used),
        tax.different_family(next(iter(used), None)),
    )
    if entry and entry.analogy_family not in used:
        family = entry.analogy_family

    if entry:
        analogy = entry.preferred_analogy
        model = entry.correct_model
        q_prompt = entry.diagnostic_question
    else:
        analogy = ("Let us come at this from a different angle, with an everyday "
                   "situation rather than the formal statement.")
        model = graded.feedback
        q_prompt = "In your own words, what actually happens and why?"

    script = (
        f"{graded.feedback} Let me try a completely different picture. {analogy} "
        f"{model} Now let us check that landed."
    )

    beat = Beat(
        id=f"rx-{uuid.uuid4().hex[:6]}",
        concept_id=original.concept_id,
        intent="analogy",
        script=script,
        language=lang,
        analogy_family=family,
        visual=VisualSpec(
            kind="bullets",
            reason=(
                f"A different analogy family ({family}) rather than a repeat of the "
                f"first explanation, because restating the same picture rarely "
                f"fixes a misconception."
            ),
            payload={
                "heading": (entry.summary if entry else "Let us try this differently"),
                "items": [s.strip() for s in re.split(r"(?<=[.।])\s+", model) if s.strip()][:4],
            },
        ),
        generated_after_answer=True,
    )

    question = Question(
        id=f"dq-{uuid.uuid4().hex[:6]}",
        concept_id=original.concept_id,
        type="short",
        prompt=q_prompt,
        answer_key=(entry.correct_model if entry else ""),
        rubric=[entry.correct_model] if entry else ["Shows the correct relationship."],
        targets_misconception=graded.misconception_id,
    )
    return beat, question
