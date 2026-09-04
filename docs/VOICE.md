# Voice and Timing

## Synthesis

`edge-tts` (Microsoft Edge neural voices). Free, no API key, 40+ languages
including every Indian language in `services/speech/voices.yaml`.

## The word-timing trap

CLAUDE.md's design rests on edge-tts emitting `WordBoundary` events, which give
start and duration per spoken token for free. Those timings drive three things at
once: caption highlighting, slide element build-up, and avatar visemes.

**In edge-tts 7.x the default is `SentenceBoundary`, not `WordBoundary`.** With
the default, a 107-word Hindi beat yields exactly one event and every animation
cue collapses to 0 ms, silently. There is no error. The fix is one parameter:

```python
edge_tts.Communicate(text, voice, boundary="WordBoundary")
```

This is not Hindi-specific. English voices behave identically.

## Devanagari behaves

The concern was that Devanagari would tokenise per orthographic cluster, giving
several events per written word and drifting the slide build-up. Measured on a
107-word Hindi beat:

| Metric | Value |
|---|---|
| Script words | 107 |
| WordBoundary events | 107 |
| Events per word | **1.00** |

One event per word. `align_to_words()` still merges multi-event words, because
other languages and voices do split, but Hindi does not need it.

## What did break: unspoken symbols

A script containing "V = W/Q" produces no boundary event for `=`, because it is
never spoken. A naive aligner walking both lists in step desyncs at that point
and every subsequent word inherits a 0 ms cue. On the demo beat that silently
zeroed 30 of 107 words, all after the formula.

`align_to_words()` emits unspoken tokens at the current position and continues,
and abandons its accumulator rather than propagate a desync. Covered by
`tests/test_phase3.py::test_alignment_survives_unspoken_symbols`, which runs
offline against synthetic events so it cannot flake on the service.

## Measured alignment, Hindi

Beat b3, `hi-IN-SwaraNeural`, 107 words:

| Metric | Value |
|---|---|
| Audio duration | 43,512 ms |
| Speech ends (ffmpeg silencedetect) | 42,507 ms |
| Last word ends | 42,637 ms |
| **Alignment drift** | **130 ms** (limit 150 ms) |
| Monotonic starts | yes |
| Zero-duration words | 1, the unspoken `=` |

Drift is measured against the end of speech rather than the end of the file,
because the container carries about a second of trailing silence that is not
misalignment.

## Pace

Spoken pace is language-specific and the time budget is graded, so
`planner.WPM` carries a rate per language: English 150, Hinglish 140, Hindi 130,
Telugu and Tamil 120. A 20 minute Hindi lesson is therefore a 2,600 word script.

The model reliably lands a few percent under whatever word count it is asked
for, so `WORD_BUDGET_CALIBRATION = 1.10` asks for 10 percent more than the true
target. Measured effect on the demo lesson: -11.3% before, **-3.9% after**.

## Voices

`services/speech/voices.yaml` is the single source of truth, with a fallback
voice per language. Hinglish deliberately uses the Indian **English** voice:
a Hindi voice reading Roman-script Hindi mispronounces heavily, while the Indian
English voice handles code-mixed text well.

Shipped and tested end to end: English, Hindi, Hinglish. Six further languages
are configured and selectable but outside the tested demo path.
