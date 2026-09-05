# Known Limitations

Written honestly. Every number here is measured, and every item we did not fix
says so plainly rather than being left undocumented.

## Time fidelity: one global calibration constant, tuned per language

`services/pedagogy/planner.py` carries a single module-level constant:

```python
WORD_BUDGET_CALIBRATION = 1.45
```

The model reliably produces fewer words than it is asked for, so we ask for more
than the true target. The problem is that the shortfall is **not uniform across
languages**, and one global multiplier cannot correct both:

| Language | Target | Delivered | Delta | Requested / actual |
|---|---|---|---|---|
| Hindi | 2600 words | 2499 | **-3.9%** | 20 min / 19.2 min |
| English | 3000 words | 2687 | **-10.4%** | 20 min / 17.9 min |

**English is outside our own 10 percent acceptance band.** The constant was
originally 1.10, tuned against Hindi alone, at which point English came in at
**-35.9%** (12.8 minutes against 20 requested). Raising it to 1.45 fixed most of
the gap but overshoots for Hindi and still undershoots for English.

The correct fix is per-language word-density calibration: a measured constant per
language, derived from several generations each, rather than one number tuned on
one language. We did not have time to gather that data, so the single constant
stands and English runs about two minutes short of the requested twenty.

## Avatar

- The avatar is a **stylised 2D flat illustration**, not a 3D model. This is a
  deliberate choice, not a failed attempt at photorealism.
- Visemes are **derived from spelling, not phonemes**. There is no
  grapheme-to-phoneme model in the pipeline, so mouth shapes are chosen from the
  vowel in the word currently being spoken. They are time-accurate because the
  word timings are real, but they are not phonetically exact.
- Two 3D routes were evaluated and rejected: **Ready Player Me** needs an
  interactive account flow that cannot be completed headlessly, and
  **`facecap.glb`** was downloaded then deleted unused because it is a scan of a
  **real person's face**, which our own build rules forbid and whose licence we
  could not verify. It is not in this repository.

## Retrieval

- **Short queries rank poorly.** The bare query "Ohm's law" ranks section 11.7
  above 11.4. Mitigated by section scoping, which is the path the lesson planner
  actually uses, but a bare semantic query is weak.
- **No reranker.** Cut item 1. Retrieval is RRF-fused dense plus BM25, top 8,
  with no cross-encoder rerank.
- **No OCR fallback.** Cut item 2. Both seed documents have an extractable text
  layer; a scanned PDF would produce nothing.
- The **drop cap** on a chapter's first paragraph is extracted as a separate
  glyph, so the first body word reads "lectricity". Cosmetic, once per chapter.

## Groundedness

The mean groundedness score is **not comparable across language pairs**. Measured
on the same material:

| Comparison | Score |
|---|---|
| English claim vs English source | 0.859 |
| Hindi lesson vs English source (mean) | 0.543 |

Cross-lingual cosine on a multilingual sentence encoder sits structurally lower
than same-language cosine. The threshold should be language-pair aware and
currently is not, so the Hindi lesson's average looks worse than it is.

## Language coverage

Three languages are shipped and tested end to end: **English, Hindi, Hinglish**.
Six more (Telugu, Tamil, Marathi, Bengali, Spanish, French) are configured in
`services/speech/voices.yaml` with real voice ids and are selectable, but are
**not part of the tested path** and are shown in the UI as unavailable rather
than being offered and failing.

## Video generation

- Rendering is **not real time**: roughly one minute of wall clock per beat, so a
  40-beat lesson takes about 40 minutes to produce an MP4. Fine for a studio
  render, unsuitable for on-demand generation.
- Requires a **desktop browser and ffmpeg**. It does not run on free CPU hosting.
- The live web player and the MP4 share one renderer, so what a judge sees in the
  video is what a student sees in the app, but the MP4 is produced offline.

## Deployment

**Not deployed.** The brief requires "a functional application **or** deployed
demonstration", and we chose the former. A `Dockerfile` targeting Hugging Face
Spaces is included and CPU-torch-pinned, but its build was **never verified**
because the Docker daemon was unavailable during the build window. Treat it as
untested.

## Testing gaps we hit and what they taught us

Two defects reached a rendered video while the whole suite was green. Both are
now covered, but they are worth recording because they show what our assertions
were not measuring:

1. **Word-timing collapse.** Phase 3 measured alignment on a single sampled beat
   and passed. 25 of 26 beats were in fact collapsing every animation cue to the
   final word, so slides sat blank while the teacher talked over them. Cause: the
   Devanagari danda `।` (U+0964) sits **inside** the `ऀ-ॿ` block, so a
   range-based normaliser preserved it and every sentence-final word failed to
   match its spoken token. Now asserted across all beats.

2. **Mermaid error cards.** Three beats rendered "Syntax error in text, mermaid
   version 10.9.1" straight into the video. The existing check asked whether a
   Mermaid SVG existed, and **Mermaid renders its own parse failure as an SVG**,
   so the check passed on all three. Now asserted on visible text.

The lesson in both cases: a proxy for success is not success. Duration, file
size and element presence all passed while the artefact was wrong.

## Request budget

`DEMO_MODE` replays a frozen lesson from `data/demo/` rather than generating
live, so a demonstration cannot be rate-limited. This is a deliberate engineering
choice, disclosed here rather than hidden: the live generation path is the same
code and is exercised by the same tests, but the demo defaults to the frozen
plan. Gemini free tier allows roughly 1,500 requests per day and one full lesson
costs exactly one.
