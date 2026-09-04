"""Embedding behind a one-line-swappable interface.

Default is paraphrase-multilingual-MiniLM-L12-v2 (~470MB, 384 dims), which
handles Devanagari and loads fast on CPU. If retrieval quality is poor, change
EMBED_MODEL to BAAI/bge-m3 and re-index. Nothing else in the codebase needs to
know which model is in use.
"""

from __future__ import annotations

import os
import threading

import numpy as np

EMBED_MODEL = os.environ.get("EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

_model = None
_lock = threading.Lock()


def _get_model():
    global _model
    with _lock:
        if _model is None:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer(EMBED_MODEL)
    return _model


def embed(texts: list[str], *, is_query: bool = False) -> np.ndarray:
    """L2-normalised float32 embeddings, so cosine similarity is a dot product."""
    if not texts:
        return np.zeros((0, dim()), dtype=np.float32)
    # bge models want an instruction prefix on queries, MiniLM does not.
    if is_query and "bge" in EMBED_MODEL.lower():
        texts = [f"Represent this sentence for searching relevant passages: {t}" for t in texts]
    vecs = _get_model().encode(
        texts, batch_size=32, convert_to_numpy=True, normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vecs.astype(np.float32)


def dim() -> int:
    return _get_model().get_sentence_embedding_dimension()


def model_name() -> str:
    return EMBED_MODEL
