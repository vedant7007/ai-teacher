"""Hybrid retrieval: dense + BM25, fused with Reciprocal Rank Fusion.

Cross-lingual: the source book and the teaching language are independent, so a
query is embedded as given and, when a translation is supplied, as its
translation too. The two result sets are unioned before fusion, which lets a
Hindi question retrieve from an English textbook.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from services.ingest import embed
from services.ingest.chunk import Chunk
from services.ingest.index import DocIndex, _tokenize

RRF_K = 60
TOP_K = 8
CANDIDATES = 30


@dataclass
class Hit:
    chunk: Chunk
    score: float
    dense_rank: int | None
    sparse_rank: int | None

    def citation(self) -> dict:
        c = self.chunk
        return {
            "doc_id": c.doc_id, "chunk_id": c.id, "chapter": c.chapter,
            "section": c.section, "subsection": c.subsection, "page_start": c.page_start, "page_end": c.page_end,
            "char_start": c.char_start, "char_end": c.char_end,
        }


def _dense_ranks(idx: DocIndex, queries: list[str]) -> dict[int, int]:
    qv = embed.embed(queries, is_query=True)
    # Vectors are L2-normalised, so this dot product is cosine similarity.
    sims = (idx.vectors @ qv.T).max(axis=1)
    order = np.argsort(-sims)[:CANDIDATES]
    return {int(i): r for r, i in enumerate(order)}


def _sparse_ranks(idx: DocIndex, queries: list[str]) -> dict[int, int]:
    scores = np.zeros(len(idx.chunks), dtype=np.float32)
    for q in queries:
        scores = np.maximum(scores, np.asarray(idx.bm25.get_scores(_tokenize(q))))
    order = np.argsort(-scores)[:CANDIDATES]
    return {int(i): r for r, i in enumerate(order)}


def retrieve(
    idx: DocIndex,
    query: str,
    *,
    translation: str | None = None,
    top_k: int = TOP_K,
    section: str | list[str] | None = None,
) -> list[Hit]:
    queries = [query] + ([translation] if translation else [])

    dense = _dense_ranks(idx, queries)
    sparse = _sparse_ranks(idx, queries)

    fused: dict[int, float] = {}
    for ranks in (dense, sparse):
        for i, r in ranks.items():
            fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + r + 1)

    hits = [
        Hit(idx.chunks[i], s, dense.get(i), sparse.get(i))
        for i, s in sorted(fused.items(), key=lambda kv: -kv[1])
    ]
    if section:
        wants = [section] if isinstance(section, str) else list(section)
        wants = [w.strip().lower() for w in wants if w and w.strip()]
        scoped = [h for h in hits
                  if any(w in h.chunk.section.lower() for w in wants)]
        # Scoping must never return nothing, fall back to the whole document.
        hits = scoped or hits
    return hits[:top_k]


def groundedness(sentence: str, chunks: list[Chunk]) -> float:
    """Max cosine between a generated sentence and its cited chunks.

    Local and free, so verifying a whole lesson costs zero API requests. Used in
    place of a cross-encoder reranker, which is cut item 1.
    """
    if not chunks:
        return 0.0
    sv = embed.embed([sentence], is_query=True)
    cv = embed.embed([c.text for c in chunks])
    return float((cv @ sv.T).max())
