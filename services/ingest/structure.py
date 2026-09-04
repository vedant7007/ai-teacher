"""Line list -> chapter / section / paragraph tree.

Headings are found by clustering font sizes, not by regex. The modal size of
substantial text lines is the body size; anything meaningfully larger is a
heading, and distinct heading sizes become nesting levels. Section numbering
("11.6.1") is used only to refine depth and to merge a heading that wrapped
onto a second line, never as the primary detector, so this works on documents
that do not number their sections.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from .parse import Line

HEADING_RATIO = 1.15      # a heading must be at least 15% larger than body text
MIN_BODY_LINE_CHARS = 25  # short lines are captions and labels, not body
MAX_HEADING_CHARS = 120

SECTION_NUM = re.compile(r"^(\d+(?:\.\d+)*)\s+(.*)$")


@dataclass
class Node:
    title: str
    level: int
    page: int
    number: str | None = None
    text: str = ""
    size: float = 0.0
    font: str = ""
    lines: list = field(default_factory=list)
    children: list["Node"] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title, "level": self.level, "page": self.page,
            "number": self.number, "chars": len(self.text),
            "children": [c.to_dict() for c in self.children],
        }


def body_size(lines: list[Line]) -> float:
    sizes = Counter(
        l.size for l in lines if len(l.text) >= MIN_BODY_LINE_CHARS
    )
    if not sizes:
        sizes = Counter(l.size for l in lines)
    return sizes.most_common(1)[0][0]


def _heading_levels(lines: list[Line], body: float) -> dict[float, int]:
    """Map each heading font size to a nesting level, largest size = level 0."""
    sizes = sorted(
        {l.size for l in lines
         if l.size >= body * HEADING_RATIO and len(l.text) <= MAX_HEADING_CHARS},
        reverse=True,
    )
    return {s: i for i, s in enumerate(sizes)}


def _is_heading_text(text: str) -> bool:
    """Reject decorative glyphs: page numbers, the '?' on a Questions box, rules."""
    return len(re.findall(r"[^\W\d_]", text)) >= 3 and len(text) <= MAX_HEADING_CHARS


def build_tree(lines: list[Line], doc_title: str) -> Node:
    body = body_size(lines)
    levels = _heading_levels(lines, body)
    title_size = max(levels, default=0.0)

    root = Node(title=doc_title, level=-1, page=lines[0].page if lines else 1)
    stack: list[Node] = [root]
    current: Node = root
    numbered_level = 0  # depth of the innermost numbered section currently open

    for line in lines:
        if not (line.size in levels and _is_heading_text(line.text)):
            current.text += line.text + " "
            current.lines.append(line)
            continue

        m = SECTION_NUM.match(line.text)
        number = m.group(1) if m else None

        # A heading that wrapped onto a second line: same size, same page, no
        # number of its own, and the heading it follows has no body text yet.
        if (number is None and current is not root and not current.text.strip()
                and current.page == line.page and current.size == line.size
                and current.font == line.font):
            current.title = f"{current.title} {line.text}".strip()
            continue

        if number:
            level = len(number.split("."))
            numbered_level = level
        elif line.size == title_size:
            level = 0  # the chapter title itself
        else:
            # Activity boxes, Questions, "What you have learnt". These are real
            # headings but must never outrank the section they sit inside.
            level = numbered_level + 1

        node = Node(line.text, level, line.page, number, size=line.size, font=line.font)
        while len(stack) > 1 and stack[-1].level >= level:
            stack.pop()
        stack[-1].children.append(node)
        stack.append(node)
        current = node

    return root


def _norm(s: str) -> str:
    """Curly apostrophes and NBSPs must not break a title lookup."""
    return (s.replace("’", "'").replace("‘", "'")
             .replace(" ", " ").strip().lower())


def find_section(root: Node, query: str) -> Node | None:
    """Resolve 'Chapter 11', '11.4', or 'Ohm's law' to a node in the tree."""
    q = _norm(query)
    num = re.search(r"\d+(?:\.\d+)*", q)

    def walk(n: Node):
        yield n
        for c in n.children:
            yield from walk(c)

    nodes = list(walk(root))
    if num:
        for n in nodes:
            if n.number == num.group(0):
                return n
    for n in nodes:
        if q in _norm(n.title):
            return n
    # Fall back to the best word-overlap match.
    words = {w for w in re.findall(r"\w+", q) if len(w) > 3}
    if words:
        best = max(nodes, key=lambda n: len(words & set(re.findall(r"\w+", _norm(n.title)))))
        if words & set(re.findall(r"\w+", _norm(best.title))):
            return best
    return None


def render_tree(node: Node, indent: int = 0) -> str:
    """Human-readable tree, printed in the acceptance output."""
    out = []
    if node.level >= 0:
        pad = "  " * indent
        chars = f"  [{len(node.text.strip())} chars]" if node.text.strip() else ""
        out.append(f"{pad}p{node.page:<3} {node.title}{chars}")
    for c in node.children:
        out.append(render_tree(c, indent + (1 if node.level >= 0 else 0)))
    return "\n".join(x for x in out if x)
