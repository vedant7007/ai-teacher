# Personalization

## The profile

```python
class LearnerProfile:
    level: beginner | intermediate | advanced
    prior_knowledge: list[str]
    goal: exam | interview | curiosity | revision | None
    language: str            # en-IN, hi-IN, hinglish, ...
    style: examples-first | theory-first | socratic | visual
    time_budget_minutes: int
    depth: overview | standard | deep
```

Parsed from one natural sentence. The brief's own example
("I am a beginner. Teach me Chapter 4 in 20 minutes. Explain it in Hindi...")
resolves to `level=beginner, language=hi-IN, minutes=20, topic="Chapter 4",
questions=True, test=True`.

A deterministic fallback parser handles the same sentence with no network,
including Devanagari and Hinglish time units.

## Time budgeting

Word count is allocated from the time budget and a per-language speaking rate.
A 20 minute Hindi lesson is a 2,600 word script. Concept count is capped so a
short lesson covers a few ideas properly rather than eight thinly.

Measured fidelity, and the constant that is wrong for English, are recorded in
[KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).

## Adaptation during the lesson

| Signal | Response |
|---|---|
| Wrong, mastery < 0.40 | re-explain with a different analogy family |
| Two consecutive wrong | step back to the prerequisite |
| Mastery > 0.85 early | skip that concept's remaining beats, bank the time |
