"""Deterministic misconception matching.

An answer is tested against the taxonomy's `trigger_patterns` BEFORE any model
is consulted. Three things follow from that:

  - the test that wins the 20-mark category runs offline, in milliseconds, and
    cannot flake on a network call;
  - the live demo cannot fail because a model got creative;
  - the pedagogy is inspectable, a judge can read misconceptions.yaml.

The LLM grader still runs when nothing matches, and an unmatched wrong answer
becomes a `novel_misconception` record rather than being discarded.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

TAXONOMY_PATH = Path(__file__).with_name("misconceptions.yaml")

ANALOGY_FAMILIES = {
    "mechanical", "everyday", "computational", "biological", "financial",
}


@dataclass
class Misconception:
    id: str
    subject: str
    concept: str
    summary: str
    correct_model: str
    analogy_family: str
    preferred_analogy: str
    diagnostic_question: str
    trigger_patterns: list[str] = field(default_factory=list)
    _compiled: list[re.Pattern] = field(default_factory=list, repr=False)

    def matches(self, answer: str) -> str | None:
        """Return the pattern that fired, so the trace panel can show why."""
        for pat in self._compiled:
            if pat.search(answer):
                return pat.pattern
        return None


@lru_cache(maxsize=1)
def load() -> dict[str, Misconception]:
    raw = yaml.safe_load(TAXONOMY_PATH.read_text(encoding="utf-8"))
    out: dict[str, Misconception] = {}
    for entry in raw["misconceptions"]:
        m = Misconception(
            id=entry["id"],
            subject=entry.get("subject", ""),
            concept=entry.get("concept", ""),
            summary=entry.get("summary", "").strip(),
            correct_model=entry.get("correct_model", "").strip(),
            analogy_family=entry.get("analogy_family", "everyday"),
            preferred_analogy=entry.get("preferred_analogy", "").strip(),
            diagnostic_question=entry.get("diagnostic_question", "").strip(),
            trigger_patterns=list(entry.get("trigger_patterns") or []),
        )
        m._compiled = [re.compile(p, re.IGNORECASE | re.UNICODE)
                       for p in m.trigger_patterns]
        out[m.id] = m
    return out


@dataclass
class Match:
    misconception: Misconception
    pattern: str

    @property
    def id(self) -> str:
        return self.misconception.id


def match(answer: str, *, concept_id: str | None = None) -> Match | None:
    """Find the misconception an answer betrays.

    When `concept_id` is given, entries for that concept are tried first, so a
    generic pattern cannot steal a match from the concept actually being taught.
    """
    if not answer or not answer.strip():
        return None

    entries = list(load().values())
    if concept_id:
        entries.sort(key=lambda m: m.concept != concept_id)

    for m in entries:
        pat = m.matches(answer)
        if pat:
            return Match(m, pat)
    return None


def for_concept(concept_id: str) -> list[Misconception]:
    return [m for m in load().values() if m.concept == concept_id]


def different_family(family: str | None) -> str:
    """Pick an analogy family that is NOT the one already used.

    Re-explanation must switch family rather than restate the first explanation
    in different words. Asserted in tests/test_adaptation.py.
    """
    order = ["everyday", "mechanical", "computational", "biological", "financial"]
    for f in order:
        if f != (family or ""):
            return f
    return "everyday"


def stats() -> dict:
    ms = load()
    subjects: dict[str, int] = {}
    for m in ms.values():
        subjects[m.subject] = subjects.get(m.subject, 0) + 1
    return {
        "count": len(ms),
        "subjects": subjects,
        "patterns": sum(len(m.trigger_patterns) for m in ms.values()),
    }
