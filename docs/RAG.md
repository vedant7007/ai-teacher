# RAG and Knowledge Grounding

## Pipeline

```
parse -> structure tree -> chunk -> embed -> index -> hybrid retrieve -> ground
```

Every stage runs locally. Indexing a chapter costs **zero API requests**.

## 1. Parse

`services/ingest/parse.py`, PyMuPDF for PDF, python-docx and python-pptx for
Office files. Each line carries page, font size, font name and x/y geometry.

NCERT PDFs fake bold by drawing a heading four or five times at sub-pixel
offsets, each pass split into overlapping horizontal fragments. Naive extraction
returns this for a single heading:

```
"11.5 FA"  "11.5 FACTORS ON WHICH THE RESIST"  "CTORS ON WHICH THE RESISTANCE OF A"  "ANCE OF A"
```

`_cover_yband()` reconstructs each visual line as a greedy left-to-right cover:
start at the leftmost fragment, then repeatedly take the fragment beginning where
the previous one ended and extending furthest right. A fragment starting well
past the cursor opens a new line instead, which keeps Activity side-boxes from
being glued onto body text. A leftover overprint that starts mid-word is dropped
because it is always a substring of the correctly reconstructed line.

## 2. Structure

`services/ingest/structure.py`. Headings are found by **font-size clustering**,
not regex: the modal size of substantial lines is the body size, and anything at
least 15 percent larger is a heading candidate. Candidates need three or more
letters, which rejects decorative page numbers and the "?" glyph on Questions
boxes.

Section numbering refines depth but never detects headings, so unnumbered
documents still produce a tree. Unnumbered headings (Activity boxes, "What you
have learnt") become children of the numbered section they sit inside and can
never outrank it. Font name discriminates section headings from Activity
headings, which share a font size.

Extracted tree for NCERT Class 10 Science Chapter 11, matching the printed book:

```
Electricity
  11.1 ELECTRIC CURRENT AND CIRCUIT
  11.2 ELECTRIC POTENTIAL AND POTENTIAL DIFFERENCE
  11.3 CIRCUIT DIAGRAM
  11.4 OHM'S LAW
    Activity 11.1 / Activity 11.2
  11.5 FACTORS ON WHICH THE RESISTANCE OF A CONDUCTOR DEPENDS
  11.6 RESISTANCE OF A SYSTEM OF RESISTORS
    11.6.1 Resistors in Series
    11.6.2 Resistors in Parallel
  11.7 HEATING EFFECT OF ELECTRIC CURRENT
    11.7.1 Practical Applications
  11.8 ELECTRIC POWER
```

`find_section()` resolves "Chapter 11", "11.4" or "Ohm's law" to a real node,
normalising curly apostrophes so "Ohm's law" matches "OHM'S LAW".

## 3. Chunk

Structure-aware, 300 to 500 tokens, 15 percent overlap carried as whole trailing
lines. Chunks never cross a section boundary, so each inherits an exact chapter,
section and page span for citation. A line that looks like an equation stays with
its lead-in rather than ending a chunk.

Each chunk records the **nearest numbered section**, not the leaf heading. Section
11.6.2 holds only 140 characters of its own text and all the substance lives in
its child Activity 11.6, so leaf-title attribution would cite "Activity 11.6" and
lose the section entirely.

## 4. Index

`numpy` matrix of L2-normalised float32 vectors plus `rank_bm25`. At a few
thousand chunks a dot product beats a vector database on latency and setup, and
has no native dependency to fail on Windows. Persisted to `storage/index/<doc_id>/`.

## 5. Embed

`paraphrase-multilingual-MiniLM-L12-v2`, 384 dims, handles Devanagari. Behind a
one-line-swappable interface in `services/ingest/embed.py`; set `EMBED_MODEL` to
`BAAI/bge-m3` and re-index if quality demands it. It did not: the acceptance
suite scores 10/10 on MiniLM.

## 6. Retrieve

Dense and BM25 candidates fused by Reciprocal Rank Fusion, `k=60`, top 8.

**Cross-lingual:** a query is embedded as given and, when a translation is
supplied, as its translation, then the result sets are unioned before fusion.
This lets a Hindi question retrieve from an English textbook and the reverse,
since the source language and the teaching language are independent.

**Section scoping:** the lesson planner retrieves with `section="11.4"` rather
than a bare semantic query. Short queries are weak: "Ohm's law" alone ranks 11.7
above 11.4, while scoped to 11.4 it returns the correct pages. Scoping never
returns nothing, it falls back to the whole document.

## 7. Ground

`groundedness()` is the maximum cosine similarity between a generated sentence
and its cited chunks. Local, free, and used instead of a cross-encoder reranker
(cut item 1), so verifying a whole lesson costs zero API requests.

It separates true from false claims about the same section:

| Sentence | Score |
|---|---|
| "The potential difference across a conductor is directly proportional to the current through it." | **0.859** |
| "Ohm's law states that current is inversely proportional to voltage." | **0.539** |

The second is the `ohms_law_inverse_confusion` misconception, scored against the
very section that refutes it.

## Acceptance results

`tests/test_phase1.py`, **13 passed**. Ten known-answer questions each retrieve
the section that actually contains the answer, plus tree-structure and
citation-integrity checks.

| Question | Expected | Found |
|---|---|---|
| SI unit of electric current | 11.1 | yes |
| Electric potential difference, volt | 11.2 | yes |
| Circuit diagram symbols | 11.3 | yes |
| State Ohm's law | 11.4 | yes |
| Factors resistance depends on | 11.5 | yes |
| Equivalent resistance of a system | 11.6 | yes |
| Resistors in series formula | 11.6.1 | yes |
| Resistors in parallel | 11.6.2 | yes |
| Heating effect, Joule's law | 11.7 | yes |
| Electric power, watt | 11.8 | yes |

Zero fabricated page references: every citation page lies inside the document's
real 24-page range.

## Known limitations

- Bare two-word queries rank poorly. Mitigated by section scoping, which is the
  path the planner uses.
- The drop cap on a chapter's first paragraph is extracted as a separate glyph,
  so the first body word reads "lectricity". Cosmetic, one occurrence per chapter.
- No OCR fallback for scanned pages (cut item 2). Both seed documents have an
  extractable text layer.
