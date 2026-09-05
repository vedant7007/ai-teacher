# Deployment

## What is deployed

The **frontend** is deployed to Vercel and runs with **no backend**. The frozen
lesson JSON, the per-beat audio and the pre-rendered slides ship in `public/`,
and the adaptive loop runs client-side from `apps/web/lib/pedagogy.ts`, a
TypeScript port of the same taxonomy and BKT arithmetic the Python tests assert
against.

That means the live demo runs the **real** adaptive loop, not a canned sequence:
the regex match, the mastery update and the analogy-family switch are all
computed in the browser from the same data.

```bash
cd apps/web
npm run build
npx vercel deploy --prod
```

If the deployment returns 302, Vercel Deployment Protection is enabled. Disable
it under Settings -> Deployment Protection, or a judge will hit an SSO wall.

## What is not deployed

The **backend** is local only. Document upload, live lesson generation and the
studio video render need Python, a desktop browser and ffmpeg.

A `Dockerfile` targeting Hugging Face Spaces is included and CPU-torch-pinned,
but **its build was never verified** because the Docker daemon was unavailable
during the build window. Treat it as untested.

## Regenerating the deployed assets

```bash
python -m pytest -q                      # confirm green first
python -c "import services.studio.render" # render the mp4 (local, ~30s/beat)
```

Slides and audio are exported into `apps/web/public/` by the export step in the
build log; they are marked `linguist-generated` in `.gitattributes`.
