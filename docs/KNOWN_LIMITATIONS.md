# Known Limitations

Written honestly. Every number here is measured, and every item we did not fix
says so plainly rather than being left undocumented.

## Time fidelity: the words-per-minute constant is wrong for English

`services/pedagogy/planner.py` carries a per-language speaking rate and a single
global calibration constant:

```python
WPM = {"en-IN": 150, "hi-IN": 130, ...}
WORD_BUDGET_CALIBRATION = 1.45
```

We originally believed English lessons were running short and raised the
calibration from 1.10 to 1.45 to compensate. **That diagnosis was wrong.**
Measuring the rendered audio rather than estimating from word count shows:

| Language | Words | Predicted | Actual audio | Actual wpm | Constant | vs 20 min |
|---|---|---|---|---|---|---|
| Hindi | 2499 | 19.2 min | **18.9 min** | 132 | 130 | **-5%** |
| English | 2687 | 17.9 min | **23.0 min** | **117** | 150 | **+15%** |

The Hindi constant of 130 is accurate. The English constant of 150 is roughly
28 percent too fast: `en-IN-NeerjaNeural` actually delivers about **117 words per
minute**. So English lessons were never undershooting, and raising the
calibration to 1.45 pushed them from approximately on target to 15 percent long.

**The correct fix is per-voice wpm measurement**, not word-budget calibration:
synthesize a fixed passage with each configured voice, divide words by measured
audio duration, and store the result per voice in `voices.yaml`. The calibration
constant then becomes unnecessary for all languages rather than being tuned to
compensate for a wrong rate in one of them.

We did not have time to run that measurement across the voice set, so the demo
English lesson runs about three minutes long against a 20 minute request. The
number reported in `docs/EVALUATION.md` as "-10.4 percent" is a word-count
estimate and is superseded by the measured +15 percent above.

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
