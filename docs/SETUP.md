# Setup

## Requirements

Python 3.12, Node 22, ffmpeg on PATH. A GPU is not required.

## Backend

```bash
pip install -r requirements.txt
cp .env.example .env        # then put your real keys in .env, never in .env.example
uvicorn services.api.main:app --reload
```

`GET /health` reports which providers are usable. Swagger is at `/swagger`.

## Frontend

```bash
cd apps/web && npm install && npm run dev
```

## Git hooks (do this once per clone)

The repo ships a pre-commit hook that blocks any commit containing an API key.
Git does not enable a custom hooks directory automatically, so on a fresh clone run:

```bash
git config core.hooksPath .githooks
```

## Developing without spending quota

```bash
AI_TEACHER_OFFLINE=1 uvicorn services.api.main:app --reload
```

Routes every LLM call to a local Ollama model. Responses are also cached to
`.cache/llm/` by SHA256 of (prompt, model, params), so repeating any call costs
zero API requests.

## Tests

```bash
python -m pytest -v
```
