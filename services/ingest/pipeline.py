"""parse -> tree -> chunk -> embed -> index, in one call."""

from __future__ import annotations

import hashlib
from pathlib import Path

from . import index
from .chunk import chunk_tree
from .parse import parse
from .structure import build_tree, render_tree


def detect_lang(text: str) -> str:
    from langdetect import DetectorFactory, detect

    DetectorFactory.seed = 0
    try:
        return detect(text[:4000])
    except Exception:  # noqa: BLE001 - langdetect throws on short or symbolic text
        return "en"


def doc_id_for(path: str | Path) -> str:
    p = Path(path)
    digest = hashlib.sha256(p.read_bytes()).hexdigest()[:12]
    return f"{p.stem}-{digest}"


def ingest(path: str | Path, title: str | None = None, force: bool = False) -> index.DocIndex:
    path = Path(path)
    doc_id = doc_id_for(path)
    if index.exists(doc_id) and not force:
        return index.load(doc_id)

    lines = parse(path)
    if not lines:
        raise ValueError(f"no text extracted from {path}")

    title = title or path.stem
    tree = build_tree(lines, title)
    lang = detect_lang(" ".join(l.text for l in lines[:200]))
    chunks = chunk_tree(tree, doc_id, lang=lang)

    meta = {
        "doc_id": doc_id,
        "title": title,
        "filename": path.name,
        "pages": max(l.page for l in lines),
        "lines": len(lines),
        "chunks": len(chunks),
        "lang": lang,
    }
    return index.build(doc_id, chunks, tree.to_dict(), meta)


def tree_text(path: str | Path, title: str | None = None) -> str:
    lines = parse(path)
    return render_tree(build_tree(lines, title or Path(path).stem))
