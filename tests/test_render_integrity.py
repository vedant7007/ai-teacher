"""Render integrity: what duration and file-property checks could not catch.

Two defects shipped into a rendered video while every existing test passed:
a Mermaid "Syntax error" card screenshotted into beat 1, and the possibility of
a silent audio track behind a correct-looking duration. Both were invisible to
assertions about file size, stream presence and length.

These tests look at what is actually on screen and actually audible.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from services.llm.schemas import LessonPlan
from services.visual.mermaid import sanitize

DEMO = Path("data/demo/lesson_ohms_law_hi.json")
REPORT = Path("storage/studio/render_report.json")

# Text that must never appear in a rendered slide.
FORBIDDEN = ["syntax error", "mermaid version", "undefined", "nan", "[object object]"]


@pytest.fixture(scope="module")
def plan() -> LessonPlan:
    return LessonPlan(**json.loads(DEMO.read_text(encoding="utf-8")))


def _mean_volume_db(path: Path) -> float:
    r = subprocess.run(
        ["ffmpeg", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    m = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?) dB", r.stderr)
    if not m:
        pytest.fail(f"volumedetect produced no mean_volume for {path}")
    return float(m.group(1))


# --- audio ------------------------------------------------------------------


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
@pytest.mark.skipif(not REPORT.exists(), reason="run services.studio.render first")
def test_final_mp4_has_audible_audio():
    """A silent track has mean_volume near -91 dB and a perfectly correct duration."""
    mp4 = Path(json.loads(REPORT.read_text(encoding="utf-8"))["mp4"])
    assert mp4.exists()
    mean = _mean_volume_db(mp4)
    assert mean > -50.0, f"audio is effectively silent: mean_volume {mean} dB"


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
@pytest.mark.skipif(not REPORT.exists(), reason="run services.studio.render first")
def test_no_individual_beat_is_silent():
    """An overall mean can hide one silent beat among twenty six."""
    clips = [Path(c) for c in json.loads(REPORT.read_text(encoding="utf-8"))["clips"]]
    silent = [(c.name, v) for c in clips if (v := _mean_volume_db(c)) < -50.0]
    assert not silent, f"silent beats: {silent}"


# --- rendered content -------------------------------------------------------


def test_mermaid_sanitiser_quotes_problem_labels():
    """The three shapes that produced an error card on the demo lesson."""
    assert sanitize("C[कम बहाव (उच्च प्रतिरोध)]") == 'C["कम बहाव (उच्च प्रतिरोध)"]'
    assert sanitize("D{तार (लम्बाई, मोटाई)}") == 'D{"तार (लम्बाई, मोटाई)"}'
    assert sanitize("subgraph विद्युत परिपथ") == 'subgraph "विद्युत परिपथ"'
    # Colour directives are the theme's job, not the model's.
    assert sanitize("style A fill:#add8e6") == ""
    assert sanitize("linkStyle 0 stroke:blue;") == ""


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="browser tests need a desktop")
def test_no_beat_renders_an_error_card(plan):
    """Mermaid renders its own parse failure AS AN SVG.

    So "an svg exists" is not proof of success, which is how this reached a
    rendered video unnoticed. Assert on the visible text instead.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright not installed")

    from services.visual.slide import render_slide

    out = Path("storage/sweep"); out.mkdir(parents=True, exist_ok=True)
    offenders = []
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        pg = br.new_page(viewport={"width": 1280, "height": 720})
        for beat in plan.beats:
            f = (out / f"{beat.id}.html").resolve()
            f.write_text(render_slide(beat, [], title=beat.intent, avatar=True),
                         encoding="utf-8")
            pg.goto(f.as_uri())
            pg.wait_for_function("window.__ready===true", timeout=25000)
            pg.wait_for_timeout(300)
            text = (pg.inner_text("body") or "").lower()
            hits = [w for w in FORBIDDEN if w in text]
            if hits:
                offenders.append((beat.id, hits))
        br.close()
    assert not offenders, f"beats rendering an error card: {offenders}"


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="browser tests need a desktop")
def test_every_beat_slide_has_visible_content(plan):
    """A container with nothing in it still passes a 'renders' check."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright not installed")

    from services.visual.slide import render_slide

    out = Path("storage/sweep"); out.mkdir(parents=True, exist_ok=True)
    empty = []
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        pg = br.new_page(viewport={"width": 1280, "height": 720})
        for beat in plan.beats:
            f = (out / f"{beat.id}.html").resolve()
            f.write_text(render_slide(beat, [], title=beat.intent, avatar=True),
                         encoding="utf-8")
            pg.goto(f.as_uri())
            pg.wait_for_function("window.__ready===true", timeout=25000)
            pg.wait_for_timeout(300)
            visible = pg.evaluate("""(() => {
                const stage = document.querySelector('.stage');
                if (!stage) return 0;
                return [...stage.querySelectorAll('*')].filter(el => {
                    const r = el.getBoundingClientRect();
                    return r.width > 4 && r.height > 4 &&
                           (el.textContent || '').trim().length > 0;
                }).length;
            })()""")
            if visible < 1:
                empty.append(beat.id)
        br.close()
    assert not empty, f"beats whose slide renders nothing visible: {empty}"
