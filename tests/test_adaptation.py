"""THE test. Section 14 of the build plan.

On a wrong answer to the Ohm's law checkpoint, the system must:
  1. name the misconception,
  2. re-explain with a DIFFERENT analogy family,
  3. issue a NEW diagnostic question on the same concept,
  4. decrease mastery for that concept,
  5. add the concept to the revision plan with an SM-2 due date.

Every assertion runs offline with `use_llm=False`. The misconception match is
deterministic, so this cannot flake on a network call and costs zero requests.
"""

from __future__ import annotations

from datetime import date

import pytest

from services.llm.schemas import (
    Beat, Concept, LearnerProfile, LessonPlan, Question, VisualSpec,
)
from services.pedagogy import misconceptions as tax
from services.pedagogy.bkt import P_INIT
from services.pedagogy.orchestrator import Session

WRONG_ANSWER = "Current increases."
CONCEPT = "ohms_law"


def _plan() -> LessonPlan:
    """A minimal Ohm's law lesson: one explanation, one checkpoint, one follow-on."""
    explain = Beat(
        id="b1", concept_id=CONCEPT, intent="explain",
        script=(
            "Think of a water pipe driven by a pump. The pump pressure is the "
            "voltage and the flow rate is the current."
        ),
        language="en-IN",
        analogy_family="mechanical",   # the re-explanation must NOT reuse this
        visual=VisualSpec(kind="equation", reason="The formula being introduced.",
                          payload={"latex": "V = I R"}),
    )
    check = Beat(
        id="b2", concept_id=CONCEPT, intent="check",
        script="Let us check that. Here is my question.",
        language="en-IN",
        visual=VisualSpec(kind="bullets", reason="The question on screen.",
                          payload={"heading": "Check", "items": ["V constant"]}),
        checkpoint=Question(
            id="q1", concept_id=CONCEPT, type="short",
            prompt=(
                "What happens to the current if the resistance increases while "
                "the voltage stays constant?"
            ),
            answer_key="The current decreases, because I = V/R.",
            rubric=["Current decreases", "inversely proportional", "I = V/R"],
            targets_misconception="ohms_law_inverse_confusion",
        ),
    )
    after = Beat(
        id="b3", concept_id=CONCEPT, intent="example",
        script="Now a worked example with real numbers.",
        language="en-IN",
        visual=VisualSpec(kind="equation", reason="Applying the formula.",
                          payload={"latex": "I = V/R"}),
    )
    return LessonPlan(
        title="Ohm's Law",
        profile=LearnerProfile(level="beginner", language="en-IN",
                               time_budget_minutes=20, topic="11.4"),
        concepts=[Concept(id=CONCEPT, name="Ohm's Law",
                          analogy_families=["mechanical", "everyday", "financial"])],
        beats=[explain, check, after],
    )


@pytest.fixture
def outcome():
    s = Session(plan=_plan())
    s.start()
    check = s.plan.beats[1]
    result = s.answer(WRONG_ANSWER, beat=check, use_llm=False, today=date(2026, 9, 5))
    return s, result


# --- the five assertions ----------------------------------------------------


def test_1_names_the_misconception(outcome):
    _, r = outcome
    assert r["graded"].misconception_id == "ohms_law_inverse_confusion"
    assert r["graded"].matched_by == "taxonomy", "must not need a model call"
    assert not r["graded"].correct
    # Forbidden from ever just saying "incorrect".
    fb = r["graded"].feedback.lower()
    assert len(fb) > 40 and fb.strip() not in {"incorrect", "wrong"}


def test_2_reexplains_with_a_different_analogy_family(outcome):
    s, r = outcome
    original = s.plan.beats[0]
    assert r["new_beats"], "no re-explanation was generated"
    new = r["new_beats"][0]
    assert new.analogy_family, "re-explanation records no analogy family"
    assert new.analogy_family != original.analogy_family, (
        f"reused the {original.analogy_family!r} family instead of switching"
    )
    assert new.analogy_family in tax.ANALOGY_FAMILIES
    assert new.generated_after_answer is True


def test_3_issues_a_new_diagnostic_question(outcome):
    s, r = outcome
    q = r["new_question"]
    assert q is not None, "no new diagnostic question"
    assert q.concept_id == CONCEPT, "question must target the same concept"
    assert q.id != s.plan.beats[1].checkpoint.id, "must be a NEW question"
    assert q.prompt.strip() and q.prompt != s.plan.beats[1].checkpoint.prompt
    assert q.targets_misconception == "ohms_law_inverse_confusion"


def test_4_mastery_decreases(outcome):
    s, r = outcome
    assert r["mastery_after"] < r["mastery_before"], (
        f"mastery went {r['mastery_before']} -> {r['mastery_after']}"
    )
    assert s.learner.mastery()[CONCEPT] < P_INIT


def test_5_concept_enters_the_revision_plan(outcome):
    s, _ = outcome
    plan = s.learner.revision_plan()
    assert CONCEPT in plan, "concept was not scheduled for revision"
    due = date.fromisoformat(plan[CONCEPT])
    assert due > date(2026, 9, 5), "due date must be in the future"


# --- supporting behaviour ---------------------------------------------------


def test_the_whole_loop_costs_zero_requests(outcome):
    """The 20-mark path must not depend on a network call."""
    s, r = outcome
    assert r["graded"].matched_by == "taxonomy"
    stages = [e.stage for e in s.trace]
    assert stages[:2] == ["understand", "plan"]
    assert "question" in stages and "evaluate" in stages and "adapt" in stages


def test_reexplanation_is_spliced_after_the_checkpoint(outcome):
    s, r = outcome
    ids = [b.id for b in s.beats()]
    new_id = r["new_beats"][0].id
    assert new_id in ids, "re-explanation never reaches the playback order"
    assert ids.index(new_id) == ids.index("b2") + 1, "must follow the checkpoint"


def test_a_correct_answer_does_not_adapt():
    s = Session(plan=_plan())
    s.start()
    r = s.answer("The current decreases, because I = V/R.",
                 beat=s.plan.beats[1], use_llm=False, today=date(2026, 9, 5))
    assert r["graded"].correct
    assert r["new_beats"] == [] and r["new_question"] is None
    assert r["mastery_after"] > r["mastery_before"]


def test_two_wrong_answers_step_back_to_the_prerequisite():
    plan = _plan()
    plan.concepts[0].prerequisites = ["potential_difference"]
    s = Session(plan=plan)
    s.start()
    check = plan.beats[1]
    s.answer(WRONG_ANSWER, beat=check, use_llm=False)
    second = s.answer(WRONG_ANSWER, beat=check, use_llm=False)
    assert second["graded"].recommended_action == "step_back_prereq"


def test_mastery_recovers_after_correct_answers():
    """The demo shows the bar drop then recover. It must actually do that."""
    s = Session(plan=_plan())
    s.start()
    check = s.plan.beats[1]
    low = s.answer(WRONG_ANSWER, beat=check, use_llm=False)["mastery_after"]
    for _ in range(3):
        out = s.answer("The current decreases, because I = V/R.",
                       beat=check, use_llm=False)
    assert out["mastery_after"] > low


def test_taxonomy_is_substantial():
    st = tax.stats()
    assert st["count"] >= 30, f"only {st['count']} misconceptions"
    assert len(st["subjects"]) >= 5, st["subjects"]
