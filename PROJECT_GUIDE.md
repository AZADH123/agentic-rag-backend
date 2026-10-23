# Agentic RAG Backend — Complete Guide

> One document that contains: folder structure, file responsibilities, run steps, and verification. Keep this open in a side pane while you set up the project.

---

## 1. Folder Structure (every file explained)

```text
agentic-rag-backend/
│
├── README.md                    # High-level overview + architecture diagram
├── RUN.md                       # Detailed run guide + troubleshooting
├── PROJECT_GUIDE.md             # ← THIS FILE
├── .gitignore
├── .env.example                 # copy to .env, then fill in GEMINI_API_KEY
├── pyproject.toml               # ruff / black / mypy / setuptools config
├── requirements.txt             # pinned runtime deps
├── requirements-dev.txt         # ruff, ipython, etc.
├── Dockerfile                   # single image for API + worker
├── docker-compose.yml           # postgres + redis + minio (+ optional api/worker)
├── alembic.ini                  # alembic config (URL overridden by app settings)
│
├── app/                         # ───── Application code ─────
│   ├── __init__.py
│   ├── main.py                  # FastAPI app factory + router mounting
│   ├── lifespan.py              # startup: logging, DB engine, S3 bucket, MCP client
│   ├── dependencies.py          # FastAPI deps: get_session, get_current_owner
│   │
│   ├── core/                    # cross-cutting concerns
│   │   ├── __init__.py
│   │   ├── config.py            # Settings (pydantic-settings, env-driven)
│   │   ├── logging.py           # structlog setup + secret redaction
│   │   ├── exceptions.py        # AppError hierarchy + JSON error handlers
│   │   ├── middleware.py        # request_id, rate limit, CORS
│   │   └── security.py          # X-API-Key auth (off in dev unless API_KEY set)
│   │
│   ├── api/                     # HTTP layer (no business logic)
│   │   ├── __init__.py
│   │   ├── router.py            # mounts /v1 router
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py        # aggregates all v1 sub-routers
│   │       ├── health.py        # GET /health, /health/ready
│   │       ├── documents.py     # POST /documents/upload, GET/DELETE, /reindex
│   │       ├── ingestion_jobs.py # GET list, GET one, POST /retry
│   │       ├── retrieval.py     # POST /retrieval/search, GET chunks
│   │       ├── chat.py          # POST /chat
│   │       ├── conversations.py # GET list, GET one, DELETE
│   │       └── tools.py         # GET /tools, GET /tools/{name}
│   │
│   ├── schemas/                 # Pydantic request/response contracts
│   │   ├── __init__.py
│   │   ├── common.py            # PaginatedResponse, ErrorResponse base
│   │   ├── document.py          # DocumentResponse, UploadResponse, etc.
│   │   ├── ingestion_job.py     # IngestionJobResponse
│   │   ├── retrieval.py         # SearchRequest, SearchResponse, ChunkHit
│   │   ├── chat.py              # ChatRequest, ChatResponse, ConversationResponse
│   │   └── citation.py         # Citation, ToolCallRecord
│   │
│   ├── modules/                 # domain modules (DDD-style)
│   │   ├── __init__.py
│   │   ├── documents/
│   │   │   ├── __init__.py
│   │   │   ├── models.py        # Document ORM (status state machine fields)
│   │   │   ├── repository.py    # CRUD over documents table
│   │   │   ├── service.py       # upload_and_enqueue, delete, reindex
│   │   │   └── validators.py   # filename / content-type / size checks
│   │   │
│   │   ├── ingestion_jobs/
│   │   │   ├── __init__.py
│   │   │   ├── models.py        # IngestionJob ORM
│   │   │   ├── repository.py    # status transitions, attempt counter
│   │   │   └── service.py       # retry logic with bounded attempts
│   │   │
│   │   └── conversations/
│   │       ├── __init__.py
│   │       ├── models.py        # Conversation + Message ORM (JSONB citations)
│   │       ├── repository.py
│   │       └── service.py       # create/get/list/delete + add_message
│   │
│   ├── agent/                   # ───── Agent loop ─────
│   │   ├── __init__.py
│   │   ├── orchestrator.py     # main loop: call Gemini → execute tool → repeat
│   │   ├── planner.py          # decides next action from LLM response
│   │   ├── executor.py          # runs a tool via ToolRegistry, captures citations
│   │   ├── state.py             # RunState (messages, tool_calls, citations, steps)
│   │   ├── memory.py            # builds Gemini `contents` from DB conversation
│   │   ├── tool_registry.py     # allowlist + per-tool/per-run call limits
│   │   ├── policies.py          # max_steps, max_query_refinements
│   │   └── mcp_client.py        # thin adapter to app.mcp.client
│   │
│   ├── llm/                     # ───── Gemini integration ─────
│   │   ├── __init__.py
│   │   ├── gemini_client.py    # GeminiClient (google-genai SDK wrapper)
│   │   ├── model_factory.py     # reads GEMINI_MODEL, warns on unknown models
│   │   ├── tool_calling.py      # convert tools↔Gemini spec, parse responses
│   │   └── response_parser.py   # re-export of _parse_response
│   │
│   ├── rag/                     # ───── RAG pipeline ─────
│   │   ├── __init__.py
│   │   ├── embeddings/
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # EmbeddingModel abstract interface
│   │   │   ├── bge_embeddings.py # BGE impl (async, offloaded to thread)
│   │   │   └── model_loader.py  # singleton SentenceTransformer loader
│   │   │
│   │   ├── ingestion/
│   │   │   ├── __init__.py
│   │   │   ├── parsers.py       # PDF (pypdf) / DOCX (python-docx) / TXT
│   │   │   ├── chunker.py        # sentence-boundary chunking + overlap
│   │   │   ├── metadata.py       # builds JSONB metadata per chunk
│   │   │   └── pipeline.py       # end-to-end: parse → chunk → embed → index
│   │   │
│   │   ├── retrieval/
│   │   │   ├── __init__.py
│   │   │   ├── retriever.py      # query → embed → search → rerank → citations
│   │   │   ├── query_transformer.py # normalize + strip injection patterns
│   │   │   ├── reranker.py       # Jaccard dedup + truncate to top_k
│   │   │   └── citations.py      # SearchHit → Citation schema
│   │   │
│   │   ├── indexing/
│   │   │   ├── __init__.py
│   │   │   ├── indexer.py        # DocumentChunk ORM + Indexer.upsert
│   │   │   └── deduplication.py  # exact-text dedupe pass
│   │   │
│   │   └── vector_store/
│   │       ├── __init__.py
│   │       ├── base.py           # VectorStore abstract (CRUD + search)
│   │       └── pgvector_store.py # pgvector impl (cosine, HNSW index)
│   │
│   ├── storage/                  # ───── Object storage ─────
│   │   ├── __init__.py
│   │   ├── s3_client.py          # boto3 client factory (S3 or MinIO)
│   │   ├── object_storage.py     # high-level upload/download/delete/presign
│   │   └── storage_keys.py       # safe S3 key construction + new_document_id
│   │
│   ├── queue/                    # ───── Taskiq + Redis ─────
│   │   ├── __init__.py
│   │   ├── broker.py             # ListQueueBroker + RedisAsyncResultBackend
│   │   ├── tasks.py              # @broker.task process_document_task + enqueue_ingestion
│   │   └── job_status.py         # JobStatus/DocumentStatus constants + transition table
│   │
│   ├── workers/
│   │   ├── __init__.py
│   │   └── ingestion_worker.py   # run_ingestion() — called by Taskiq
│   │
│   ├── mcp/                      # ───── MCP integration ─────
│   │   ├── __init__.py
│   │   ├── client.py             # McpClient: launches + manages server subprocesses
│   │   ├── server_config.py      # McpServerSpec list (command + allowlist)
│   │   └── servers/
│   │       ├── __init__.py
│   │       ├── rag_server.py     # search_documents tool (stdio server)
│   │       ├── calculator_server.py # calculate tool (no eval)
│   │       └── weather_server.py  # get_weather tool (Open-Meteo)
│   │
│   ├── prompts/                  # ───── Prompt templates ─────
│   │   ├── __init__.py
│   │   ├── system.py             # SYSTEM_PROMPT (citation rules, loop rules)
│   │   ├── planning.py           # evidence evaluation prompt
│   │   ├── retrieval.py          # retrieved-chunks context template
│   │   └── answer_generation.py  # final answer template
│   │
│   ├── database/                 # ───── DB layer ─────
│   │   ├── __init__.py
│   │   ├── base.py               # DeclarativeBase
│   │   ├── session.py            # async engine + AsyncSession factory
│   │   └── migrations/
│   │       ├── __init__.py
│   │       ├── env.py            # Alembic env (async, reads app settings)
│   │       ├── script.py.mako    # revision template
│   │       └── versions/
│   │           ├── 0001_documents.py        # documents table + pgvector ext
│   │           ├── 0002_ingestion_jobs.py   # ingestion_jobs table
│   │           ├── 0003_document_chunks.py  # document_chunks + HNSW index
│   │           └── 0004_conversations.py    # conversations + messages
│   │
│   └── utils/                    # ───── Helpers ─────
│       ├── __init__.py
│       ├── file_hash.py          # SHA-256 for dedup
│       ├── text_normalizer.py    # NFC + whitespace collapse
│       └── ids.py                # ULID-based prefix IDs (doc_, job_, chunk_, etc.)
│
├── workers/
│   └── run_worker.py             # standalone Taskiq worker entrypoint
│
└── scripts/
    ├── create_database.py        # CREATE DATABASE + CREATE EXTENSION vector
    └── download_embedding_model.py # pre-fetch BGE so first ingestion is fast
```

**File count**: 115 Python files + 8 config/doc files = 123 total.

---

## 2. Steps to Run the Project

> Prerequisites: Docker 24+, Python 3.11+, a [Gemini API key](https://aistudio.google.com/apikey).

### Step 1 — Enter the project folder

```bash
cd /path/to/agentic-rag-backend
```

### Step 2 — Copy and edit the environment file

```bash
cp .env.example .env
```

Open `.env` in your editor and set at minimum:

```dotenv
GEMINI_API_KEY=your-real-key-here

# Defaults below are fine for local dev:
STORAGE_BACKEND=minio
S3_BUCKET_NAME=agentic-rag-documents
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
S3_ENDPOINT_URL=http://localhost:9000
```

> If you have a real AWS account and want to use S3 instead of MinIO, set `STORAGE_BACKEND=s3`, leave `S3_ENDPOINT_URL` empty, set `S3_USE_PATH_STYLE=false`, and use real AWS credentials.

### Step 3 — Start the infrastructure containers

```bash
docker compose up -d postgres redis minio
```

Wait for them to be healthy:

```bash
docker compose ps
# All three should show Status = "healthy"
```

- PostgreSQL → `localhost:5432` (user `app`, password `password`, db `agentic_rag`)
- Redis → `localhost:6379`
- MinIO console → http://localhost:9001 (login: `minioadmin` / `minioadmin`)

### Step 4 — Create a Python virtual environment and install deps

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

(On Windows: use `python -m venv .venv` and `.venv\Scripts\activate`.)

### Step 5 — Create the database and enable pgvector

```bash
python scripts/create_database.py
```

Expected output:
```
[ok] created database 'agentic_rag' owned by 'app'
[ok] enabled pgvector extension
```

### Step 6 — Run database migrations

```bash
alembic upgrade head
```

Expected output ends with:
```
INFO  [alembic.runtime.migration] Running upgrade_0003 -> 0004_conversations, create conversations and messages tables
```

Verify the tables exist:
```bash
docker exec -it agentic-rag-postgres psql -U app -d agentic_rag -c "\dt"
```

You should see: `documents`, `ingestion_jobs`, `document_chunks`, `conversations`, `messages`, `alembic_version`.

### Step 7 — Pre-download the embedding model (one-time, ~130MB)

```bash
python scripts/download_embedding_model.py
```

Expected output:
```
Downloading embedding model: BAAI/bge-small-en-v1.5
Done. Model produces 384-dimensional vectors.
```

This avoids a long wait on the first document upload.

### Step 8 — Start the FastAPI API (Terminal 1)

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Expected:
```
INFO: startup_complete
INFO: Uvicorn running on http://0.0.0.0:8000
```

Open Swagger UI: **http://localhost:8000/docs**

### Step 9 — Start the Taskiq worker (Terminal 2)

Open a NEW terminal, activate the venv, then:

```bash
cd /path/to/agentic-rag-backend
source .venv/bin/activate
python workers/run_worker.py
```

Expected:
```
INFO worker_starting
INFO taskiq_broker_created
```

Leave it running. **Without the worker, document uploads will stay in `queued` status forever.**

---

## 3. Verification (copy-paste commands)

### Step 10 — Health check

```bash
curl http://localhost:8000/api/v1/health
# {"status":"ok"}

curl http://localhost:8000/api/v1/health/ready
# {"status":"ok","components":{"database":"ok","pgvector":"ok","redis":"ok","storage":"ok"}}
```

### Step 11 — Upload a document

Create a sample text file:

```bash
cat > /tmp/leave_policy.txt <<'EOF'
Employees may request annual leave of up to 24 days per calendar year.
Leave requests must be submitted at least 7 days in advance via the HR portal.
Emergency leave of up to 3 days may be granted at manager discretion.
Unused leave does not carry over to the next calendar year.
EOF
```

Upload it:

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@/tmp/leave_policy.txt"
```

Expected response (HTTP 202):
```json
{
  "document_id": "doc_01jz...",
  "job_id": "job_01jz...",
  "filename": "leave_policy.txt",
  "status": "queued"
}
```

In the **worker terminal** you should see:
```
INFO task_started document_id=doc_... job_id=job_...
INFO parsed pages=1 text_chars=...
INFO chunked chunks=1
INFO indexed written=1
INFO ingestion_completed
```

### Step 12 — Check document status

```bash
curl http://localhost:8000/api/v1/documents
# {"items":[{"document_id":"doc_...","status":"indexed",...}],"total":1}

curl http://localhost:8000/api/v1/ingestion-jobs
# {"items":[{"job_id":"job_...","status":"completed",...}],"total":1}
```

### Step 13 — Test retrieval

```bash
curl -X POST http://localhost:8000/api/v1/retrieval/search \
  -H "Content-Type: application/json" \
  -d '{"query": "How many leave days per year?", "top_k": 5}'
```

Expected:
```json
{
  "query": "How many leave days per year?",
  "results": [
    {
      "document_id": "doc_01jz...",
      "chunk_id": "chunk_01jz...",
      "text": "Employees may request annual leave of up to 24 days...",
      "score": 0.87,
      "metadata": {"filename": "leave_policy.txt", "page": 1, "sequence": 0}
    }
  ],
  "total": 1
}
```

### Step 14 — Test Agentic chat (the main feature)

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Summarize the leave policy in one sentence."}'
```

Expected:
```json
{
  "conversation_id": "conv_01jz...",
  "answer": "According to the leave policy, employees receive up to 24 days of annual leave per calendar year, with requests required at least 7 days in advance...",
  "citations": [
    {
      "document_id": "doc_01jz...",
      "chunk_id": "chunk_01jz...",
      "filename": "leave_policy.txt",
      "page": 1,
      "snippet": "Employees may request annual leave..."
    }
  ],
  "tool_calls": [
    {"tool_name": "search_documents", "status": "success"}
  ],
  "steps_taken": 2
}
```

### Step 15 — Test other MCP tools via chat

```bash
# Calculator
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 25 multiplied by 18?"}'

# Weather
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the current temperature in Mumbai?"}'
```

### Step 16 — List MCP tools directly

```bash
curl http://localhost:8000/api/v1/tools
# {"tools":[{"name":"search_documents",...},{"name":"calculate",...},{"name":"get_weather",...}]}
```

### Step 17 — View conversation history

```bash
# List conversations
curl http://localhost:8000/api/v1/chat/conversations

# Get one with messages
curl http://localhost:8000/api/v1/chat/conversations/<conversation_id_from_step_14>
```

### Step 18 — Document operations

```bash
# Re-index (after changing CHUNK_SIZE in .env, for example)
curl -X POST http://localhost:8000/api/v1/documents/<doc_id>/reindex

# Delete (cascades to chunks + S3 + ingestion jobs)
curl -X DELETE http://localhost:8000/api/v1/documents/<doc_id>
```

### Step 19 — Retry a failed job

```bash
curl -X POST http://localhost:8000/api/v1/ingestion-jobs/<job_id>/retry
```

---

## 4. Architecture Flow (request lifecycle)

### 4.1 Document upload + ingestion (async)

```text
Client ──POST /documents/upload──► FastAPI
                                    │
                                    ▼
                       DocumentService.upload_and_enqueue()
                                    │
                ┌───────────────────┼───────────────────┐
                ▼                   ▼                   ▼
            validate            upload to S3       INSERT documents
            filename/type/size  (MinIO or AWS)    row (status='uploaded')
                                    │
                                    ▼
                       enqueue_ingestion(document_id)
                                    │
                       ┌────────────┴────────────┐
                       ▼                         ▼
                INSERT ingestion_jobs      Taskiq .kiq()
                (status='queued')          (Redis queue)
                                    │
                       Response 202 ◄──┘
                                                          ┌─────────────────────────┐
                                                          │ Worker process          │
                                                          │ (workers/run_worker.py) │
                                                          │                         │
                                                          │ 1. dequeue from Redis   │
                                                          │ 2. mark job 'processing'│
                                                          │ 3. download S3 bytes    │
                                                          │ 4. IngestionPipeline:   │
                                                          │    parse → chunk →      │
                                                          │    embed (BGE) →        │
                                                          │    upsert pgvector      │
                                                          │ 5. mark job 'completed' │
                                                          │    + doc 'indexed'     │
                                                          └─────────────────────────┘
```

### 4.2 Agentic chat (sync loop)

```text
Client ──POST /chat──► FastAPI
                        │
                        ▼
              AgentOrchestrator.run()
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
        load/create       AgentMemory.build_initial_contents()
        conversation       (load recent messages from Postgres)
                        │
                        ▼
              ┌─────── LOOP (max 6 steps) ───────┐
              │                                   │
              ▼                                   │
        GeminiClient.chat()                       │
        (system prompt + tools + history)         │
              │                                   │
              ▼                                   │
        Planner.plan_next(response)               │
              │                                   │
        ┌─────┼─────────┐                         │
        ▼     ▼         ▼                         │
     answer  stop   call_tool                     │
        │     │         │                         │
        │     │         ▼                         │
        │     │     ToolExecutor.execute()        │
        │     │         │                         │
        │     │         ▼                         │
        │     │     MCP client (stdio)            │
        │     │     ┌───┬───┬───┐                 │
        │     │     ▼   ▼   ▼                   │
        │     │   rag  calc  weather              │
        │     │   (pgvector) (Python) (HTTP)      │
        │     │         │                         │
        │     │         ▼                         │
        │     │     append function_response     │
        │     │     to contents ──────────────────┘
        │     │
        ▼     ▼
   persist user msg + assistant msg to Postgres
                        │
                        ▼
              ChatResponse (answer, citations, tool_calls)
```

---

## 5. Endpoint reference

| Method   | Path                                            | Purpose                            |
| -------- | ----------------------------------------------- | ---------------------------------- |
| GET      | `/api/v1/health`                                | Liveness probe                     |
| GET      | `/api/v1/health/ready`                          | Readiness (DB, Redis, S3)          |
| POST     | `/api/v1/documents/upload`                      | Upload + queue ingestion (202)     |
| GET      | `/api/v1/documents`                             | List documents (owner-scoped)     |
| GET      | `/api/v1/documents/{id}`                       | Get one document                   |
| DELETE   | `/api/v1/documents/{id}`                       | Delete doc + chunks + S3 + jobs    |
| POST     | `/api/v1/documents/{id}/reindex`               | Re-enqueue ingestion               |
| GET      | `/api/v1/ingestion-jobs`                        | List jobs                          |
| GET      | `/api/v1/ingestion-jobs/{id}`                  | Get one job                        |
| POST     | `/api/v1/ingestion-jobs/{id}/retry`           | Retry a failed job                 |
| POST     | `/api/v1/retrieval/search`                     | Semantic search                    |
| GET      | `/api/v1/retrieval/documents/{id}/chunks`      | List chunks for a doc              |
| POST     | `/api/v1/chat`                                  | Send a question to the agent       |
| GET      | `/api/v1/chat/conversations`                    | List conversations                |
| GET      | `/api/v1/chat/conversations/{id}`              | Get conversation + messages        |
| DELETE   | `/api/v1/chat/conversations/{id}`              | Delete a conversation              |
| GET      | `/api/v1/tools`                                 | List MCP tools                     |
| GET      | `/api/v1/tools/{name}`                          | Get tool schema                    |

Swagger UI at http://localhost:8000/docs lets you call all of these interactively.

---

## 6. Common issues and fixes

| Symptom                                              | Cause / Fix                                                            |
| ---------------------------------------------------- | ---------------------------------------------------------------------- |
| `health/ready` shows `"database": "degraded"`        | Postgres not started. Run `docker compose up -d postgres`               |
| `health/ready` shows `"pgvector": "missing"`         | Run `python scripts/create_database.py` to enable the extension        |
| `health/ready` shows `"storage": "degraded"`         | MinIO not started, or wrong credentials in `.env`                      |
| Document upload returns 202 but status stays `queued`| Worker not running. Start it: `python workers/run_worker.py`           |
| `/chat` returns 500 with "GEMINI_API_KEY not set"    | Set `GEMINI_API_KEY` in `.env` and restart uvicorn                     |
| `/chat` returns 502 with "Gemini auth failed"        | Wrong API key, or your key doesn't have access to `gemini-2.5-flash`   |
| `/tools` returns empty list                          | MCP servers failed to start. Check API logs for `mcp_init_failed`      |
| `alembic upgrade head` fails on `vector` extension   | Run `python scripts/create_database.py` first                         |
| Worker hangs on "loading_embedding_model"            | First download is slow. Pre-fetch: `python scripts/download_embedding_model.py` |
| `psycopg.OperationalError: connection refused`       | Postgres not running, or wrong port in `DATABASE_URL`                  |
| MCP server `ImportError: mcp`                        | `pip install -r requirements.txt` (the `mcp` package is listed)        |

For more detail, see `RUN.md > Troubleshooting`.

---

## 7. Switching to full Docker mode (optional)

If you want everything in containers (no Python on host):

1. Edit `docker-compose.yml` and **uncomment** the `api:` and `worker:` service blocks at the bottom (remove the leading `#` from each line).
2. Build and start everything:

```bash
docker compose up -d --build
```

3. Wait for healthchecks:

```bash
docker compose ps
```

4. Run migrations inside the API container:

```bash
docker compose exec api alembic upgrade head
```

5. Pre-download the embedding model inside the worker:

```bash
docker compose exec worker python scripts/download_embedding_model.py
```

API is still at http://localhost:8000.

---

## 8. Key design decisions (for interview prep)

1. **Separation of concerns**: API layer only validates and serializes. Services hold business logic. Repositories do DB access. Models are dumb data. Schemas are external contracts.
2. **Async everywhere**: FastAPI + SQLAlchemy 2.0 async + asyncpg + Taskiq async tasks. CPU-bound work (embedding) is offloaded to threads via `anyio.to_thread.run_sync` so the event loop is never blocked.
3. **Postgres as source of truth**: Redis is only the queue. Document/job/conversation status lives in Postgres so a Redis flush can't lose business state.
4. **Idempotent ingestion**: The indexer deletes existing chunks for a document before inserting new ones — so re-running ingestion on the same doc replaces instead of duplicates.
5. **Bounded agent loop**: `MAX_AGENT_STEPS` (default 6) caps the LLM ↔ tool ping-pong. Per-tool and total call limits are enforced in `ToolRegistry`.
6. **No eval in calculator**: Arithmetic operations are dispatched explicitly. The model can never ask the calculator to `eval("import os; os.system('rm -rf /')")`.
7. **MCP for all tool execution**: The `/tools` REST endpoint only lists tools. The agent calls them through the MCP client (stdio subprocess). No bypass.
8. **Citation integrity**: The system prompt forbids fabrication. The retriever returns chunks with `score` defined as cosine similarity in [0, 1]. Citations include `document_id`, `chunk_id`, `filename`, `page`.
9. **Safe storage keys**: `build_source_key()` strips path components and unsafe characters from user-supplied filenames before constructing S3 keys.
10. **Gemini isolation**: All Gemini-specific code lives in `app/llm/`. The agent orchestrator imports only `LLMResponse` and `GeminiClient` — never the SDK directly.

---

## 9. Where to start reading the code

If you're new to the codebase, read in this order:

1. `app/core/config.py` — see every env var and what it controls
2. `app/main.py` + `app/lifespan.py` — what happens at startup
3. `app/api/v1/documents.py` + `app/modules/documents/service.py` — upload flow
4. `app/queue/tasks.py` + `app/workers/ingestion_worker.py` — async job flow
5. `app/rag/ingestion/pipeline.py` — parse → chunk → embed → index
6. `app/rag/retrieval/retriever.py` — search flow
7. `app/agent/orchestrator.py` — the agent loop (most important file for interviews)
8. `app/mcp/client.py` + `app/mcp/servers/rag_server.py` — how MCP works
9. `app/llm/gemini_client.py` + `app/llm/tool_calling.py` — LLM integration

Total reading time: ~2-3 hours for the full codebase.

---

You're ready to run. Start with Step 1 above.