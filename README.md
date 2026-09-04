# AI Teacher

An AI educator that reads your textbook, plans a lesson for your level, language
and available time, teaches it as a video with an avatar and subject-appropriate
visuals, stops to question you, and changes what it teaches next based on how you
answer.

Bharat Academix AI Innovation Hackathon 2026, Round 2. Team **Code Gauntlet**.

## The differentiator

Most submissions wrap an LLM in a video. This one carries an explicit, inspectable
**learner model**: a concept graph, Bayesian mastery estimates per concept, and
tagged misconceptions, all visible on screen and visibly steering the lesson.

When you answer a checkpoint wrongly, the system does not say "incorrect". It
names the misconception from a taxonomy, drops the mastery estimate for that
concept, regenerates the next beats with a **different analogy family**, and asks
a fresh diagnostic question. That behaviour is asserted in
`tests/test_adaptation.py`, and the misconception match is deterministic, so the
test never depends on a network call.

## Status

Phase 0 complete. See [PROGRESS.md](PROGRESS.md) for the live build log.

## Architecture

```
Next.js 16 (App Router)
  REST for upload and setup, polling for lesson progress
        |
FastAPI (Python 3.12)
  ingest    parse -> structure tree -> chunk -> embed (bge-m3) -> numpy + BM25
  plan      ONE Gemini call -> full LessonPlan (beats, visuals, questions, citations)
  speech    edge-tts -> audio + word timings
  visual    Visual Director guardrails -> VisualSpec -> HTML slide + timeline JSON
  tutor     checkpoint -> grade -> classify misconception -> regenerate next beats
  learner   BKT mastery, misconception counts, SM-2 revision, next topic
  studio    Playwright page recording + ffmpeg -> lesson.mp4
        |
SQLite + numpy index + ./storage
```

## Request budget

The free Gemini tier allows roughly 1,000 to 1,500 requests per day, shared
between development, testing and the demo. Three things keep us inside it:

1. **One call per lesson.** The entire lesson plan, every beat script, visual
   spec and checkpoint question, arrives in a single structured response.
2. **Disk cache** keyed by SHA256 of (prompt, model, params). A repeated call
   costs zero requests, and the saving is counted and displayed.
3. **Tiered routing.** Gemini handles the big structured generations. Groq
   handles grading and re-explanation. A local Ollama model is the fallback and
   powers `--offline` mode for development.

Every call is logged with model, purpose, latency and token estimate. `GET /budget`
returns the running daily count, which the UI trace panel displays.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # add GEMINI_API_KEY and GROQ_API_KEY
uvicorn services.api.main:app --reload
```

```bash
cd apps/web && npm run dev
```

Development without burning quota:

```bash
AI_TEACHER_OFFLINE=1 uvicorn services.api.main:app --reload
```

## Seed material

`data/seed/` holds NCERT Class 10 Science, used for the grounded demo and the
cross-lingual test:

| File | Content | Language |
|---|---|---|
| `jesc111.pdf` | Chapter 11, Electricity | English |
| `jesc112.pdf` | Chapter 12, Magnetic Effects of Electric Current | English |
| `jhsc111.pdf` | Chapter 11, विद्युत | Hindi |
| `jhsc112.pdf` | Chapter 12, विद्युत धारा के चुम्बकीय प्रभाव | Hindi |

Source: [ncert.nic.in](https://ncert.nic.in/textbook.php). Note that in the
current rationalised edition Electricity is **Chapter 11**, not Chapter 12.

## Tests

```bash
python -m pytest -v
```

## Licence and disclosure

Third-party APIs, models and libraries with their licences and free-tier limits
are disclosed in `docs/APIS.md`, as the brief requires.
