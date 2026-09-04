# PROGRESS

Clock: **deadline not yet supplied**. Tracking elapsed session time until a date
and time is given, then this converts to T-minus.

Session start: 2026-09-04 18:05 IST.

## Locked decisions (deviations from CLAUDE.md, approved)

| # | Decision | Reason |
|---|---|---|
| 1 | numpy matrix instead of sqlite-vec | install risk on Windows, no benefit at 2k chunks |
| 3 | No WebSocket, POST plus status line | one-call generation makes beat streaming moot |
| 4 | Wav2Lip pre-cut | dead checkpoints, torch version hell, avatar already satisfies the requirement |
| 5 | Deployment optional | PDF says "application **or** deployed demonstration" |
| 6 | Keep DOCX and PPTX | cheaper than documenting their absence |
| 8 | Docs hand-written, not generated | 18 LLM calls produce text that does not match the code |
| A | Deterministic misconception matching first, LLM only on no-match | the 20-mark test must not depend on a network call |
| B | Playwright `record_video_dir` is the only video artefact path, built in Phase 4 | captures three.js canvas and DOM slides in one pass, no canvas merging |
| C | Grading on Groq, Ollama as fallback and `--offline` | never put an 8B model on the live critical path |
| D | Five visual kinds: equation, diagram, code, bullets, graph | PDF section 10 names graphs explicitly |
| E | Wrong answer regenerates the next 2 beats | makes the adaptation claim literally true |

## Phases

### Phase 0 Skeleton
- [x] Repo structure created
- [x] LLM disk cache keyed by SHA256 of (prompt, model, params)
- [x] Request accountant with per-provider daily counts and 60 percent warning
- [x] Tiered router: Gemini for plan/report, Groq for grade/reexplain/intake, Ollama fallback and offline
- [x] FastAPI `/health` and `/budget`
- [x] Next.js shell scaffolded (Next 16.3.4, React 19.2.8)
- [x] Seed docs fetched: NCERT Electricity EN + HI, Magnetic Effects EN + HI
- [x] `.env.example`, `requirements.txt`, `.gitignore`, `pytest.ini`
- [x] **Acceptance: `/health` ok, repeat LLM call costs 0 requests** (2 passed, 57.74s)
- [ ] Dockerfile build verified (deferred to Phase 7, Docker daemon not running, deployment is optional)
- [x] Pushed to GitHub: github.com/vedant7007/ai-teacher (**private, Vedant to flip to public**)

### Phase 1 Ingest and RAG
- [x] PyMuPDF parse with page, font size, font name, geometry
- [x] Overprint reconstruction (greedy y-band span cover) for fake-bold headings
- [x] Heading detection by font-size clustering, numbering only refines depth
- [x] Chapter/section/paragraph tree, persisted, matches the printed book
- [x] Structure-aware chunking, 300 to 500 tokens, 15 percent overlap, equation-safe
- [x] Chunks attributed to nearest numbered section, not leaf heading
- [x] MiniLM-multilingual embeddings, numpy matrix on disk, swappable via EMBED_MODEL
- [x] BM25 over the same chunks, RRF fusion, top 8, section scoping
- [x] Cross-lingual retrieval (query + translation union)
- [x] Local groundedness scoring, 0 API requests
- [x] `GET /docs`, `POST /docs`, `GET /docs/{id}/tree`, `GET /docs/{id}/search`
- [x] **Acceptance: 13 passed, 10/10 questions cited to the right section, zero fabricated pages**
- [x] Hindi source indexed (34 chunks, lang=hi, Devanagari sections clean)
- [x] `docs/RAG.md` written

### Phase 2 Lesson generation
- [ ] Pydantic contracts from CLAUDE.md section 7
- [ ] `intake.md` prompt, natural sentence to LearnerProfile
- [ ] `lesson.md` prompt, one call to full LessonPlan
- [ ] Word-budget allocation to hit the time target
- [ ] Validation failure policy: one repair call, then deterministic default
- [ ] Acceptance: "beginner, chapter, 20 min, Hindi" lands within 10 percent, Devanagari, all explain-beats cited

### Phase 3 Speech and slides
- [ ] edge-tts with WordBoundary timings
- [ ] HTML slide renderer, 5 visual kinds
- [ ] Visual Director guardrails with a stated reason per choice
- [ ] Acceptance: each subject picks the right visual kind, timings align within 150 ms

### Phase 4 Stage and video artefact
- [ ] Three.js avatar with viseme morph targets
- [ ] Slide build-up keyed to word timings, synced captions
- [ ] **Playwright `record_video_dir` render plus ffmpeg audio mux**
- [ ] Acceptance: a full lesson plays in the browser and produces `lesson.mp4`

### Phase 5 Adaptation
- [ ] `misconceptions.yaml`, 30+ entries with trigger_patterns
- [ ] Deterministic matcher, LLM grader on no-match
- [ ] BKT mastery, SM-2 revision
- [ ] Regenerate next 2 beats on a wrong answer
- [ ] Final quiz and learning report
- [ ] Acceptance: `tests/test_adaptation.py`, all five assertions

### Phase 6 Multilingual
- [ ] voices.yaml, cross-lingual retrieval, mid-lesson switch
- [ ] Acceptance: switch at beat 3, beats 4+ Devanagari, mastery preserved

### Phase 7 Dashboard (deploy only if on schedule)
- [ ] Dashboard, report, revision schedule, learning path

### Phase 8 Demo video
### Phase 9 Docs
### Phase 10 Submit

## Cut list, revised

0. Deployment (HF Spaces + Vercel), the PDF does not require it
1. Reranker, use RRF top 8 raw and cosine for grounding
2. OCR fallback
3. Languages beyond English, Hindi, Hinglish
4. ~~Wav2Lip~~ already cut
5. Flashcards and notes export
6. Learning path graph visual
7. PDF report download
8. ~~DOCX/PPTX~~ keeping, they are cheap
9. Voice input

Never cut: RAG citations, one-call generation, checkpoints and grading,
misconception naming, BKT mastery, re-explanation with a new analogy, the
final report, Hindi, the avatar, the trace panel, the video artefact.
