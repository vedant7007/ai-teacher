"""Phase 4 acceptance: alignment health, avatar motion, video artefact.

The alignment tests here exist because Phase 3 passed on a single sampled beat
while 25 of 26 beats were silently broken. Anything that can collapse quietly
is asserted across the whole lesson, not a sample.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from services.llm.schemas import LessonPlan
from services.speech.tts import WordTiming, align_to_words, _norm
from services.visual.slide import cues_for, render_slide

DEMO = Path("data/demo/lesson_ohms_law_hi.json")
REPORT = Path("storage/studio/render_report.json")


@pytest.fixture(scope="module")
def plan() -> LessonPlan:
    return LessonPlan(**json.loads(DEMO.read_text(encoding="utf-8")))


def _b(ms: int, dur: int, text: str) -> dict:
    return {"text": text, "offset": ms * 10_000, "duration": dur * 10_000}


# --- normalisation ----------------------------------------------------------


def test_devanagari_danda_is_stripped():
    """The danda U+0964 sits INSIDE the Devanagari block ऀ-ॿ.

    A range-based keep-list preserves it, so every sentence-final word fails to
    match its spoken token. That desynced 25 of 26 beats.
    """
    assert _norm("सीखेंगे।") == _norm("सीखेंगे")
    assert _norm("है॥") == _norm("है")


def test_math_symbols_are_stripped():
    """'=' is category Sm, not punctuation, and is never spoken."""
    assert _norm("=") == ""
    assert _norm("V/I।") == _norm("VI")


# --- alignment --------------------------------------------------------------


def test_alignment_recovers_from_an_unspoken_word():
    """A word the voice skips entirely must not zero the rest of the beat."""
    script = "यह Ω मान है"
    # No boundary event for Ω at all.
    got = align_to_words(script, [_b(0, 200, "यह"), _b(300, 250, "मान"), _b(600, 200, "है")])
    assert [t.word for t in got] == script.split()
    assert got[-1].start_ms >= 600, "tail must keep real timings"


def test_alignment_never_collapses_on_any_beat(plan):
    """Every beat must stay aligned to its end.

    A collapse is silent: cues pile up at the final word and the slide sits
    blank while the teacher talks over it.
    """
    from services.speech.tts import speak

    collapsed = []
    for beat in plan.beats:
        try:
            _, timings = speak(beat.script, beat.language)
        except Exception as exc:  # noqa: BLE001
            pytest.skip(f"tts unavailable: {exc}")
        end = timings[-1].start_ms
        last_real = max((t.index for t in timings if t.start_ms < end), default=-1)
        if last_real < len(timings) * 0.9:
            collapsed.append((beat.id, last_real, len(timings)))
    assert not collapsed, f"beats whose timings collapse early: {collapsed}"


# --- cues -------------------------------------------------------------------


def test_no_slide_sits_blank(plan):
    """The first reveal must land early, whatever the model asked for."""
    for beat in plan.beats:
        timings = [WordTiming(w, i, i * 400, 350) for i, w in enumerate(beat.script.split())]
        cues = cues_for(beat, timings)
        if not cues:
            continue
        duration = timings[-1].end_ms
        assert cues[0]["at_ms"] <= duration * 0.10 + 1, (
            f"{beat.id}: first cue at {cues[0]['at_ms']}ms of {duration}ms"
        )


def test_cues_are_spread_not_bunched_at_the_end(plan):
    from services.speech.tts import speak

    for beat in plan.beats:
        try:
            _, timings = speak(beat.script, beat.language)
        except Exception as exc:  # noqa: BLE001
            pytest.skip(f"tts unavailable: {exc}")
        cues = cues_for(beat, timings)
        if len(cues) < 2:
            continue
        duration = max(1, timings[-1].end_ms)
        assert cues[0]["at_ms"] < duration * 0.5, f"{beat.id} cues bunched late"


# --- avatar -----------------------------------------------------------------


def test_avatar_is_present_and_wired(plan):
    beat = plan.beats[0]
    timings = [WordTiming(w, i, i * 400, 350) for i, w in enumerate(beat.script.split())]
    html = render_slide(beat, timings, avatar=True)
    assert 'id="avatar"' in html and 'id="av-mouth"' in html
    assert "__avatarFrame" in html, "mouth must be driven per frame"
    assert "__wordSpans" in html, "mouth must be driven by word timings"
    assert render_slide(beat, timings, avatar=False).count('id="avatar"') == 0


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_avatar_mouth_actually_moves(plan):
    """A frozen face raises no error, so assert the geometry changes."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright not installed")

    from services.speech.tts import speak

    beat = plan.beats[0]
    try:
        _, timings = speak(beat.script, beat.language)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"tts unavailable: {exc}")

    out = Path("storage/slides"); out.mkdir(parents=True, exist_ok=True)
    f = (out / "avatar_test.html").resolve()
    f.write_text(render_slide(beat, timings, avatar=True), encoding="utf-8")

    # Sample across the whole beat. A fixed window can land inside a pause
    # between sentences, where a closed mouth is the correct behaviour.
    span = timings[-1].end_ms
    points = [int(span * i / 40) for i in range(1, 40)]

    heights = []
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        pg = br.new_page(viewport={"width": 1280, "height": 720})
        pg.goto(f.as_uri())
        pg.wait_for_function("window.__ready===true", timeout=30000)
        for ms in points:
            pg.evaluate(f"window.seek({ms})")
            heights.append(pg.evaluate("+document.getElementById('av-mouth').getAttribute('ry')"))
        br.close()

    distinct = len(set(round(h, 1) for h in heights))
    assert distinct >= 5, f"mouth barely moves across the beat: {sorted(set(heights))}"
    assert max(heights) > 8, f"mouth never opens wide: max ry={max(heights)}"


# --- video artefact ---------------------------------------------------------


@pytest.mark.skipif(not REPORT.exists(), reason="run services.studio.render first")
def test_rendered_video_matches_the_audio():
    """Requirement 6: the teaching video exists, and its duration is honest.

    record_video_dir emits VFR with no audio. Without the CFR normalisation step
    the mux drifts progressively across 26 beats.
    """
    r = json.loads(REPORT.read_text(encoding="utf-8"))
    assert Path(r["mp4"]).exists()
    assert r["beats"] >= 20
    assert abs(r["drift_ms"]) <= 200, (
        f"video {r['video_ms']}ms vs audio {r['audio_ms']}ms, "
        f"drift {r['drift_ms']}ms exceeds 200ms"
    )
