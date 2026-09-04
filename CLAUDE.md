# MASTER BUILD PROMPT: "AI Teacher" (Bharat Academix AI Innovation Hackathon 2026, Round 2)

> **How to use this file**
> 1. Create the repo folder, save this file as `CLAUDE.md` at the repo root. Claude Code loads it automatically every session.
> 2. First message to Claude Code: *"Read CLAUDE.md fully. Restate the plan and your assumptions in 10 lines, then execute Phase 0 and Phase 1. Do not skip acceptance tests."*
> 3. Every later session: *"Read CLAUDE.md and PROGRESS.md. Continue from the first unchecked item. Report the clock first."*

---

## 0. THE SITUATION (THESE ARE FACTS, PLAN AROUND THEM)

- **Solo developer.** One person, Vedant, team name **Code Gauntlet**. No parallel help.
- **Under 24 hours** of wall clock until the submission form closes.
- **One Gemini API key.** Free tier is Flash-only (Pro moved behind billing in 2026), roughly 10 to 15 requests per minute and 1,000 to 1,500 per day, 250k tokens/min, 1M context. **Request count is the binding constraint of this entire project, not tokens.** See Section 3.
- **RTX 3060 6GB local**, available for rendering while the demo video is recorded, but **not guaranteed to be online afterwards**.
- **Submission is a Google Form**, not a live judged session. Required: public repo link plus demo video link (YouTube or Loom). Optional: live demo link.

**What that means architecturally, and this is the most important design decision in this file:**

> The judges experience the project through a **recorded video** and a **public repo**. The heavy GPU path (lip sync, high-quality render) only has to work **once, locally, while recording**. The deployed live demo has to work **forever on free CPU hosting**.
>
> So build **two rendering paths from day one**:
> - **Path A "Studio"**: local, GPU, Wav2Lip lip sync, full MP4 render. Used to record the demo video. Never needs to be deployed.
> - **Path B "Live"**: browser 3D avatar with viseme lip sync driven by TTS word timings, zero GPU, zero server render. This is what gets deployed and what the optional live demo link points at.
>
> Path B is also the safety net: if Wav2Lip fights you, Path B alone still satisfies every mandatory requirement including "human-like AI avatar" and "video-based presentation", because the browser avatar session is captured to MP4 with `MediaRecorder` plus canvas capture.

---

## 1. OPERATING RULES FOR YOU (CLAUDE CODE)

1. **Time is the scarcest resource. Ship over polish.** Never refactor working code for elegance. Never add a dependency that needs more than 5 minutes to install.
2. **Announce the clock at the top of every response**: `T-19:30 | Phase 3 | on track / 40 min behind`. If behind, immediately propose which item from the CUT LIST (Section 15) to drop.
3. **No stubs in any path the video shows.** Anything unfinished goes behind an OFF feature flag and into `docs/KNOWN_LIMITATIONS.md`.
4. **Every phase ends with its acceptance test actually run.** Paste real output, then tick `PROGRESS.md`. Never tick an unverified box.
5. **Zero paid services.** If you think something paid is unavoidable, stop and ask.
6. **Hard timeboxes are hard.** When a timebox expires, take the fallback and move on. Wav2Lip gets 75 minutes, no more.
7. **Docs style: never use em dashes.** Commas, colons, or new sentences.
8. Commit after every green acceptance test: `feat(scope): what changed`. Push to a public repo from Phase 0 so the form can be filled at any moment.
9. **Every LLM call goes through the router and is counted.** Never call Gemini directly from feature code.

---

## 2. WHAT WE ARE BUILDING

An **AI Teacher**: it ingests a textbook, PDF, DOCX, PPTX or notes, **or** a bare topic, builds a lesson plan tuned to the learner's level, language and available time, then **teaches it as a video with a human-like avatar, natural voice and subject-appropriate visuals**, **stops to question the student**, **grades answers, names the misconception, re-explains differently, changes difficulty**, and ends with an assessment, a learning report and a recommendation of what to study next.

The brief explicitly rejects three things: a Q and A chatbot, a static video, and a talking head reading a script over plain text. Check every decision against that sentence.

**Our differentiator (say this in the README and the video):** an explicit, inspectable **learner model**, a concept graph plus Bayesian mastery estimates plus tagged misconceptions, visible on screen and visibly steering the lesson. Most submissions will wrap an LLM in a video. We show pedagogy as state.

---

## 3. THE 1,500-REQUEST BUDGET (READ TWICE, THIS KILLS PROJECTS)

One free Gemini key gives roughly 10 to 15 RPM and 1,000 to 1,500 requests per day, shared between development, testing and the demo. A naive per-beat design burns 40 requests per lesson and dies by lunchtime.

**Mandatory design rules:**

1. **One call generates the entire lesson.** Send the retrieved chunks plus the learner profile once, get back the full `LessonPlan` with every beat script, visual spec and checkpoint question in a single structured JSON response. 1M context makes this easy. Budget: **1 request per lesson**, not 20.
2. **Disk cache keyed by SHA256 of (prompt, model, params)** in `.cache/llm/`. Committed to `.gitignore` but persistent across runs. A repeated test costs 0 requests. Build this in Phase 0, before anything else touches the LLM.
3. **Tiered routing.** Cheap, frequent calls (answer grading, one-line rephrasing, language switching of a single beat) go to **Groq free tier** first, then OpenRouter free models, and only fall back to Gemini. Gemini is reserved for the big structured generations.
4. **Request accountant**: `services/llm/budget.py` logs every call with model, purpose, tokens and a running daily count, and prints a warning at 60 percent of budget. Show the counter in the trace panel, it is a genuinely good look for the "AI/ML implementation" score.
5. **Offline mode**: `--offline` flag routes everything to **Ollama with Qwen 2.5 7B Instruct Q4** on the 3060. Use this for all repetitive development testing so the quota survives until the demo recording. This also ticks the "offline/local AI models" advanced feature in the brief.
6. **Freeze the demo.** Once the demo lesson generates well, save its full JSON to `data/demo/` and add a `DEMO_MODE=1` env var that replays it. The live deployed link uses this by default so it can never rate-limit in front of a judge, with the live path available behind a toggle. Document this honestly in `docs/KNOWN_LIMITATIONS.md`, it reads as engineering maturity, not cheating.

---

## 4. LOCKED STACK (SOLO, 24 HOURS, DO NOT SUBSTITUTE)

**Frontend:** Next.js 15 App Router, TypeScript, Tailwind, shadcn/ui, Zustand. Deploy on Vercel free.

**Backend:** Python 3.11, FastAPI, Pydantic v2 for every LLM output. No Celery, no Redis, no queue. Long jobs use `BackgroundTasks` plus a `jobs` table and a WebSocket for progress.

**Storage:** **SQLite** plus `sqlite-vec` (or FAISS flat index on disk) plus local `./storage` for media. No Supabase, no Postgres, no Docker database. A single-file DB is the right call for solo plus 24 hours, and it deploys to Hugging Face Spaces without configuration. Files served by FastAPI `StaticFiles`.

**Deployment (Path B only):** backend on **Hugging Face Spaces (Docker, free CPU)**, frontend on **Vercel free**. The Space ships with the pre-built demo index and `DEMO_MODE` available. Do this in Phase 7, not earlier, but verify the Dockerfile builds in Phase 0.

**LLM:** Gemini Flash via AI Studio key (primary, structured generation), Groq free (fast small calls), OpenRouter free (overflow), Ollama Qwen 2.5 7B (offline dev and demo insurance). Router in `services/llm/router.py`.

**Embeddings:** `BAAI/bge-m3` locally via `sentence-transformers`. Multilingual, handles Devanagari and code-mixed Hinglish, runs on the 3060 and acceptably on CPU. **Use local embeddings, not the API**, so indexing costs zero requests. Sparse: `rank_bm25`. Fusion: Reciprocal Rank Fusion. Rerank top 30 to top 8 with `bge-reranker-v2-m3` if it loads in time, otherwise skip reranking and note it.

**Document parsing:** `PyMuPDF` for text, layout blocks, font sizes and embedded images. `python-docx`, `python-pptx`. `pytesseract` plus `pdf2image` only as an OCR fallback for pages with under 40 characters of extractable text. `langdetect` for source language.

**TTS:** **`edge-tts`** as primary. Free, no API key, neural voices in Hindi, Telugu, Tamil, Marathi, Bengali, English and 40 plus languages. Critically it emits **WordBoundary events**, giving word-level timings for free. Those timings drive captions, slide build-up animation and avatar visemes. Fallbacks: Sarvam AI free tier (60 RPM, better Indic prosody, use it for the demo if the key works), then `gTTS`.

**STT (student speaks):** browser **Web Speech API** first (zero latency, zero install), `faster-whisper small int8` locally as the fallback, typed answer box always available.

**Avatar:**
- Path B (default, deployed): **Ready Player Me** GLB avatar in `three.js` via `@react-three/fiber`, Oculus viseme morph targets driven by a phoneme timeline derived from the edge-tts word timings. Blinks, idle head sway, and a "looks at the slide" turn on demo beats.
- Path A (local, for the recorded video only): **Wav2Lip** over a pre-rendered idle loop of the same avatar, on the 3060. **Timebox: 75 minutes.** If checkpoints, torch versions or face detection fight you, abandon it and record Path B. Do not sink two hours here.
- The avatar must be licence-safe: a Ready Player Me avatar or one you generate. Never a real person's face. Record this in `docs/APIS.md`.

**Visuals (this is where marks are won, and where time gets wasted):**
- **Do not install Manim.** The LaTeX toolchain plus render time will eat two hours you do not have.
- Build one **HTML slide renderer** with a shared design system, animated by a timeline JSON that is keyed to word timings. It runs in the browser for Path B and is screenshotted by **Playwright** for Path A. One renderer, two consumers.
- Visual kinds: `equation` (KaTeX with term-by-term highlight as it is spoken), `graph` (Plotly or a simple SVG plotter, animated draw-in), `diagram` and `concept_map` and `flow` (Mermaid), `code` (Shiki plus a typed-out execution trace, real output where the snippet is safe Python), `timeline` and `map` (SVG components), `labelled_image` (SVG callouts positioned by the LLM), `table`, `bullets` (build-up, never a wall of text).
- Images: **Wikimedia Commons and Openverse APIs only**, permissive licences, attribution stored per asset. Never scrape.

**Video assembly (Path A):** Playwright screenshots per animation keyframe plus `ffmpeg` to build each beat clip, avatar composited as a masked picture-in-picture at 22 percent width bottom right, concat with 250 ms crossfades, captions as separate `.vtt` per language, `chapters.json` for per-concept seeking.

**Video capture (Path B):** `MediaRecorder` over a canvas capture stream of the lesson stage, producing a downloadable `.webm` then `ffmpeg` to mp4. This means the deployed app genuinely generates a teaching video too, which satisfies the mandatory requirement without a GPU.

---

## 5. ARCHITECTURE

```
Next.js (Vercel)
  REST for upload and setup, WebSocket for lesson progress and live tutoring
        |
FastAPI (HF Spaces free CPU, or local for Studio path)
  ingest    parse -> structure tree -> chunk -> embed (bge-m3) -> sqlite-vec + BM25
  plan      ONE Gemini call -> full LessonPlan (beats, visuals, questions, citations)
  speech    edge-tts -> audio + word timings
  visual    Visual Director guardrails -> VisualSpec -> HTML slide + timeline JSON
  tutor     WebSocket loop: checkpoint -> grade -> classify misconception -> adapt
  learner   BKT mastery, misconception counts, SM-2 revision, next topic
  studio    (local only) Playwright + Wav2Lip + ffmpeg -> lesson.mp4
        |
SQLite + sqlite-vec + ./storage
```

**Streaming rule:** `POST /lessons` returns `lesson_id` immediately and pushes `plan_ready`, `beat_1_ready`, `beat_2_ready` over WebSocket. The student starts watching beat 1 while beat 4 is still preparing. **Never render past a checkpoint before it is answered.** Say that out loud in the demo video, it proves the adaptation is real rather than pre-scripted.

---

## 6. REPO STRUCTURE

```
ai-teacher/
  CLAUDE.md  PROGRESS.md  README.md  .env.example  Dockerfile  Makefile
  apps/web/                      Next.js 15
    app/learn/page.tsx           intake: upload or topic + natural language instruction
    app/lesson/[id]/page.tsx     stage: slide + avatar + captions + questions + trace
    app/dashboard/page.tsx       learner model, report, revision plan, learning path
    components/{Stage,AvatarLive,SlideRenderer,QuestionCard,MasteryPanel,TracePanel,LangSwitch,SourceChip}
  services/
    api/main.py
    llm/{router.py,budget.py,cache.py,schemas.py,repair.py,prompts/*.md}
    ingest/{parse.py,structure.py,chunk.py,embed.py,index.py}
    rag/{retrieve.py,ground.py}
    pedagogy/{planner.py,grader.py,misconceptions.yaml,bkt.py,path.py,orchestrator.py}
    visual/{director.py,slide_spec.py}
    speech/{tts.py,timings.py,voices.yaml}
    studio/{screenshot.py,wav2lip.py,assemble.py}     local only
  data/seed/                     3 demo documents + expected outputs
  data/demo/                     frozen demo lesson JSON for DEMO_MODE
  tests/  docs/
```

---

## 7. DATA CONTRACTS (PYDANTIC, VALIDATED ON EVERY LLM OUTPUT)

```python
class LearnerProfile(BaseModel):
    level: Literal["beginner","intermediate","advanced"]
    prior_knowledge: list[str] = []
    goal: str | None                 # exam, interview, curiosity, revision
    language: str                    # "en-IN", "hi-IN", "hinglish", "te-IN", ...
    style: Literal["examples-first","theory-first","socratic","visual"] = "examples-first"
    time_budget_minutes: int         # 5, 20, 60, or 7*24*60 for a study plan
    depth: Literal["overview","standard","deep"] = "standard"

class Concept(BaseModel):
    id: str; name: str
    prerequisites: list[str]
    source_refs: list[SourceRef]     # doc_id, chapter, page, char_span
    difficulty: float                # 0..1
    est_minutes: float

class Beat(BaseModel):               # one teaching moment, 20 to 60 seconds
    id: str; concept_id: str
    intent: Literal["hook","explain","example","analogy","demo","check","recap","transition"]
    script: str                      # target language, spoken register
    visual: VisualSpec
    citations: list[SourceRef]       # required unless intent in {hook, transition}
    checkpoint: Question | None

class VisualSpec(BaseModel):
    kind: Literal["equation","graph","diagram","concept_map","flow","code","timeline",
                  "map","labelled_image","table","bullets"]
    reason: str                      # WHY this visual, shown in the UI
    subject: str
    payload: dict                    # renderer specific
    timeline: list[TimelineCue]      # element id + word index it appears on

class Question(BaseModel):
    id: str; concept_id: str
    type: Literal["mcq","short","numeric","explain_own_words","apply"]
    prompt: str; options: list[str] | None; answer_key: str
    rubric: list[str]
    targets_misconception: str | None

class GradedAnswer(BaseModel):
    correct: bool; confidence: float
    misconception_id: str | None
    feedback: str
    recommended_action: Literal["continue","reexplain_analogy","reexplain_simpler",
                                "worked_example","step_back_prereq","drill","level_up"]

class LearnerState(BaseModel):
    mastery: dict[str, float]        # concept_id -> p(known)
    misconceptions: dict[str, int]
    next_review: dict[str, str]      # SM-2
    history: list[Interaction]
```

Validation failure policy: one automatic repair call including the validator error, then a deterministic default. Log all three outcomes and surface the repair rate in the trace panel.

---

## 8. THE FIVE PROMPTS (in `services/llm/prompts/`, quotable in the docs)

Solo plus 24 hours means five prompts, not seven agents.

1. **`intake.md`** cheap model. Parses the student's natural sentence into `LearnerProfile`. Must handle the brief's own example: *"I am a beginner. Teach me Chapter 4 in 20 minutes. Explain it in Hindi using simple examples. Ask me questions during the lesson and test me at the end."*
2. **`lesson.md`** the big one, Gemini, one call. Input: document structure tree plus retrieved chunks (or nothing, for topic-only mode) plus `LearnerProfile` plus the allowed-visuals table. Output: complete `LessonPlan`. Rules baked in: speak to one student using "you", one idea per beat, a concrete example at least every third beat, never read the slide verbatim, end explain-beats with a bridge sentence, allocate spoken words to hit the time budget (150 words per minute English, 130 Hindi, 120 Telugu and Tamil), place a `check` beat after every concept, and cite for every factual claim.
3. **`grader.md`** cheap model, Groq first. Grades a free-text answer against the rubric, classifies into the misconception taxonomy, picks `recommended_action`. **Forbidden from ever just saying "incorrect".**
4. **`reexplain.md`** cheap model. Given the concept, the failed explanation and the misconception, produce a new beat using a **different analogy family** (mechanical, everyday, computational) plus a fresh diagnostic question.
5. **`report.md`** one call at the end. Score, concepts understood, weak areas, wrong concepts, recommended revision, next topic, and for multi-day requests a day-by-day plan.

Orchestration is plain Python in `services/pedagogy/orchestrator.py`. **Do not add LangChain, CrewAI or LlamaIndex.** They add install time and failure surface, and they hide the architecture we are being graded on.

---

## 9. RAG SPEC (15 marks)

1. **Parse** with PyMuPDF into blocks carrying page number and font size. Detect headings by font-size clustering, not regex. Keep embedded figures with their page and caption.
2. **Structure** into a chapter to section to paragraph tree, persisted. "Teach me Chapter 4" must resolve to the real chapter node. Support chapter naming in either language.
3. **Chunk** structure-aware, 300 to 500 tokens, 15 percent overlap, never splitting a worked example or an equation block. Store `{doc_id, chapter, section, page, char_span, lang}`.
4. **Index** bge-m3 vectors in sqlite-vec plus a BM25 index over the same chunks.
5. **Retrieve** hybrid, RRF fused, top 8. **Cross-lingual:** embed the query in both the learner language and its English translation and union the results, since the source book language and the teaching language are independent.
6. **Ground:** after generation, verify each factual sentence against its cited chunks. Do this **locally with the reranker or a cross-encoder score**, not with an API call, to protect the request budget. Sentences below threshold are re-generated once, then marked visibly as "general knowledge". Store `groundedness_score` per beat, show the lesson average in the UI.
7. **Citations:** every beat carries `SourceRef`s and the player shows a "Source" chip that opens the page image with the span highlighted. This single UI element sells the whole RAG score in the video.

*Accept:* on the seeded textbook, 10 known-answer questions score above 90 percent grounded and correct with zero fabricated page references. Numbers go in `docs/EVALUATION.md`.

---

## 10. INTERACTION AND ADAPTATION (20 marks, the highest weight, never cut this)

Explicit state machine: `Understand -> Plan -> Explain -> Demonstrate -> Question -> Evaluate -> Adapt -> Continue`. Log every transition and render the log in the trace panel.

**Mastery, Bayesian Knowledge Tracing** in `bkt.py`: per concept keep `p(known)` with `p_init=0.25, p_transit=0.15, p_slip=0.1, p_guess=0.2`. Update on every graded answer. Policy:
- wrong and `p < 0.4`: `reexplain_analogy` with a different analogy family, then a fresh diagnostic question.
- two consecutive wrong on one concept: `step_back_prereq`.
- `p > 0.85` early: `level_up`, skip that concept's remaining beats, reallocate the saved minutes to weak concepts. Call this out in the demo.

**Misconception taxonomy** in `misconceptions.yaml`: seed **at least 30 entries** across physics, math, biology, chemistry and programming, each with `id`, `trigger_patterns`, `correct_model`, `preferred_analogy`, `diagnostic_question`. Include the brief's own example, `ohms_law_inverse_confusion` (student says current rises when resistance rises at constant voltage). Unmatched answers create a `novel_misconception` record from the grader's description.

**Analogy bank:** each concept carries three analogy families. Re-explanation must switch family, never restate the first explanation in different words. Assert this in `tests/test_adaptation.py`.

**Doubts:** the learner can interrupt any time by voice or text. The answer uses lesson context plus retrieval, then one bridge sentence returns to the same beat. The lesson never restarts.

---

## 11. MULTILINGUAL (10 marks)

- Ship: English, **Hindi**, **Hinglish** (Roman-script code-mixed, first-class mode with few-shot examples in the prompt, since the brief literally quotes a Hinglish request), Telugu, Tamil, Marathi, Bengali, plus Spanish and French to show international reach. Config-driven in `speech/voices.yaml`.
- **Cross-lingual grounding:** English textbook to Hindi teaching and the reverse. Citations always point at the original-language span, with a translated caption below.
- **Mid-lesson switch:** the `LangSwitch` control regenerates only upcoming beats, preserves `LearnerState`, mastery and concept position, and the teacher acknowledges the switch in one sentence.
- *Accept:* start English, switch to Hindi at beat 3, assert beats 4 onward are Devanagari, mastery preserved, concept order unchanged. Plus one full lesson in Telugu from an English source.

---

## 12. FRONTEND (5 marks, but it is the entire visual impression of the video)

- **`/learn`** drop zone (PDF, DOCX, PPTX, TXT) or topic box, one natural-language instruction field **pre-filled with the brief's example sentence**, and parsed profile chips rendered back so the "understanding" step is visible.
- **`/lesson/[id]`** the stage: slide area, live avatar, synced captions, concept progress rail, per-concept mastery bars that move in real time, question overlay, mic and text doubt box, language switch, Source chips, and a collapsible **Agent Trace** drawer showing model used, latency, request count against the daily budget, retrieved chunks, groundedness score and the "why this visual" reason.
- **`/dashboard`** score, strong and weak concepts, misconception radar, SM-2 revision schedule, next topic, learning path graph, plus auto-generated notes and flashcards and a downloadable PDF report.
- Dark academic theme, one accent colour, skeleton loaders everywhere, and never a spinner without a status line naming the current pipeline stage. **Zero dead buttons.** If a control is not wired, remove it.

---

## 13. HOUR BY HOUR PLAN (T is submission time)

Track this in `PROGRESS.md`. Each block ends with its acceptance test run and a commit.

| Window | Phase | Deliverable | Acceptance test |
|---|---|---|---|
| T-24 to T-23 | 0 Skeleton | Repo pushed public, FastAPI health, Next shell, **LLM router plus disk cache plus budget counter**, Dockerfile builds | `/health` ok, one cached LLM call costs 0 requests on repeat |
| T-23 to T-20:30 | 1 Ingest and RAG | Parse, structure tree, chunk, bge-m3 index, hybrid retrieve, citations | Seeded PDF: `/docs/{id}/tree` shows real chapters, 10 questions cited correctly |
| T-20:30 to T-18:30 | 2 Lesson generation | One-call `LessonPlan`, intake parser, time budgeting | "beginner, chapter 4, 20 min, Hindi" gives a plan within 10 percent of 20 min, Devanagari, all explain-beats cited |
| T-18:30 to T-16 | 3 Speech and slides | edge-tts plus word timings, HTML slide renderer, Visual Director guardrails | Math, biology, history and code beats each pick the right visual kind and render; timings align within 150 ms |
| T-16 to T-13 | 4 Path B stage | Three.js avatar with visemes, synced slide build-up, captions, `MediaRecorder` capture | A full lesson plays end to end in the browser and exports an mp4 |
| T-13 to T-9 | 5 **Adaptation** | Checkpoints, grader, misconception taxonomy, BKT, re-explain, difficulty change, final quiz and report | `tests/test_adaptation.py`: wrong Ohm's law answer triggers all five assertions in Section 14 |
| T-9 to T-7:30 | 6 Multilingual | Language router, cross-lingual retrieval, mid-lesson switch | Section 11 acceptance passes |
| T-7:30 to T-6 | 7 Deploy plus dashboard | HF Space plus Vercel live, `DEMO_MODE` frozen lesson, dashboard and report | Phone on mobile data completes the full journey on the live URL |
| T-6 to T-4:30 | 8 Studio path | Wav2Lip **75 min timebox**, Playwright plus ffmpeg render | `lesson.mp4` with lip-synced avatar, or documented fallback to Path B capture |
| T-4:30 to T-2:30 | 9 Demo video | Record and edit to 5 minutes per Section 16 | Uploaded, unlisted YouTube link works in an incognito window |
| T-2:30 to T-1 | 10 Docs | All 17 docs plus README plus screenshots plus GIF | Fresh clone plus `docs/SETUP.md` runs on a clean machine |
| T-1 to T-0 | 11 Submit | Fill the Google Form, buffer | Form submitted with repo, video and live links |

**If you sleep, cut 5 hours from the T-9 to T-4:30 window and take the entire CUT LIST.**

---

## 14. THE FIVE ASSERTIONS THAT WIN THE 20-MARK CATEGORY

`tests/test_adaptation.py` must assert, on a wrong answer to the Ohm's law checkpoint:
1. the response **names the misconception** (`misconception_id == "ohms_law_inverse_confusion"`),
2. the re-explanation uses a **different analogy family** than the original beat,
3. a **new diagnostic question** targeting the same concept is issued,
4. `mastery["ohms_law"]` **decreases**,
5. the concept is **added to the revision plan** with an SM-2 due date.

This test is the project. If everything else is mediocre and this is solid, the submission still scores well.

---

## 15. CUT LIST (drop in this order when behind, never improvise)

1. Reranker model (use RRF top 8 raw).
2. OCR fallback for scanned pages.
3. Telugu, Tamil, Marathi, Bengali, Spanish, French (keep English, Hindi, Hinglish; keep the config table so the capability is visible).
4. Wav2Lip Path A entirely (record Path B, the browser avatar, which is already a real avatar).
5. Flashcards and notes export.
6. Learning path graph visual (keep the JSON and a simple list).
7. PDF report download (keep the on-screen report).
8. DOCX and PPTX ingestion (keep PDF and TXT, document the limitation).
9. Voice input (keep the typed answer box).

**Never cut:** RAG citations, the one-call lesson generation, checkpoints and grading, misconception naming, BKT mastery, re-explanation with a new analogy, the final report, Hindi, the avatar, or the trace panel.

---

## 16. DEMO VIDEO SCRIPT (5 minutes, record it exactly like this)

- **0:00 to 0:20** the problem in one sentence, then the thesis: an AI teacher with a learner model, not a chatbot.
- **0:20 to 0:50** upload the textbook, type the brief's own instruction sentence, show the parsed profile chips and the generated concept graph with prerequisites.
- **0:50 to 2:00** the teaching video plays: avatar plus voice, an equation building term by term in sync with the speech, then open a Source chip to show the exact textbook page behind the claim.
- **2:00 to 3:15 the money shot.** Answer a checkpoint wrongly on purpose. The teacher names the misconception, re-explains with a different analogy, asks a new diagnostic question, and the mastery bar visibly drops then recovers. **Say out loud that the following scenes were generated after the answer, not pre-scripted.**
- **3:15 to 3:45** switch to Hindi mid-lesson, the lesson continues from the same concept. Ask one Hinglish doubt by voice.
- **3:45 to 4:30** final quiz, learning report, weak areas, revision schedule, recommended next topic.
- **4:30 to 5:00** architecture slide, the request-budget and fallback design, and the measured numbers from `docs/EVALUATION.md`.

Record at 1080p, use a headset mic, keep the browser zoom at 110 percent so text is readable on a phone. Upload unlisted to YouTube and **verify the link in an incognito window** before pasting it into the form.

---

## 17. SUBMISSION FORM ANSWERS (prepare these in `docs/SUBMISSION.md` by T-2)

The Google Form asks for: Team Name, Team Leader name, email, phone, university, up to 5 member names and emails, **Open Source Repository Link (required)**, **Video Demo Link (required)**, Live Demo Link (optional), Additional Comments.

- Team Name: **Code Gauntlet**
- Team Leader: Vedant Manmath Idlgave, vedantidlgave16@gmail.com, Vidya Jyothi Institute of Technology (VJIT), Hyderabad
- Repository: public GitHub link, **make sure the repo is public and the README renders with the architecture diagram and GIF**
- Video Demo: unlisted YouTube link, verified in incognito
- Live Demo: the Vercel URL
- **Additional Comments (draft this, do not leave it blank):** four to six lines covering the learner-model differentiator, the measured groundedness and time-fidelity numbers, the fact that it runs entirely on free and open-source infrastructure with a local-model offline mode, and the honest note about `DEMO_MODE` caching. Judges read this box, and honesty about engineering trade-offs reads as senior.

---

## 18. DOCS TO PRODUCE (the brief lists these explicitly, one file each in `docs/`)

`PROBLEM.md`, `SOLUTION.md`, `FEATURES.md`, `ARCHITECTURE.md` (Mermaid diagram plus a sequence diagram of one adaptive loop), `MODELS.md`, `RAG.md`, `AGENTS.md` (paste the actual prompt files), `PERSONALIZATION.md`, `ASSESSMENT.md`, `MULTILINGUAL.md`, `VOICE.md`, `AVATAR_VIDEO.md`, `APIS.md` (every third-party API, model and library with licence and free-tier limits, since the brief requires disclosure), `SETUP.md`, `DEPLOYMENT.md`, `KNOWN_LIMITATIONS.md`, `EVALUATION.md` (groundedness, time fidelity, render latency, adaptation test results, request budget per lesson), `SUBMISSION.md`.

---

## 19. START NOW

1. Restate the plan in 10 lines and list every assumption that could be wrong.
2. Create `PROGRESS.md` from Section 13.
3. Execute Phase 0 including the LLM cache and budget counter, run the acceptance test, paste real output, commit and push to a public repo.
4. Execute Phase 1, run its acceptance test, paste output, commit.
5. Stop and report actual elapsed time versus the Section 13 plan so we can re-plan.

If anything here conflicts with the hackathon PDF, the PDF wins, and you flag the conflict before proceeding.
