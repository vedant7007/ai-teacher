# Submission

Everything below is ready to paste into the Google Form.

## Form fields

| Field | Value |
|---|---|
| **Team Name** | Code Gauntlet |
| **Team Leader** | Vedant Manmath Idlgave |
| **Email** | vedantidlgave16@gmail.com |
| **University** | Vidya Jyothi Institute of Technology (VJIT), Hyderabad |
| **Open Source Repository Link** (required) | https://github.com/vedant7007/ai-teacher |
| **Video Demo Link** (required) | *paste the unlisted YouTube link, verified in an incognito window* |
| **Live Demo Link** (optional) | *paste the Vercel URL* |

Repository visibility confirmed **PUBLIC** (unauthenticated API returns 200).

Fallback video artefact, if the YouTube upload is not ready:
https://github.com/vedant7007/ai-teacher/releases

## Additional Comments

> AI Teacher carries an explicit, inspectable learner model rather than wrapping
> an LLM in a video: a concept graph, Bayesian Knowledge Tracing mastery per
> concept, and a 32-entry misconception taxonomy that is matched
> deterministically before any model is called. That design choice is why our
> adaptation test suite, which asserts that a wrong Ohm's law answer names the
> misconception, re-explains with a different analogy family, issues a new
> diagnostic question, drops mastery and schedules SM-2 revision, runs fully
> offline in 1.42 seconds and cannot fail in front of a judge.
>
> Measured: 10 of 10 known-answer questions retrieve the correct textbook
> section with zero fabricated page references; time fidelity is -3.9 percent
> against a 20 minute Hindi budget and -10.4 percent in English; a complete
> 20 minute lesson costs exactly one Gemini request, and the entire build to
> date consumed 16.
>
> The stack is entirely free and open source: Gemini Flash free tier, Groq free
> tier, local sentence-transformers embeddings, edge-tts, Playwright and ffmpeg,
> with an Ollama offline mode that routes every call to a local model so the
> system runs with no internet and no API key at all.
>
> Two honest notes. The deployed demo defaults to DEMO_MODE, replaying a frozen
> lesson from data/demo so it cannot be rate-limited during judging; the live
> generation path is the same code and is exercised by the same tests. And our
> English lessons land about two minutes short of a 20 minute request because
> word-budget calibration is a single global constant rather than per-language;
> both of these, and everything else we know is imperfect, are written up in
> docs/KNOWN_LIMITATIONS.md rather than left for a judge to find.

## Measured numbers, for reference

| Metric | Value |
|---|---|
| Test suite | 68 tests passing |
| The five adaptation assertions | offline, **1.42 s**, zero API requests |
| Retrieval accuracy | **10 / 10** questions to the correct section |
| Fabricated citations | **0** |
| Misconception taxonomy | 32 entries, 82 patterns, 5 subjects, 3 languages |
| Time fidelity, Hindi | -3.9 percent (19.2 min vs 20 requested) |
| Time fidelity, English | -10.4 percent (17.9 min vs 20 requested) |
| Gemini requests per lesson | **1** |
| Gemini requests, entire build | **16** |
| Requests saved by disk cache | 16 |
| Rendered video A/V drift | 97 ms over 18.9 minutes |
| Languages shipped end to end | English, Hindi, Hinglish |

## Mandatory requirements checklist

| # | Requirement | Where |
|---|---|---|
| 1 | Learning from uploaded material | `POST /docs`, NCERT Ch 11 seeded |
| 2 | Topic-based teaching | `plan_lesson(topic=...)` with no document |
| 3 | AI-generated lesson structure | one Gemini call to a full `LessonPlan` |
| 4 | Personalized teaching | `LearnerProfile`: level, language, time, depth |
| 5 | Human-like teaching interaction | checkpoints, grading, re-explanation |
| 6 | Video-based presentation | `storage/studio_en/lesson.mp4` |
| 7 | AI voice | edge-tts with word-level timings |
| 8 | Human-like AI avatar | stylised avatar, text-derived visemes |
| 9 | Multilingual | English, Hindi, Hinglish, mid-lesson switch |
| 10 | Questioning and assessment | check beats plus final quiz |
| 11 | Adaptive response | BKT, misconception taxonomy, re-explanation |
| 12 | Working prototype | runs locally; `docs/SETUP.md` |

## Pre-submission checklist

- [x] Repository public and pushed
- [x] `docs/KNOWN_LIMITATIONS.md` honest and complete
- [ ] English video rendered, watched with sound, no error cards
- [ ] Release asset replaced with the English video
- [ ] YouTube upload, verified in an incognito window
- [ ] Vercel URL live
- [ ] README with architecture diagram and screenshots
