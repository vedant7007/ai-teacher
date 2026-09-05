# Assessment

## During the lesson

One `check` beat per concept, placed immediately after that concept is taught,
never all at the end. Each carries a structured `Question` with a rubric, and
where relevant a `targets_misconception` id naming the specific error it is
designed to catch.

Question types: `mcq`, `short`, `numeric`, `explain_own_words`, `apply`.

## Grading

Deterministic first. The student's answer is tested against the taxonomy's
`trigger_patterns`, concept-scoped so a generic pattern cannot steal a match from
the concept being taught. Only on a miss does an LLM grade against the rubric.

The grader is **forbidden from ever just saying "incorrect"**. Every response
names what the student was probably thinking.

## Mastery

Bayesian Knowledge Tracing, `p_init=0.25, p_transit=0.15, p_slip=0.10,
p_guess=0.20`. A wrong answer moves 0.25 to 0.184; three correct answers recover
it to 0.87. The bar on screen is this number.

## Revision

SM-2. A lapsed concept is scheduled for tomorrow, not dropped. Intervals grow
1 -> 6 -> `interval * ease` on success.

## Final report

Score, concepts understood, weak areas, misconceptions hit with counts, revision
dates, and a recommended next topic.
