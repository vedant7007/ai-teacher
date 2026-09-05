# Prompt and agent architecture

There are **no agents**. There are five prompts and a plain Python orchestrator,
which is a deliberate choice: an agent framework would add install time, failure
surface, and would hide the architecture being graded.

| Prompt | Model tier | Purpose |
|---|---|---|
| `services/llm/prompts/intake.md` | cheap | natural sentence -> `LearnerProfile` |
| `services/llm/prompts/lesson.md` | Gemini | the whole lesson in one call |
| grading | deterministic | taxonomy regex match, no model |
| re-explanation | deterministic | taxonomy supplies analogy and question |
| report | local | derived from `LearnerState` |

Grading and re-explanation were originally planned as prompts. Both became
deterministic because that is what makes the adaptation test run offline in 1.42
seconds. The LLM grader survives only as the fallback for answers no pattern
matches, which then become `novel_misconception` records.

## Structured output policy

Every model output is validated against a Pydantic schema. Near-miss JSON is
**coerced before validation** (`_sanitize`), because a repair call costs a full
second generation. Repair is reserved for genuine structural failure, then a
deterministic fallback. A truncated response raises rather than being repaired,
so the cause is visible.
