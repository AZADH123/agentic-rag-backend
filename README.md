# Agentic RAG Backend

A modular, backend-only Agentic RAG platform built with Python, FastAPI, Gemini, BGE embeddings, PostgreSQL+pgvector, Taskiq/Redis, Amazon S3 (or MinIO), and the Model Context Protocol (MCP).

## Architecture at a Glance

```
                â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                â”‚                 Client                   â”‚
                â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                   â”‚ HTTP /api/v1
                â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                â”‚              FastAPI API                 â”‚
                â”‚  (health, documents, retrieval, chat)    â”‚
                â””â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                     â”‚         â”‚          â”‚
        â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”  â”Œâ”€â”€â”€â”€â–¼â”€â”€â”€â”€â”  â”Œâ”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
        â”‚  S3 / MinIO  â”‚  â”‚ Postgresâ”‚  â”‚  Agent          â”‚
        â”‚  (source)    â”‚  â”‚ +pgvec  â”‚  â”‚  orchestrator   â”‚
        â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”˜  â””â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”˜
                               â”‚          â”‚         â”‚
                               â”‚       â”Œâ”€â”€â–¼â”€â”€â”  â”Œâ”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”
                               â”‚       â”‚Geminiâ”‚  â”‚ MCP clientâ”‚
                               â”‚       â””â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                               â”‚                    â”‚ stdio
                               â”‚            â”Œâ”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”
                               â”‚         â”Œâ”€â”€â”€â–¼â”€â”€â” â”Œâ”€â”€â–¼â”€â”€â” â”Œâ”€â”€â”€â–¼â”€â”€â”€â”
                               â”‚         â”‚ RAG  â”‚ â”‚calc â”‚ â”‚weatherâ”‚
                               â”‚         â”‚serverâ”‚ â”‚srv  â”‚ â”‚ srv   â”‚
                               â”‚         â””â”€â”€â”¬â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”˜
                               â”‚            â”‚
                â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜            â”‚
                â”‚   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                â”‚   â”‚ Taskiq worker (separate process)   â”‚
                â”‚   â”‚  - parse PDF/DOCX/TXT              â”‚
                â”‚   â”‚  - chunk + BGE embed               â”‚
                â”‚   â”‚  - write to pgvector                â”‚
                â”‚   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                â”‚                  â”‚
        â”Œâ”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”
        â”‚    Redis     â”‚    â”‚  Postgres   â”‚
        â”‚  (Taskiq q)  â”‚    â”‚  (durable)  â”‚
        â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
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
| 10    | Frontend: React 19 + Vite + TypeScript  | done   |

### Running the Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:5173 to access the dashboard, document uploader, chat UI, semantic retrieval search, and MCP tools overview.

See `PROJECT_PLAN.md` for the full design document.
