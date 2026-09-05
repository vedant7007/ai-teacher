# Features

## Mandatory requirements

| # | Requirement | Implementation |
|---|---|---|
| 1 | Learn from uploaded material | `services/ingest/`, PDF/DOCX/PPTX/TXT |
| 2 | Topic-based teaching | `plan_lesson(topic=...)` with no document |
| 3 | AI-generated lesson structure | one Gemini call to a full `LessonPlan` |
| 4 | Personalized teaching | `LearnerProfile`: level, language, time, depth, style |
| 5 | Human-like teaching interaction | checkpoints, grading, re-explanation |
| 6 | Video-based presentation | Playwright + ffmpeg, `storage/studio_en/lesson.mp4` |
| 7 | AI voice | edge-tts with word-level timings |
| 8 | Human-like avatar | stylised 2D teacher, text-derived visemes |
| 9 | Multilingual | English, Hindi, Hinglish end to end |
| 10 | Questioning and assessment | check beats plus a final quiz |
| 11 | Adaptive response | BKT, misconception taxonomy, re-explanation |
| 12 | Working prototype | live demo plus local backend |

## Advanced features implemented

- **Offline/local models** — `AI_TEACHER_OFFLINE=1` routes everything to Ollama
- **Spaced repetition** — SM-2 scheduling per concept
- **Concept maps** — Mermaid diagrams chosen by the Visual Director
- **Coding demonstration** — `code` visual with real expected output
- **Learning analytics** — the trace panel exposes model, latency, request
  budget, groundedness and the reason for each visual choice
- **Automatic study planner** — revision dates and a recommended next topic
