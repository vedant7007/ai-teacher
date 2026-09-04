"""Phase 1 acceptance test.

Ten known-answer questions against the real NCERT Electricity chapter. Each must
retrieve the section that actually contains the answer, and no citation may
point at a page that does not exist in the document.
"""

from __future__ import annotations

import pytest

from services.ingest.pipeline import ingest
from services.rag.retrieve import retrieve

SEED = "data/seed/jesc111.pdf"
TITLE = "NCERT Class 10 Science Ch 11: Electricity"

# question -> substring that must appear in the section title of some top-8 hit
QUESTIONS = [
    ("What is the SI unit of electric current?",                 "11.1"),
    ("What is electric potential difference and its unit volt?", "11.2"),
    ("How is a circuit diagram drawn with symbols?",             "11.3"),
    ("State Ohm's law relating potential difference and current", "11.4"),
    ("On what factors does the resistance of a conductor depend?", "11.5"),
    ("What is the equivalent resistance of a system of resistors?", "11.6"),
    ("What is the formula for resistors connected in series?",   "11.6.1"),
    ("How do you calculate resistors connected in parallel?",    "11.6.2"),
    ("Explain the heating effect of electric current, Joule's law", "11.7"),
    ("What is electric power and its unit watt?",                "11.8"),
]


@pytest.fixture(scope="module")
def idx():
    return ingest(SEED, TITLE, force=True)


def test_tree_has_real_chapters(idx):
    titles = []

    def walk(n):
        titles.append(n["title"])
        for c in n["children"]:
            walk(c)

    walk(idx.tree)
    for expected in ["11.1", "11.4", "11.6.1", "11.6.2", "11.8"]:
        assert any(t.startswith(expected) for t in titles), f"missing section {expected}"


def test_chunks_are_well_formed(idx):
    pages = idx.meta["pages"]
    for c in idx.chunks:
        assert 1 <= c.page_start <= c.page_end <= pages, f"bad page span in {c.id}"
        assert len(c.text) // 4 >= 15, f"stub chunk {c.id}"
        assert c.section, f"chunk {c.id} has no section"


@pytest.mark.parametrize("question,expected_section", QUESTIONS)
def test_retrieval_finds_right_section(idx, question, expected_section):
    hits = retrieve(idx, question)
    assert hits, "no hits"
    sections = [h.chunk.section for h in hits]
    assert any(expected_section in s for s in sections), (
        f"{question!r}\n  expected a hit in section {expected_section}\n"
        f"  got: {sections}"
    )


def test_no_fabricated_pages(idx):
    pages = idx.meta["pages"]
    for question, _ in QUESTIONS:
        for h in retrieve(idx, question):
            cite = h.citation()
            assert 1 <= cite["page_start"] <= pages
            assert 1 <= cite["page_end"] <= pages
