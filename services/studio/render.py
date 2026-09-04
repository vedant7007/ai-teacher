"""Lesson -> lesson.mp4, via Playwright page recording plus ffmpeg.

Pipeline per beat:
    slide HTML + word timings
      -> Playwright records the live page (three.js canvas AND DOM in one pass)
      -> webm, variable frame rate, no audio
      -> re-encode to constant 30 fps and to exactly the audio duration
      -> mux the beat's TTS audio
    then concat every beat.

The CFR step is not optional. record_video_dir emits VFR, and muxing VFR against
audio drifts progressively: a few frames per beat becomes seconds by beat 26.
Normalising each clip to CFR and to a known duration makes the concat exact.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from services.llm.schemas import Beat, LessonPlan
from services.speech.tts import audio_duration_ms, speak
from services.visual.slide import render_slide

OUT = Path("storage/studio")
FPS = 30
WIDTH, HEIGHT = 1280, 720
TAIL_MS = 350  # let the last reveal settle before the beat cuts


def _ff(*args: str) -> None:
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {' '.join(args[:6])}\n{r.stderr[-800:]}")


def probe_ms(path: Path) -> int:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return int(float(r.stdout.strip()) * 1000)


def _record_beat(page_ctx, beat: Beat, timings, html_path: Path, ms: int) -> Path:
    """Open the slide, play it for `ms`, close, return the raw webm."""
    browser, ctx = page_ctx
    page = ctx.new_page()
    page.goto(html_path.resolve().as_uri())
    page.wait_for_function("window.__ready===true", timeout=30000)
    page.evaluate("window.play()")
    page.wait_for_timeout(ms + TAIL_MS)
    video = page.video
    page.close()
    return Path(video.path())


def render_lesson(
    plan: LessonPlan,
    *,
    out_dir: Path = OUT,
    limit: int | None = None,
    avatar: bool = True,
    verbose: bool = True,
) -> dict:
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    slides = out_dir / "slides"; slides.mkdir(exist_ok=True)
    raw = out_dir / "raw"; raw.mkdir(exist_ok=True)
    clips = out_dir / "clips"; clips.mkdir(exist_ok=True)

    beats = plan.beats[:limit] if limit else plan.beats

    # Synthesize everything up front: speak() cannot run inside Playwright's loop
    # without a thread hop, and doing it here keeps the recording loop tight.
    prepared = []
    for beat in beats:
        mp3, timings = speak(beat.script, beat.language)
        prepared.append((beat, mp3, timings, audio_duration_ms(mp3)))
    total_audio_ms = sum(d for _, _, _, d in prepared)
    if verbose:
        print(f"prepared {len(prepared)} beats, audio total {total_audio_ms/1000:.1f}s")

    made: list[Path] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for i, (beat, mp3, timings, dur) in enumerate(prepared):
            html = slides / f"{beat.id}.html"
            html.write_text(
                render_slide(beat, timings, title=beat.intent, avatar=avatar),
                encoding="utf-8",
            )
            ctx = browser.new_context(
                viewport={"width": WIDTH, "height": HEIGHT},
                record_video_dir=str(raw),
                record_video_size={"width": WIDTH, "height": HEIGHT},
            )
            webm = _record_beat((browser, ctx), beat, timings, html, dur)
            ctx.close()  # the webm is only finalised on context close

            clip = clips / f"{beat.id}.mp4"
            _normalise_and_mux(webm, mp3, dur, clip)
            made.append(clip)
            if verbose:
                got = probe_ms(clip)
                print(f"  [{i+1:2}/{len(prepared)}] {beat.id:4} audio={dur:6}ms "
                      f"clip={got:6}ms drift={got-dur:+5}ms {beat.visual.kind}")
        browser.close()

    final = out_dir / "lesson.mp4"
    _concat(made, final)

    result = {
        "mp4": str(final),
        "beats": len(made),
        "audio_ms": total_audio_ms,
        "video_ms": probe_ms(final),
        "clips": [str(c) for c in made],
    }
    result["drift_ms"] = result["video_ms"] - total_audio_ms
    (out_dir / "render_report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def _normalise_and_mux(webm: Path, mp3: Path, dur_ms: int, out: Path) -> None:
    """VFR webm -> CFR 30fps, trimmed/padded to the audio, then muxed.

    The `fps` filter plus `-fps_mode cfr` resamples the variable frame
    timestamps onto a fixed grid. `-t` pins the duration, and tpad holds the final frame if
    the recording came up short, so video and audio always agree.
    """
    secs = dur_ms / 1000
    _ff(
        "-i", str(webm),
        "-i", str(mp3),
        "-filter_complex",
        f"[0:v]fps={FPS},scale={WIDTH}:{HEIGHT},"
        f"tpad=stop_mode=clone:stop_duration=3,trim=0:{secs:.3f},setpts=PTS-STARTPTS[v]",
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        # ffmpeg 9 dropped -vsync; -fps_mode cfr is the current spelling.
        "-pix_fmt", "yuv420p", "-r", str(FPS), "-fps_mode", "cfr",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-t", f"{secs:.3f}",
        "-movflags", "+faststart",
        str(out),
    )


def _concat(clips: list[Path], out: Path) -> None:
    """Stream-copy concat. Every clip is already CFR 30fps with the same codec,
    so no re-encode is needed and no drift is introduced."""
    listing = out.parent / "concat.txt"
    listing.write_text(
        "".join(f"file '{c.resolve().as_posix()}'\n" for c in clips), encoding="utf-8"
    )
    _ff("-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(out))


def have_ffmpeg() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
