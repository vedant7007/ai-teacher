# Models

| Purpose | Model | Where | Cost |
|---|---|---|---|
| Lesson planning | `gemini-2.5-flash` | Google AI Studio | free tier, **1 request per lesson** |
| Intake parsing | `openai/gpt-oss-120b` | Groq | free tier |
| Grading fallback | `openai/gpt-oss-120b` | Groq | free tier, only on taxonomy miss |
| Offline / fallback | `llama3.1:8b-instruct-q4_K_M` | Ollama, local | free |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` | local | free |
| Speech | `edge-tts` neural voices | Microsoft Edge | free, no key |

## Routing

`services/llm/router.py` picks a chain by purpose:

- `plan`, `report` -> Gemini, then Groq, then Ollama
- `intake`, `grade`, `reexplain` -> Groq, then Gemini, then Ollama
- `AI_TEACHER_OFFLINE=1` -> Ollama only

Every call passes through a SHA256 disk cache and a budget accountant that
records model, purpose, latency, tokens and whether the call was billed. A
silently-failing cheap tier is visible as a `failed` count rather than quietly
escalating to Gemini, which is a mistake we made and fixed.

## Model selection notes

Groq decommissioned the Llama 3.x models mid-build. We benchmarked the
replacements on the actual Ohm's law grading task; all three graded it correctly,
and `openai/gpt-oss-120b` was chosen for reasoning quality at 1.5 s.
