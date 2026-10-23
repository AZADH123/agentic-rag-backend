# Agentic RAG Backend

A modular, backend-only Agentic RAG platform built with Python, FastAPI, Gemini, BGE embeddings, PostgreSQL+pgvector, Taskiq/Redis, Amazon S3 (or MinIO), and the Model Context Protocol (MCP).

## Architecture at a Glance

```
                ┌──────────────────────────────────────────┐
                │                 Client                   │
                └──────────────────┬───────────────────────┘
                                   │ HTTP /api/v1
                ┌──────────────────▼───────────────────────┐
                │              FastAPI API                 │
                │  (health, documents, retrieval, chat)    │
                └────┬─────────┬──────────┬───────────────┘
                     │         │          │
        ┌────────────▼─┐  ┌────▼────┐  ┌──▼──────────────┐
        │  S3 / MinIO  │  │ Postgres│  │  Agent          │
        │  (source)    │  │ +pgvec  │  │  orchestrator   │
        └──────────────┘  └────┬────┘  └──┬─────────┬────┘
                               │          │         │
                               │       ┌──▼──┐  ┌──▼────────┐
                               │       │Gemini│  │ MCP client│
                               │       └──────┘  └──┬────────┘
                               │                    │ stdio
                               │            ┌───────┼───────┐
                               │         ┌───▼──┐ ┌──▼──┐ ┌───▼───┐
                               │         │ RAG  │ │calc │ │weather│
                               │         │server│ │srv  │ │ srv   │
                               │         └──┬───┘ └─────┘ └───────┘
                               │            │
                ┌──────────────┘            │
                │   ┌──────────────────────▼─────────────┐
                │   │ Taskiq worker (separate process)   │
                │   │  - parse PDF/DOCX/TXT              │
                │   │  - chunk + BGE embed               │
                │   │  - write to pgvector                │
                │   └──────────────┬─────────────────────┘
                │                  │
        ┌───────▼──────┐    ┌──────▼──────┐
        │    Redis     │    │  Postgres   │
        │  (Taskiq q)  │    │  (durable)  │
        └──────────────┘    └─────────────┘
```

## Quick Start

See **[RUN.md](RUN.md)** for the full step-by-step run guide. TL;DR:

```bash
cp .env.example .env
# fill GEMINI_API_KEY
docker compose up -d postgres redis minio
pip install -r requirements.txt
alembic upgrade head
python scripts/download_embedding_model.py
uvicorn app.main:app --reload          # terminal 1
python workers/run_worker.py            # terminal 2
```

Open http://localhost:8000/docs for Swagger UI.

## Phases

| Phase | Scope                                  | Status |
| ----- | -------------------------------------- | ------ |
| 1     | Foundation: FastAPI, config, DB, health | done   |
| 2     | S3 + document management                 | done   |
| 3     | Taskiq + Redis + ingestion worker        | done   |
| 4     | RAG ingestion pipeline + pgvector        | done   |
| 5     | Retrieval + citations                    | done   |
| 6     | Gemini client + prompts                  | done   |
| 7     | MCP servers + client                     | done   |
| 8     | Agent orchestrator + chat                | done   |
| 9     | Operations: delete, reindex, retry       | done   |

See `PROJECT_PLAN.md` for the full design document.