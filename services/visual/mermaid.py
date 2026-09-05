"""Mermaid source sanitising.

Models emit Mermaid that Mermaid itself rejects. Three failures were observed on
the demo lesson, all of which rendered a "Syntax error in text" card that was
then screenshotted straight into the video:

  - parentheses inside a node label:  C[कम बहाव (उच्च प्रतिरोध)]
  - parentheses and commas in a rhombus: D{तार (लम्बाई, मोटाई)}
  - an unquoted multi-word subgraph title: subgraph विद्युत परिपथ

Quoting the label text fixes all three. Colour directives are stripped so one
theme owns the palette and pale nodes cannot render pale text.

Sanitising reduces failures; it cannot guarantee zero. The renderer therefore
also detects an error card at runtime and falls back to bullets, so nothing
broken can reach the screen.
"""

from __future__ import annotations

import re

# Colour and class directives: the theme owns the palette.
_DROP = re.compile(r"^\s*(style|linkstyle|classdef|class)\s", re.IGNORECASE)

# One pattern per bracket type. The label excludes only its OWN delimiters, so
# "C[कम बहाव (उच्च प्रतिरोध)]" keeps its parentheses instead of terminating at
# the first ")" and leaving an unbalanced node for the parser to choke on.
_NODES = [
    re.compile(r"(?P<id>\b[A-Za-z_][\w-]*)(?P<open>\[)(?P<label>[^\[\]]*)(?P<close>\])"),
    re.compile(r"(?P<id>\b[A-Za-z_][\w-]*)(?P<open>\{)(?P<label>[^{}]*)(?P<close>\})"),
    re.compile(r"(?P<id>\b[A-Za-z_][\w-]*)(?P<open>\()(?P<label>[^()]*)(?P<close>\))"),
]

_SUBGRAPH = re.compile(r"^(?P<indent>\s*)subgraph\s+(?P<title>.+?)\s*$", re.IGNORECASE)


def _quote(label: str) -> str:
    label = label.strip()
    if not label:
        return label
    if label.startswith('"') and label.endswith('"'):
        return label
    # Mermaid has no escape for a double quote inside a quoted label.
    return '"' + label.replace('"', "'") + '"'


def sanitize(src: str) -> str:
    """Make model-written Mermaid parseable, without changing what it says."""
    lines: list[str] = []
    for raw in (src or "").splitlines():
        if _DROP.match(raw):
            continue

        m = _SUBGRAPH.match(raw)
        if m:
            title = m.group("title")
            if not title.startswith('"') and re.search(r"[\s(),]", title):
                raw = f'{m.group("indent")}subgraph {_quote(title)}'
            lines.append(raw)
            continue

        for pat in _NODES:
            raw = pat.sub(
                lambda mm: (
                    mm.group("id") + mm.group("open")
                    + _quote(mm.group("label")) + mm.group("close")
                ),
                raw,
            )
        lines.append(raw)
    return "\n".join(lines).strip()


def fallback_items(script: str, limit: int = 4) -> list[str]:
    """Bullets to show instead of a diagram that will not parse."""
    parts = re.split(r"(?<=[.।?!])\s+", (script or "").strip())
    return [p.strip() for p in parts if len(p.strip()) > 12][:limit]
