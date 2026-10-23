# ─────────────────────────────────────────────────────────────────────
# Agentic RAG Backend — Dockerfile
# Single image used by both the FastAPI API and the Taskiq worker.
# Different entrypoints are selected via docker-compose `command:`.
# ─────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/opt/models \
    TRANSFORMERS_CACHE=/opt/models

# System deps required by pypdf, python-docx, torch CPU, build wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
        libpq-dev \
        libxml2 \
        libxslt1.1 \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy source
COPY . .

# Default to running the API. Override in compose for worker.
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]