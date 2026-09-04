"""Visual Director: guardrails over the model's visual choice.

The model picks a visual per beat. This layer enforces what a physics or maths
teacher would actually draw, independent of the model's mood:

  - a beat that asserts a proportional relationship gets a `graph`, because a
    straight line IS the claim. This is the defining visual of the Electricity
    chapter and the brief names graphs explicitly for maths and physics.
  - a beat that states a formula keeps its `equation`.
  - anything unrenderable falls back to `bullets` rather than breaking the stage.

Every decision records a human-readable `reason` and, when overridden, what it
was promoted from, so the trace panel can show the pedagogy rather than hide it.
"""

from __future__ import annotations

import re

from services.llm.schemas import Beat, LessonPlan, VisualSpec

# Multilingual: the demo teaches Hindi from an English source, so markers must
# fire on both scripts.
PROPORTIONALITY = re.compile(
    r"समानुपात|आनुपातिक|अनुपात|सीधा\s*संबंध|सरल\s*रेखा|"
    r"proportion|ratio|straight\s*line|linear|varies\s+(?:directly|inversely)|"
    r"V\s*/\s*I|V-I|graph|ग्राफ",
    re.IGNORECASE,
)
# A formula being stated, rather than a relationship being explored.
FORMULA = re.compile(r"=|सूत्र|formula|equation|समीकरण")

PLOTTABLE_INTENTS = {"explain", "example", "demo"}

# A beat that is describing how to BUILD the apparatus wants a circuit diagram,
# even though it goes on to mention the ratio the experiment will reveal.
APPARATUS = re.compile(
    r"सर्किट\s*बनाते|एमीटर|वोल्टमीटर|जोड़ते|उपकरण|"
    r"ammeter|voltmeter|circuit\s+(?:with|using|containing)|apparatus|set\s*up",
    re.IGNORECASE,
)
# Explicitly talking about the SHAPE of the relationship, not just its existence.
DIRECT_INVERSE = re.compile(
    r"सीधे\s*आनुपातिक|व्युत्क्रमानुपाती|समानुपाती|"
    r"directly\s+proportional|inversely\s+proportional",
    re.IGNORECASE,
)
SHAPE = re.compile(r"सरल\s*रेखा|straight\s*line|ग्राफ|graph|plot|प्लॉट", re.IGNORECASE)


def _straight_line(x_label: str, y_label: str, name: str, slope: float = 1.5,
                   n: int = 5) -> dict:
    """A proportional series, used when a beat claims proportionality but the
    model gave no plottable payload."""
    return {
        "type": "line",
        "x_label": x_label,
        "y_label": y_label,
        "series": [{"name": name, "points": [[i, round(i * slope, 2)] for i in range(n)]}],
    }


def _has_plottable_payload(v: VisualSpec) -> bool:
    series = (v.payload or {}).get("series")
    return bool(series and isinstance(series, list) and series[0].get("points"))


def _renderable(v: VisualSpec) -> bool:
    p = v.payload or {}
    if v.kind == "equation":
        return bool(p.get("latex"))
    if v.kind == "graph":
        return _has_plottable_payload(v)
    if v.kind == "diagram":
        return bool(p.get("mermaid"))
    if v.kind == "code":
        return bool(p.get("source"))
    if v.kind == "bullets":
        return bool(p.get("items") or p.get("heading"))
    return False


def _promote_to_graph(beat: Beat) -> bool:
    """Should this beat be a graph regardless of what the model chose?"""
    if beat.visual.kind == "graph":
        return False
    if beat.intent not in PLOTTABLE_INTENTS:
        return False
    if not PROPORTIONALITY.search(beat.script):
        return False
    # Building the apparatus is a diagram, not a plot.
    if APPARATUS.search(beat.script) and beat.visual.kind == "diagram":
        return False
    # Promote only with real data to plot, or when the beat explicitly describes
    # the shape of the line. Never invent readings to justify a chart.
    if _has_plottable_payload(beat.visual):
        return True
    # No readings, and we cannot infer which quantities go on which axis from
    # prose. A mislabelled physics graph is worse than the equation it replaced,
    # so promotion stops here. Graph coverage is driven by the prompt, where the
    # model knows the quantities and can label the axes itself.
    return False


def direct(plan: LessonPlan) -> dict:
    """Apply guardrails in place. Returns a report for the trace panel."""
    report = {"promoted_to_graph": [], "repaired": [], "kept": 0}

    for beat in plan.beats:
        if _promote_to_graph(beat):
            old = beat.visual.kind
            schematic = not _has_plottable_payload(beat.visual)
            payload = (
                _straight_line("Current I (A)", "Potential difference V (V)", "Conductor")
                if schematic else beat.visual.payload
            )
            # A schematic line shows shape, not measurements. The renderer drops
            # numeric ticks so invented values are never read as real data.
            payload = {**payload, "schematic": schematic}
            beat.visual = VisualSpec(
                kind="graph",
                reason=(beat.visual.reason or "")
                       + (" Shown as a schematic line: the shape of the relationship is "
                          "the claim being made." if schematic else
                          " Plotted as a graph because the straight line is the claim: "
                          "the relationship itself is what the student must see."),
                subject=beat.visual.subject or "physics",
                payload=payload,
                timeline=beat.visual.timeline,
            )
            report["promoted_to_graph"].append({"beat": beat.id, "from": old})
            continue

        if not _renderable(beat.visual):
            old = beat.visual.kind
            beat.visual = VisualSpec(
                kind="bullets",
                reason=beat.visual.reason or "Key points from this explanation.",
                subject=beat.visual.subject,
                payload={"heading": "", "items": _sentences(beat.script)[:4]},
                timeline=[],
            )
            report["repaired"].append({"beat": beat.id, "from": old, "to": "bullets"})
            continue

        report["kept"] += 1

    return report


def _sentences(script: str) -> list[str]:
    parts = re.split(r"(?<=[.।?!])\s+", script.strip())
    return [p.strip() for p in parts if len(p.strip()) > 8]
