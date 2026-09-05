"""Bayesian Knowledge Tracing plus SM-2 revision scheduling.

The learner model is the differentiator: mastery is an explicit probability per
concept that moves on every graded answer, is shown on screen, and visibly
steers what gets taught next. This module is pure functions over state, with no
LLM and no I/O, so it is fast and deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

# Standard BKT parameters, as specified in the build plan.
P_INIT = 0.25      # prior probability the learner already knows a concept
P_TRANSIT = 0.15   # chance of learning it from one teaching opportunity
P_SLIP = 0.10      # chance of answering wrongly despite knowing it
P_GUESS = 0.20     # chance of answering correctly without knowing it

# Policy thresholds.
STRUGGLING = 0.40  # below this, a wrong answer triggers a different analogy
MASTERED = 0.85    # above this, skip ahead and reallocate the time


def update(p_known: float, correct: bool) -> float:
    """One BKT step. Returns the posterior probability the learner knows it."""
    p = min(max(p_known, 0.0), 1.0)
    if correct:
        num = p * (1 - P_SLIP)
        den = num + (1 - p) * P_GUESS
    else:
        num = p * P_SLIP
        den = num + (1 - p) * (1 - P_GUESS)
    posterior = num / den if den else p
    # Account for learning that happens during the attempt itself.
    return min(1.0, posterior + (1 - posterior) * P_TRANSIT)


@dataclass
class ConceptState:
    concept_id: str
    p_known: float = P_INIT
    attempts: int = 0
    correct: int = 0
    consecutive_wrong: int = 0
    # SM-2
    repetitions: int = 0
    ease: float = 2.5
    interval_days: int = 0
    due: str | None = None

    def accuracy(self) -> float:
        return self.correct / self.attempts if self.attempts else 0.0


def sm2(state: ConceptState, quality: int, today: date | None = None) -> ConceptState:
    """SuperMemo-2. `quality` 0-5, where below 3 counts as a lapse.

    A concept the learner got wrong is scheduled for tomorrow, not dropped.
    """
    today = today or date.today()
    if quality < 3:
        state.repetitions = 0
        state.interval_days = 1
    else:
        if state.repetitions == 0:
            state.interval_days = 1
        elif state.repetitions == 1:
            state.interval_days = 6
        else:
            state.interval_days = max(1, round(state.interval_days * state.ease))
        state.repetitions += 1

    state.ease = max(
        1.3,
        state.ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)),
    )
    state.due = (today + timedelta(days=state.interval_days)).isoformat()
    return state


@dataclass
class Learner:
    """The inspectable learner model shown in the UI."""

    concepts: dict[str, ConceptState] = field(default_factory=dict)
    misconceptions: dict[str, int] = field(default_factory=dict)

    def state_for(self, concept_id: str) -> ConceptState:
        return self.concepts.setdefault(concept_id, ConceptState(concept_id))

    def mastery(self) -> dict[str, float]:
        return {c: round(s.p_known, 4) for c, s in self.concepts.items()}

    def revision_plan(self) -> dict[str, str]:
        return {c: s.due for c, s in self.concepts.items() if s.due}

    def record(
        self,
        concept_id: str,
        *,
        correct: bool,
        misconception_id: str | None = None,
        today: date | None = None,
    ) -> ConceptState:
        s = self.state_for(concept_id)
        s.p_known = update(s.p_known, correct)
        s.attempts += 1
        if correct:
            s.correct += 1
            s.consecutive_wrong = 0
        else:
            s.consecutive_wrong += 1

        if misconception_id:
            self.misconceptions[misconception_id] = (
                self.misconceptions.get(misconception_id, 0) + 1
            )

        # Quality maps onto how confident the answer was, not just right/wrong.
        quality = 4 if correct else (2 if s.consecutive_wrong == 1 else 1)
        sm2(s, quality, today=today)
        return s

    def weak_concepts(self, threshold: float = STRUGGLING) -> list[str]:
        return sorted(
            (c for c, s in self.concepts.items() if s.p_known < threshold),
            key=lambda c: self.concepts[c].p_known,
        )

    def strong_concepts(self, threshold: float = MASTERED) -> list[str]:
        return sorted(
            (c for c, s in self.concepts.items() if s.p_known >= threshold),
            key=lambda c: -self.concepts[c].p_known,
        )

    def score(self) -> int:
        total = sum(s.attempts for s in self.concepts.values())
        got = sum(s.correct for s in self.concepts.values())
        return round(got / total * 100) if total else 0


def decide_action(state: ConceptState, correct: bool, *, has_prereq: bool = False) -> str:
    """Policy from the build plan, driven by the mastery estimate.

    Returned action names match GradedAnswer.recommended_action.
    """
    if correct:
        if state.p_known >= MASTERED:
            return "level_up"
        return "continue"
    if state.consecutive_wrong >= 2 and has_prereq:
        return "step_back_prereq"
    if state.p_known < STRUGGLING:
        return "reexplain_analogy"
    return "reexplain_simpler"
