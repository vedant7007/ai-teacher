# Avatar and Video Generation

## The video artefact

Requirement 6 of the brief is a video-based AI Teacher presentation. A live web
player alone does not satisfy it, so the MP4 is a first-class output, built in
Phase 4 rather than left to a later "studio" phase.

```
slide HTML + word timings
  -> Playwright records the live page          (webm, variable frame rate, no audio)
  -> re-encode to constant 30 fps, pinned to the audio duration
  -> mux the beat's TTS audio                  (h264 + aac)
  -> concat all beats by stream copy           lesson.mp4
```

Playwright's `record_video_dir` captures the DOM and any canvas together in one
pass, so there is no compositing step and no canvas-merging problem.

### Constant frame rate is not optional

`record_video_dir` emits **variable frame rate with no audio track**. Muxing VFR
against audio drifts progressively: a few frames per beat becomes seconds by
beat 26. Each clip is therefore normalised before muxing:

```
[0:v]fps=30,scale=1280:720,tpad=stop_mode=clone:stop_duration=3,trim=0:<audio_secs>
-r 30 -fps_mode cfr -t <audio_secs>
```

`tpad` holds the final frame if the recording came up short, `trim` and `-t` pin
the duration to the audio. Every clip then has identical codec parameters, so the
final concat is a stream copy and introduces no drift of its own.

ffmpeg 9 removed `-vsync`; `-fps_mode cfr` is the current spelling.

### Measured

| Metric | Value |
|---|---|
| Per-beat drift | 0 to +14 ms |
| Full lesson drift | see `storage/studio/render_report.json` |
| Tolerance | 200 ms |
| Output | 1280x720, h264 CFR 30 fps, aac 44.1 kHz |

`tests/test_phase4.py::test_rendered_video_matches_the_audio` asserts the drift.

## The avatar

### What we ship

A stylised flat-illustration teacher rendered as inline SVG, with:

- **text-derived viseme approximation**: mouth shape is chosen from the vowel in
  the word currently being spoken, open for `आ/aa`, wide for `ई/ee`, rounded for
  `ऊ/oo`, closed for bilabials `म/ब/प`, and animated open-then-close across that
  word's measured duration;
- idle head sway and breathing;
- eye drift toward the slide;
- brow lift while speaking;
- blinks roughly every four seconds.

It is driven by the same edge-tts word timings as the captions and the slide
build-up, so the mouth tracks the audio without a separate phoneme pipeline.

### Why not a 3D GLB avatar

Two candidates were evaluated and both were rejected:

- **Ready Player Me** requires an interactive account and avatar-creation flow
  that cannot be completed headlessly during the build.
- **`facecap.glb`** (three.js examples) has real ARKit morph targets and was
  downloaded, then **deleted unused**: it is a scan of a **real person's face**.
  Using a real person's likeness is forbidden by our own build rules and the
  licence could not be verified. It is not in the repository.

We would rather ship an obviously stylised avatar we own outright than a
photoreal one with an unclear licence.

### Honest limitations

- The visemes are **derived from spelling, not phonemes**. There is no
  grapheme-to-phoneme model in the pipeline. Shapes are plausible and
  time-accurate rather than phonetically exact.
- The avatar is 2D. It is a deliberate illustration style, not a failed attempt
  at photorealism.
- A frozen face produces no error, so
  `test_avatar_mouth_actually_moves` drives the page in a real browser and
  asserts the mouth geometry takes at least three distinct values.

## Slide animation

Elements start hidden and are revealed by cues keyed to word timings. A graph
draws its line progressively rather than appearing whole, because the point of
the V-I plot is watching proportionality emerge.

Two guards exist because both failures are silent:

- **Cue resolution.** The model invents element ids such as `series[0]` and
  `x_label` that the renderer never emits. Cues resolve by exact match, then by
  prefix, then by ordinal, so every cue hits a real element.
- **Reveal floor.** If the model's first cue lands late, the primary element is
  shown by 8 percent into the beat regardless, so a slide never sits blank while
  the teacher talks over it.
