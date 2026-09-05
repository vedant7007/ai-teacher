"""The adaptive loop.

Understand -> Plan -> Explain -> Demonstrate -> Question -> Evaluate -> Adapt
-> Continue.

Every transition is logged and rendered in the trace panel, because the claim
being made is that pedagogy is explicit state rather than a prompt's mood.
Plain Python: no LangChain, no agent framework, nothing hiding the architecture
we are being graded on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from services.llm.schemas import Beat, GradedAnswer, LessonPlan, Question
from services.pedagogy import grader
from services.pedagogy.bkt import Learner, MASTERED


@dataclass
class TraceEvent:
    at: str
    stage: str
    detail: dict

    def to_dict(self) -> dict:
        return {"at": self.at, "stage": self.stage, **self.detail}


@dataclass
class Session:
    """One student working through one lesson plan."""

    plan: LessonPlan
    learner: Learner = field(default_factory=Learner)
    trace: list[TraceEvent] = field(default_factory=list)
    position: int = 0
    injected: list[Beat] = field(default_factory=list)
    pending_question: Question | None = None
    skipped: list[str] = field(default_factory=list)

    # --- trace ---------------------------------------------------------------

    def log(self, stage: str, **detail) -> None:
        self.trace.append(
            TraceEvent(datetime.now().isoformat(timespec="seconds"), stage, detail)
        )

    def trace_dicts(self) -> list[dict]:
        return [e.to_dict() for e in self.trace]

    # --- playback ------------------------------------------------------------

    def beats(self) -> list[Beat]:
        """The plan's beats with any re-explanations spliced in."""
        out: list[Beat] = []
        by_after: dict[str, list[Beat]] = {}
        for b in self.injected:
            by_after.setdefault(b.concept_id, []).append(b)
        for b in self.plan.beats:
            if b.id in self.skipped:
                continue
            out.append(b)
            if b.intent == "check":
                out.extend(by_after.pop(b.concept_id, []))
        for rest in by_after.values():
            out.extend(rest)
        return out

    def current_beat(self) -> Beat | None:
        bs = self.beats()
        return bs[self.position] if 0 <= self.position < len(bs) else None

    def start(self) -> None:
        self.log(
            "understand",
            level=self.plan.profile.level,
            language=self.plan.profile.language,
            minutes=self.plan.profile.time_budget_minutes,
        )
        self.log(
            "plan",
            concepts=[c.id for c in self.plan.concepts],
            beats=len(self.plan.beats),
        )

    # --- the adaptive step ---------------------------------------------------

    def answer(
        self,
        text: str,
        *,
        beat: Beat | None = None,
        use_llm: bool = True,
        today: date | None = None,
    ) -> dict:
        """Grade an answer and adapt. This is the money shot.

        Returns everything the UI and the demo need to show that the response
        was produced BY the answer, not scripted before it.
        """
        beat = beat or self.current_beat()
        if beat is None or beat.checkpoint is None:
            raise ValueError("no checkpoint at the current position")

        question = beat.checkpoint
        concept_id = question.concept_id or beat.concept_id or "unknown"
        state = self.learner.state_for(concept_id)
        before = state.p_known

        self.log("question", beat=beat.id, question=question.id, concept=concept_id)

        has_prereq = any(
            c.id == concept_id and c.prerequisites for c in self.plan.concepts
        )
        graded: GradedAnswer = grader.grade(
            text, question, state, use_llm=use_llm, has_prereq=has_prereq
        )

        self.log(
            "evaluate",
            correct=graded.correct,
            misconception=graded.misconception_id,
            matched_by=graded.matched_by,
            action=graded.recommended_action,
        )

        self.learner.record(
            concept_id,
            correct=graded.correct,
            misconception_id=graded.misconception_id if not graded.correct else None,
            today=today,
        )
        after = self.learner.state_for(concept_id).p_known

        result = {
            "graded": graded,
            "mastery_before": round(before, 4),
            "mastery_after": round(after, 4),
            "concept_id": concept_id,
            "new_beats": [],
            "new_question": None,
            "skipped_beats": [],
        }

        if not graded.correct:
            new_beat, new_q = grader.reexplain(
                beat, graded,
                language=self.plan.profile.language,
                used_families=self._families_used(concept_id),
            )
            self.injected.append(new_beat)
            self.pending_question = new_q
            result["new_beats"] = [new_beat]
            result["new_question"] = new_q
            self.log(
                "adapt",
                action=graded.recommended_action,
                original_family=beat.analogy_family,
                new_family=new_beat.analogy_family,
                new_beat=new_beat.id,
                new_question=new_q.id,
                mastery_before=round(before, 4),
                mastery_after=round(after, 4),
            )
        elif graded.recommended_action == "level_up":
            skipped = self._skip_remaining(concept_id, keep_current=beat.id)
            result["skipped_beats"] = skipped
            self.log(
                "adapt", action="level_up", concept=concept_id,
                skipped=skipped, mastery_after=round(after, 4),
            )
        else:
            self.log("continue", concept=concept_id, mastery_after=round(after, 4))

        return result

    def _families_used(self, concept_id: str) -> set[str]:
        """Analogy families this concept has already been taught with."""
        return {
            b.analogy_family
            for b in list(self.plan.beats) + self.injected
            if b.concept_id == concept_id and b.analogy_family
        }

    def _skip_remaining(self, concept_id: str, *, keep_current: str) -> list[str]:
        """Mastered early: drop this concept's remaining beats and bank the time."""
        seen_current = False
        skipped = []
        for b in self.plan.beats:
            if b.id == keep_current:
                seen_current = True
                continue
            if seen_current and b.concept_id == concept_id and b.intent != "recap":
                skipped.append(b.id)
        self.skipped.extend(skipped)
        return skipped

    # --- reporting -----------------------------------------------------------

    def report(self) -> dict:
        weak = self.learner.weak_concepts()
        strong = self.learner.strong_concepts()
        names = {c.id: c.name for c in self.plan.concepts}
        return {
            "lesson_id": self.plan.lesson_id,
            "title": self.plan.title,
            "score": self.learner.score(),
            "mastery": self.learner.mastery(),
            "strong_areas": [names.get(c, c) for c in strong],
            "weak_areas": [names.get(c, c) for c in weak],
            "misconceptions": dict(self.learner.misconceptions),
            "revision_plan": self.learner.revision_plan(),
            "next_topic": self._next_topic(weak),
            "trace": self.trace_dicts(),
        }

    def _next_topic(self, weak: list[str]) -> str:
        names = {c.id: c.name for c in self.plan.concepts}
        if weak:
            return f"Revise {names.get(weak[0], weak[0])} before moving on."
        remaining = [c for c in self.plan.concepts
                     if self.learner.state_for(c.id).p_known < MASTERED]
        if remaining:
            return f"Continue with {remaining[0].name}."
        return "Move on to the next chapter."
