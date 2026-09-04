# Evaluation

Measured numbers, not estimates. Reproduce with `python -m pytest -v`.

## Retrieval (Phase 1)

Corpus: NCERT Class 10 Science Chapter 11 "Electricity", 24 pages, 30 chunks.

| Metric | Result |
|---|---|
| Known-answer questions retrieving the correct section | **10 / 10** |
| Fabricated page references | **0** |
| Chapter sections detected | 8 of 8, plus 3 subsections |
| Index build time (CPU) | 11.7 s for a 26-page Hindi chapter |
| Embedding model | paraphrase-multilingual-MiniLM-L12-v2, 384 dims |
| API requests to index | **0** |

Groundedness separates a true claim from the target misconception, scored
against the section that refutes it:

| Sentence | Score |
|---|---|
| "Potential difference is directly proportional to current" | 0.859 |
| "Current is inversely proportional to voltage" (`ohms_law_inverse_confusion`) | 0.539 |

## Lesson generation (Phase 2)

Request: beginner, section 11.4, 20 minutes, Hindi.
One Gemini call, `gemini-2.5-flash`, `finish_reason=STOP`, 23,168 output tokens.

| Metric | Result | Criterion |
|---|---|---|
| Beats | 26 | |
| Concepts | 3 | |
| Script words | 2730 | target 2600 |
| Time fidelity | **+5.0%** | within 10 percent |
| Estimated duration | 21.0 min | 20 min requested |
| Beats in Devanagari | 26 / 26 | all |
| Check beats vs concepts | 3 vs 3 | one per concept |
| Final quiz questions | 4 | at least 4 |
| Fact beats without a citation | **0** | 0 |
| Timeline cues | 115 | animation, not a slideshow |
| Mean groundedness | 0.543 | see note |

Visual kinds chosen: `{'bullets': 10, 'diagram': 6, 'equation': 9, 'graph': 1}`

**Note on the 0.543 mean groundedness.** The scripts are
Hindi, the source chunks are English. Cross-lingual cosine on a multilingual
sentence encoder sits structurally lower than same-language cosine, so this is
not comparable to the 0.859 figure above, which was English against English.
The threshold has to be language-pair aware. Tracked in `docs/KNOWN_LIMITATIONS.md`.

## Request budget

| Item | Requests |
|---|---|
| Indexing a document | 0 |
| Intake parsing | 1 (Groq) |
| **Full 20-minute lesson** | **1 (Gemini)** |
| Re-running an identical call | **0** (disk cache) |
| Gemini spent through Phase 2 | 6 of ~1500 |

Two of those six went to a decommissioned-model fallthrough and one to a repair
call for a trivial schema mismatch. Both causes are fixed: the cheap tier points
at a live model, and near-miss JSON is coerced before validation rather than
triggering a second generation.

## Test suite

```
29 passed
```

Phase 0: health, cache saves a request. Phase 1: tree structure, 10 retrieval
questions, citation integrity. Phase 2: time fidelity, language, checkpoints,
citations, visual kinds, animation, offline intake fallback.
