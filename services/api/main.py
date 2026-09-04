"""FastAPI entrypoint. Phase 0: health, provider status, budget counter."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from services.ingest import index
from services.ingest.pipeline import ingest
from services.llm import budget, cache, router
from services.rag.retrieve import retrieve

STORAGE = Path("storage")
STORAGE.mkdir(exist_ok=True)

# Swagger moves off /docs, which the brief reserves for document endpoints.
app = FastAPI(title="AI Teacher", version="0.1.0", docs_url="/swagger")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ponytail: open CORS, demo app with no user data to protect
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/storage", StaticFiles(directory=str(STORAGE)), name="storage")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "providers": router.available(),
        "cache": cache.stats(),
        "budget": budget.today(),
    }


@app.get("/budget")
def budget_today() -> dict:
    """Feeds the trace panel's request counter."""
    return budget.today()


# --- documents --------------------------------------------------------------

UPLOADS = STORAGE / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)


@app.get("/docs")
def list_docs() -> list[dict]:
    return index.list_docs()


@app.post("/docs")
async def upload_doc(file: UploadFile = File(...), title: str = Form(None)) -> dict:
    dest = UPLOADS / file.filename
    dest.write_bytes(await file.read())
    try:
        idx = ingest(dest, title or dest.stem)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return idx.meta


@app.get("/docs/{doc_id}/tree")
def doc_tree(doc_id: str) -> dict:
    if not index.exists(doc_id):
        raise HTTPException(status_code=404, detail="unknown doc_id")
    idx = index.load(doc_id)
    return {"meta": idx.meta, "tree": idx.tree}


@app.get("/docs/{doc_id}/search")
def doc_search(doc_id: str, q: str, translation: str = None, k: int = 8) -> dict:
    if not index.exists(doc_id):
        raise HTTPException(status_code=404, detail="unknown doc_id")
    idx = index.load(doc_id)
    hits = retrieve(idx, q, translation=translation, top_k=k)
    return {
        "query": q,
        "hits": [
            {"score": round(h.score, 5), "text": h.chunk.text[:400], **h.citation()}
            for h in hits
        ],
    }
