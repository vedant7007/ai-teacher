"""Structure-aware chunking.

Chunks never cross a section boundary, so every chunk inherits an exact
chapter, section and page for its citation. Within a section we pack lines to
300 to 500 tokens with 15 percent overlap, and refuse to split in the middle of
an equation or a worked example, since half an equation retrieves as noise and
cites as a lie.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict

from .structure import Node

TARGET_TOKENS = 400
MIN_TOKENS = 300
MAX_TOKENS = 500
OVERLAP = 0.15

# A line that is mostly symbols, or names a numbered equation, must stay with
# its neighbours.
EQUATION_HINT = re.compile(r"\(\d+\.\d+\)\s*$|^[\s\d\W]*$|[=∝Ω√±×÷]")


def _tokens(text: str) -> int:
    return max(1, len(text) // 4)


@dataclass
class Chunk:
    id: str
    doc_id: str
    text: str
    chapter: str
    section: str
    subsection: str
    page_start: int
    page_end: int
    char_start: int
    char_end: int
    lang: str

    def to_dict(self) -> dict:
        return asdict(self)


def _is_equation(text: str) -> bool:
    return bool(EQUATION_HINT.search(text)) and len(text) < 120


def _pack(lines: list, ) -> list[list]:
    """Greedy pack lines into token-sized groups, not splitting equations."""
    groups: list[list] = []
    cur: list = []
    cur_tokens = 0

    for line in lines:
        t = _tokens(line.text)
        if cur and cur_tokens + t > MAX_TOKENS:
            # Do not end a chunk on an equation, it belongs with its lead-in.
            if _is_equation(line.text) and cur_tokens + t <= MAX_TOKENS * 1.2:
                cur.append(line)
                cur_tokens += t
                continue
            groups.append(cur)
            # 15 percent overlap, carried as whole trailing lines.
            keep, kept = [], 0
            for prev in reversed(cur):
                if kept >= cur_tokens * OVERLAP:
                    break
                keep.insert(0, prev)
                kept += _tokens(prev.text)
            cur = keep + [line]
            cur_tokens = kept + t
        else:
            cur.append(line)
            cur_tokens += t

    if cur:
        # A short tail merges back rather than becoming a stub chunk.
        if groups and cur_tokens < MIN_TOKENS // 2:
            groups[-1].extend(cur)
        else:
            groups.append(cur)
    return groups


def chunk_tree(root: Node, doc_id: str, lang: str = "en") -> list[Chunk]:
    chunks: list[Chunk] = []
    cursor = 0

    def chapter_of(path: list[Node]) -> str:
        return path[0].title if path else root.title

    def section_of(path: list[Node], node: Node) -> str:
        """Nearest numbered ancestor. An Activity box belongs to its section."""
        for n in reversed(path + [node]):
            if n.number:
                return n.title
        return node.title if node.level >= 0 else root.title

    def walk(node: Node, path: list[Node]):
        nonlocal cursor
        if node.lines:
            section = section_of(path, node)
            subsection = node.title if node.level >= 0 else root.title
            for group in _pack(node.lines):
                text = " ".join(l.text for l in group).strip()
                if not text:
                    continue
                chunks.append(Chunk(
                    id=f"{doc_id}:{len(chunks):04d}",
                    doc_id=doc_id,
                    text=text,
                    chapter=chapter_of(path),
                    section=section,
                    subsection=subsection,
                    page_start=min(l.page for l in group),
                    page_end=max(l.page for l in group),
                    char_start=cursor,
                    char_end=cursor + len(text),
                    lang=lang,
                ))
                cursor += len(text)
        for c in node.children:
            walk(c, path + [node] if node.level >= 0 else path)

    walk(root, [])
    # Decorative glyphs (a bare page number, a rule) can form a stub chunk that
    # only pollutes retrieval. Drop anything too small to answer a question.
    kept = [c for c in chunks if _tokens(c.text) >= 15]
    return kept or chunks
