# APIs, models and libraries

Full disclosure, as the brief requires. **No paid services are used.**

## Third-party APIs

| Service | Use | Tier | Key required |
|---|---|---|---|
| Google AI Studio (Gemini 2.5 Flash) | lesson planning | free, ~1500 req/day | yes |
| Groq (`openai/gpt-oss-120b`) | intake, grading fallback | free | yes |
| Microsoft Edge TTS (`edge-tts`) | speech synthesis | free | **no** |
| Ollama (local) | offline mode | free, local | no |

## Python libraries

| Library | Licence | Use |
|---|---|---|
| FastAPI, Pydantic, uvicorn | MIT | API and schemas |
| PyMuPDF | AGPL-3.0 | PDF parse with font metrics |
| python-docx, python-pptx | MIT | Office parsing |
| sentence-transformers | Apache-2.0 | embeddings |
| rank_bm25 | Apache-2.0 | sparse retrieval |
| numpy | BSD-3-Clause | dense index |
| edge-tts | GPL-3.0 | speech and word timings |
| langdetect | Apache-2.0 | source language detection |
| Playwright | Apache-2.0 | slide recording |
| pytest | MIT | tests |

## Frontend

Next.js 16, React 19, framer-motion (all MIT). KaTeX and Mermaid (MIT) are loaded
from cdnjs. Fonts: Inter and Instrument Serif via `next/font/google` (OFL).

## Tools

ffmpeg (LGPL-2.1) for muxing and concatenation.

## Content

NCERT Class 10 Science, Chapter 11 (Electricity) and Chapter 12, English and
Hindi, from [ncert.nic.in](https://ncert.nic.in/textbook.php). Used as seed
material for demonstration.

## Avatar

The avatar is **original work**: inline SVG authored for this project. No
third-party avatar asset is used. A candidate 3D model with real ARKit morph
targets was downloaded and then **deleted unused** because it is a scan of a real
person's face. It is not in this repository.
