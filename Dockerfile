# Hosted demo image (our VPS behind Caddy, or Hugging Face Spaces, Docker SDK, CPU).
# Cookies are SameSite=Lax. Inside a Hugging Face Space iframe set the Space variable
# PB_COOKIE_SAMESITE=none (cross-site writes are still blocked by the Origin check in app/main.py).
#   docker build -t porabondhu . && docker run -p 7860:7860 porabondhu
# The speech model is the int8 ONNX export made by backend/scripts/export_onnx.py,
# published at https://huggingface.co/safu58/porabondhu-wav2vec2-bn-onnx-int8

# ---- 1. frontend build
FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- 2. backend + models
FROM python:3.10-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1 \
    PB_CTC_BACKEND=onnx-int8 \
    PB_PRELOAD_MODELS=true \
    PB_TORCH_THREADS=2 \
    PB_COOKIE_SAMESITE=lax \
    PB_AUDIO_RETENTION_DAYS=14
WORKDIR /home/user/app

COPY --chown=user backend/requirements-deploy.txt backend/
RUN pip install --no-cache-dir --user -r backend/requirements-deploy.txt

ARG ONNX_REPO=safu58/porabondhu-wav2vec2-bn-onnx-int8
RUN python -c "from huggingface_hub import snapshot_download as d; d('${ONNX_REPO}', local_dir='backend/data/onnx', allow_patterns=['*.json', 'model.int8.onnx'])"
RUN python -c "from faster_whisper import WhisperModel as W; W('small', device='cpu', compute_type='int8')"

COPY --chown=user backend/ backend/
COPY --chown=user --from=web /web/dist frontend/dist

WORKDIR /home/user/app/backend
EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers", "--forwarded-allow-ips", "*"]
