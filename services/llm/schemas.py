"""Pydantic contracts. Every LLM output is validated against these.

Two fields exist here before the feature that consumes them, deliberately:
  - Beat.groundedness_score is filled in locally after generation and shown in
    the UI trace panel.
  - Beat.language plus LessonPlan.language_switches let a mid-lesson language
    change be represented in the plan rather than bolted on later.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Language = str  # "en-IN", "hi-IN", "hinglish", "te-IN", ...

VisualKind = Literal["equation", "graph", "diagram", "code", "bullets"]

Intent = Literal[
    "hook", "explain", "example", "analogy", "demo", "check", "recap", "transition"
]

# Beats that assert facts must cite. Framing beats need not.
CITATION_EXEMPT: set[str] = {"hook", "transition", "recap", "check"}


class SourceRef(BaseModel):
    doc_id: str
    chunk_id: str | None = None
    chapter: str = ""
    section: str = ""
    page_start: int
    page_end: int
    char_start: int = 0
    char_end: int = 0
    quote: str = ""


class LearnerProfile(BaseModel):
    level: Literal["beginner", "intermediate", "advanced"] = "beginner"
    prior_knowledge: list[str] = Field(default_factory=list)
    goal: str | None = None
    language: Language = "en-IN"
    style: Literal["examples-first", "theory-first", "socratic", "visual"] = "examples-first"
    time_budget_minutes: int = 20
    depth: Literal["overview", "standard", "deep"] = "standard"
    topic: str | None = None
    wants_questions_during: bool = True
    wants_final_test: bool = True

    @field_validator("time_budget_minutes")
    @classmethod
    def sane_budget(cls, v: int) -> int:
        return max(3, min(v, 7 * 24 * 60))


class Concept(BaseModel):
    id: str
    name: str
    prerequisites: list[str] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)
    difficulty: float = 0.5
    est_minutes: float = 3.0
    analogy_families: list[str] = Field(default_factory=list)


class TimelineCue(BaseModel):
    element_id: str
    word_index: int = 0
    action: Literal["show", "highlight", "hide"] = "show"


class VisualSpec(BaseModel):
    kind: VisualKind
    reason: str  # WHY this visual for this subject, surfaced in the UI
    subject: str = ""
    payload: dict = Field(default_factory=dict)
    timeline: list[TimelineCue] = Field(default_factory=list)


class Question(BaseModel):
    id: str
    concept_id: str
    type: Literal["mcq", "short", "numeric", "explain_own_words", "apply"] = "short"
    prompt: str
    options: list[str] | None = None
    answer_key: str = ""
    rubric: list[str] = Field(default_factory=list)
    targets_misconception: str | None = None


class Beat(BaseModel):
    """One teaching moment, 20 to 60 seconds of speech."""

    id: str
    # None on framing beats: a recap or hook spans every concept, not one.
    concept_id: str | None = None
    intent: Intent
    script: str
    visual: VisualSpec
    citations: list[SourceRef] = Field(default_factory=list)
    checkpoint: Question | None = None
    language: Language = "en-IN"
    analogy_family: str | None = None
    # Filled locally after generation, never by the model.
    groundedness_score: float | None = None
    est_seconds: float | None = None
    generated_after_answer: bool = False

    @property
    def needs_citation(self) -> bool:
        return self.intent not in CITATION_EXEMPT

    def word_count(self) -> int:
        return len(self.script.split())


class LanguageSwitch(BaseModel):
    """A mid-lesson language change, recorded in the plan itself."""

    at_beat_id: str
    from_language: Language
    to_language: Language
    acknowledgement: str = ""


class LessonPlan(BaseModel):
    lesson_id: str = ""
    title: str
    profile: LearnerProfile
    concepts: list[Concept]
    beats: list[Beat]
    final_quiz: list[Question] = Field(default_factory=list)
    language_switches: list[LanguageSwitch] = Field(default_factory=list)
    doc_id: str | None = None

    def total_words(self) -> int:
        return sum(b.word_count() for b in self.beats)

    def est_minutes(self, wpm: float) -> float:
        return self.total_words() / wpm

    def uncited_fact_beats(self) -> list[Beat]:
        return [b for b in self.beats if b.needs_citation and not b.citations]

    def mean_groundedness(self) -> float | None:
        scored = [b.groundedness_score for b in self.beats if b.groundedness_score is not None]
        return sum(scored) / len(scored) if scored else None


class GradedAnswer(BaseModel):
    correct: bool
    confidence: float = 0.5
    misconception_id: str | None = None
    feedback: str
    recommended_action: Literal[
        "continue", "reexplain_analogy", "reexplain_simpler", "worked_example",
        "step_back_prereq", "drill", "level_up",
    ] = "continue"
    matched_by: Literal["taxonomy", "llm", "default"] = "llm"


class Interaction(BaseModel):
    beat_id: str
    question_id: str
    answer: str
    graded: GradedAnswer
    at: str


class LearnerState(BaseModel):
    mastery: dict[str, float] = Field(default_factory=dict)
    misconceptions: dict[str, int] = Field(default_factory=dict)
    next_review: dict[str, str] = Field(default_factory=dict)
    history: list[Interaction] = Field(default_factory=list)
