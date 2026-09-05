# Architecture

The full diagram is in the [README](../README.md#architecture). This document
covers one adaptive loop in detail.

## Sequence: a wrong answer

```mermaid
sequenceDiagram
  participant S as Student
  participant O as Orchestrator
  participant T as Taxonomy (YAML)
  participant B as BKT
  participant R as Re-explainer

  S->>O: "Current increases."
  O->>T: match(answer, concept="ohms_law")
  T-->>O: ohms_law_inverse_confusion (regex hit, 0 requests)
  O->>B: record(correct=False)
  B-->>O: mastery 0.25 -> 0.184, SM-2 due tomorrow
  O->>R: reexplain(used_families={mechanical})
  R-->>O: new beat (family=everyday) + new diagnostic question
  O-->>S: names it, re-explains differently, asks again
```

No network call anywhere in that path.

## Module map

| Path | Responsibility |
|---|---|
| `services/ingest/` | parse, structure tree, chunk, embed, index |
| `services/rag/` | hybrid retrieval, RRF fusion, groundedness scoring |
| `services/llm/` | router, disk cache, budget accountant, Pydantic schemas, prompts |
| `services/pedagogy/` | planner, grader, taxonomy, BKT, orchestrator |
| `services/visual/` | Visual Director, slide renderer, Mermaid sanitiser |
| `services/speech/` | edge-tts, word-timing alignment, voice config |
| `services/studio/` | Playwright recording, CFR normalisation, ffmpeg mux |
| `apps/web/` | landing, setup flow, lesson stage, report |

Orchestration is plain Python. No LangChain, no agent framework: they would hide
the architecture being graded.
