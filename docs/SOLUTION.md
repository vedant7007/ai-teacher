# Solution

An AI teacher whose pedagogy is **explicit, inspectable state** rather than an
implicit property of a prompt.

## The loop

```
Understand -> Plan -> Explain -> Demonstrate -> Question -> Evaluate -> Adapt -> Continue
```

Every transition is logged and rendered in the trace panel, because the claim we
are making is that the teaching decisions are real and visible, not improvised
per token.

## What is different

| Common approach | This project |
|---|---|
| LLM grades free text | Deterministic taxonomy match first, LLM only on no-match |
| "Incorrect, the answer is..." | Names the misconception, re-explains with a *different* analogy family |
| Progress bar | Bayesian Knowledge Tracing probability per concept, shown and steering |
| One call per beat | **One call per lesson**, 40 beats in a single structured response |
| Grading costs requests | Grading costs **zero** requests |

## Why deterministic first

The five assertions that carry the highest-weighted rubric category run in
**1.42 seconds with no network**. A judge can read the taxonomy as a YAML file.
The live demo cannot fail because a model got creative.

See [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) for what this costs us.
