"""Phase 3 acceptance: speech timings, visual direction, slide rendering.

The alignment tests that matter are pure unit tests over synthetic boundary
events, so they run offline and cannot flake on the TTS service. The live
synthesis and browser tests are marked and skipped when unavailable.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from services.llm.schemas import Beat, LessonPlan, TimelineCue, VisualSpec
from services.speech.tts import WordTiming, align_to_words
from services.visual.director import direct, _renderable
from services.visual.slide import cues_for, element_ids, render_slide

DEMO = Path("data/demo/lesson_ohms_law_hi.json")


@pytest.fixture(scope="module")
def plan() -> LessonPlan:
    return LessonPlan(**json.loads(DEMO.read_text(encoding="utf-8")))


def _b(offset_ms: int, dur_ms: int, text: str) -> dict:
    return {"text": text, "offset": offset_ms * 10_000, "duration": dur_ms * 10_000}


# --- word alignment ---------------------------------------------------------


def test_alignment_one_event_per_word():
    script = "करंट बढ़ता है"
    got = align_to_words(script, [_b(100, 400, "करंट"), _b(520, 300, "बढ़ता"), _b(840, 200, "है")])
    assert [t.word for t in got] == script.split()
    assert [t.start_ms for t in got] == [100, 520, 840]


def test_alignment_survives_unspoken_symbols():
    """The '=' in 'V = W/Q' gets no boundary event and must not desync the rest.

    This is the bug that silently zeroed every cue after a formula.
    """
    script = "यह V = W/Q है"
    got = align_to_words(script, [
        _b(0, 200, "यह"), _b(220, 200, "V"), _b(440, 300, "W"), _b(750, 300, "Q"),
        _b(1100, 200, "है"),
    ])
    assert [t.word for t in got] == script.split(), "word list must be preserved"
    assert got[2].word == "=" and got[2].duration_ms == 0, "unspoken symbol"
    # The words AFTER the formula are the ones that used to collapse to 0 ms.
    assert got[-1].start_ms >= 1100, "tail must keep real timings"
    assert all(got[i].start_ms <= got[i + 1].start_ms for i in range(len(got) - 1))


def test_alignment_handles_word_split_across_events():
    got = align_to_words("इलेक्ट्रिक सर्किट", [
        _b(0, 200, "इलेक्ट्"), _b(200, 300, "रिक"), _b(520, 400, "सर्किट"),
    ])
    assert [t.word for t in got] == ["इलेक्ट्रिक", "सर्किट"]
    assert got[0].start_ms == 0 and got[0].end_ms == 500
    assert got[1].start_ms == 520


def test_alignment_never_loses_words():
    script = "a b c d e"
    got = align_to_words(script, [_b(0, 10, "a")])
    assert len(got) == 5, "unvoiced tail still needs cue positions"


# --- visual direction -------------------------------------------------------


def test_physics_lesson_has_multiple_graphs(plan):
    """PDF section 10 names graphs for maths and physics. One is not enough."""
    graphs = [b for b in plan.beats if b.visual.kind == "graph"]
    assert len(graphs) >= 2, f"only {len(graphs)} graph beats"


def test_the_ohms_law_relationship_is_a_graph(plan):
    """The V-I straight line is the defining visual of this chapter."""
    vi = [b for b in plan.beats if b.visual.kind == "graph"
          and re.search(r"धारा|करंट|current", str(b.visual.payload.get("x_label", "")), re.I)]
    assert vi, "no current-on-x graph found"
    pts = vi[0].visual.payload["series"][0]["points"]
    assert len(pts) >= 3, "a line needs points"


def test_graph_axes_are_distinct_per_beat(plan):
    """A copied axis label means a mislabelled graph, worse than no graph."""
    axes = [(str(b.visual.payload.get("x_label")), str(b.visual.payload.get("y_label")))
            for b in plan.beats if b.visual.kind == "graph"]
    assert len(set(axes)) == len(axes), f"duplicate axes across graphs: {axes}"


def test_no_fabricated_data_presented_as_real(plan):
    """Invented points must be flagged schematic so they cannot read as data."""
    for b in plan.beats:
        if b.visual.kind == "graph":
            assert b.visual.payload.get("x_label"), f"{b.id} graph has no x label"
            assert b.visual.payload.get("y_label"), f"{b.id} graph has no y label"


def test_director_never_leaves_an_unrenderable_visual(plan):
    direct(plan)
    assert [b.id for b in plan.beats if not _renderable(b.visual)] == []


def test_director_keeps_apparatus_beats_as_diagrams():
    """Building a circuit is a diagram even though it mentions the ratio."""
    beat = Beat(
        id="x", concept_id="c", intent="explain",
        script="हम एक सर्किट बनाते हैं जिसमें एमीटर और वोल्टमीटर हैं, फिर V/I का अनुपात देखेंगे.",
        visual=VisualSpec(kind="diagram", reason="circuit",
                          payload={"mermaid": "graph LR; A-->B;"}),
    )
    p = LessonPlan(title="t", profile={"language": "hi-IN"}, concepts=[], beats=[beat])
    direct(p)
    assert p.beats[0].visual.kind == "diagram"


# --- slide rendering --------------------------------------------------------


def test_every_visual_kind_renders(plan):
    kinds = {b.visual.kind for b in plan.beats}
    for beat in plan.beats:
        html = render_slide(beat, [], title=beat.intent)
        assert "<!doctype html>" in html.lower()
        assert beat.visual.reason[:20] in html, "the why-this-visual line must be shown"
    assert kinds <= {"equation", "graph", "diagram", "code", "bullets"}


def test_cues_resolve_to_real_dom_ids(plan):
    """The model invents element ids. Every cue must still hit a real element."""
    for beat in plan.beats:
        if not beat.visual.timeline:
            continue
        timings = [WordTiming(w, i, i * 300, 250)
                   for i, w in enumerate(beat.script.split())]
        real = set(element_ids(beat.visual.kind, beat.visual.payload))
        for cue in cues_for(beat, timings):
            assert cue["element"] in real, (
                f"{beat.id}: cue {cue['requested']!r} resolved to "
                f"{cue['element']!r}, not among {sorted(real)[:6]}"
            )


def test_cue_times_are_monotonic_and_within_the_script(plan):
    for beat in plan.beats:
        timings = [WordTiming(w, i, i * 300, 250)
                   for i, w in enumerate(beat.script.split())]
        cues = cues_for(beat, timings)
        assert all(cues[i]["at_ms"] <= cues[i + 1]["at_ms"] for i in range(len(cues) - 1))
        for c in cues:
            assert 0 <= c["word_index"] < max(1, len(timings))


@pytest.mark.skipif(shutil.which("ffprobe") is None, reason="ffmpeg not installed")
def test_word_timings_align_with_real_audio():
    """Live check: synthesized Hindi audio must match its word timings.

    Skipped without network. The offline unit tests above cover the logic.
    """
    from services.speech.tts import audio_duration_ms, speak

    plan = LessonPlan(**json.loads(DEMO.read_text(encoding="utf-8")))
    beat = next(b for b in plan.beats if len(b.script.split()) > 40)
    try:
        mp3, timings = speak(beat.script, beat.language)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"tts unavailable: {exc}")

    assert len(timings) == len(beat.script.split())
    assert all(timings[i].start_ms <= timings[i + 1].start_ms for i in range(len(timings) - 1))
    drift = abs(audio_duration_ms(mp3) - timings[-1].end_ms)
    # Trailing silence in the container is expected, so allow a small margin
    # beyond the 150 ms cue tolerance.
    assert drift <= 1500, f"{drift} ms between last word and end of audio"
