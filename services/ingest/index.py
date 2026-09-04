"""On-disk index: a numpy matrix for dense vectors plus BM25 for sparse.

At a few thousand chunks a normalised matrix and one dot product beats a vector
database on both latency and setup cost, and it has no native dependency to fail
on Windows. Swap in FAISS only if the corpus outgrows memory.
"""

from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from . import embed
from .chunk import Chunk

INDEX_DIR = Path("storage/index")


def _tokenize(text: str) -> list[str]:
    # Whitespace plus lowering. Devanagari has no case, and this keeps the
    # sparse side language-agnostic without a per-language analyser.
    return text.lower().split()


@dataclass
class DocIndex:
    doc_id: str
    chunks: list[Chunk]
    vectors: np.ndarray
    bm25: BM25Okapi
    tree: dict
    meta: dict

    def save(self) -> Path:
        d = INDEX_DIR / self.doc_id
        d.mkdir(parents=True, exist_ok=True)
        np.save(d / "vectors.npy", self.vectors)
        (d / "chunks.json").write_text(
            json.dumps([c.to_dict() for c in self.chunks], ensure_ascii=False), encoding="utf-8"
        )
        (d / "tree.json").write_text(json.dumps(self.tree, ensure_ascii=False), encoding="utf-8")
        (d / "meta.json").write_text(json.dumps(self.meta, ensure_ascii=False), encoding="utf-8")
        with (d / "bm25.pkl").open("wb") as fh:
            pickle.dump(self.bm25, fh)
        return d


def build(doc_id: str, chunks: list[Chunk], tree: dict, meta: dict) -> DocIndex:
    vectors = embed.embed([c.text for c in chunks])
    bm25 = BM25Okapi([_tokenize(c.text) for c in chunks])
    idx = DocIndex(doc_id, chunks, vectors, bm25, tree, meta)
    idx.save()
    return idx


def load(doc_id: str) -> DocIndex:
    d = INDEX_DIR / doc_id
    chunks = [Chunk(**c) for c in json.loads((d / "chunks.json").read_text(encoding="utf-8"))]
    with (d / "bm25.pkl").open("rb") as fh:
        bm25 = pickle.load(fh)
    return DocIndex(
        doc_id=doc_id,
        chunks=chunks,
        vectors=np.load(d / "vectors.npy"),
        bm25=bm25,
        tree=json.loads((d / "tree.json").read_text(encoding="utf-8")),
        meta=json.loads((d / "meta.json").read_text(encoding="utf-8")),
    )


def exists(doc_id: str) -> bool:
    return (INDEX_DIR / doc_id / "chunks.json").exists()


def list_docs() -> list[dict]:
    if not INDEX_DIR.exists():
        return []
    out = []
    for d in sorted(INDEX_DIR.iterdir()):
        meta = d / "meta.json"
        if meta.exists():
            out.append(json.loads(meta.read_text(encoding="utf-8")))
    return out
