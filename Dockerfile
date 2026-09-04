# Backend image for Hugging Face Spaces (free CPU tier, port 7860).
# Deployment is optional per the brief, this exists so it is a 10 minute job
# rather than a 2 hour job if we choose to deploy.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/app/.hf \
    SENTENCE_TRANSFORMERS_HOME=/app/.hf

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# CPU-only torch, the CUDA wheels are 2GB+ and useless on a free CPU Space.
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY services/ ./services/
COPY data/ ./data/

EXPOSE 7860
CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
