# Run Guide — Agentic RAG Backend (Windows / PowerShell)

This guide walks you through running the entire project end-to-end on Windows.

**Mode: Hybrid (recommended for dev)** — Postgres + Redis + MinIO in Docker;
FastAPI API and Taskiq worker running natively in your Python venv.

---

## 0. Prerequisites

| Tool | Version | Why |
| --- | --- | --- |
| Docker Desktop | 24+ | Runs Postgres, Redis, MinIO |
| Python | 3.11+ | App + worker runtime |
| Gemini API key | [get one](https://aistudio.google.com/apikey) | Agent reasoning |

> Total disk footprint after setup: ~2 GB (mostly the sentence-transformers model + Python venv).

---

## 1. Enter the project directory

```powershell
cd C:\Users\hp\OneDrive\Desktop\agentic-rag-backend
```

---

## 2. Check your `.env` file

Open `.env` and confirm these are set:

| Variable | Value |
| --- | --- |
| `GEMINI_API_KEY` | Your Gemini API key (required for /chat) |
| `STORAGE_BACKEND` | `minio` (default for local dev) |
| `AWS_ACCESS_KEY_ID` | `minioadmin` |
| `AWS_SECRET_ACCESS_KEY` | `minioadmin` |
| `S3_BUCKET_NAME` | `agentic-rag-docs` (or any name) |

All other values can stay at defaults for local dev.

---

## 3. Start Postgres + Redis + MinIO (Docker)

```powershell
docker compose up -d postgres redis minio
```

Wait for all three containers to be healthy:

```powershell
docker compose ps
# All three should show "healthy" under STATUS
```

If MinIO doesn't come up:
```powershell
docker compose logs minio
```

> MinIO console: http://localhost:9001 (login: `minioadmin` / `minioadmin`)

---

## 4. Activate the virtual environment

```powershell
.venv\Scripts\Activate.ps1
```

If you get an execution policy error, run once as admin:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

## 5. Install Python dependencies (first time only)

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 6. Create the database and enable pgvector (first time only)

```powershell
python -m scripts.create_database
```

Expected output:
```
[ok] created database 'agentic_rag' owned by 'app'
[ok] enabled pgvector extension
```

If you see `database already exists`, that's fine — it's idempotent.

---

## 7. Run Alembic migrations (first time or after schema changes)

```powershell
alembic upgrade head
```

Verify the schema:
```powershell
docker exec -it agentic-rag-postgres psql -U app -d agentic_rag -c "\dt"
# Should list: documents, ingestion_jobs, document_chunks, conversations, messages, alembic_version
```

---

## 8. Pre-download the BGE embedding model (first time only)

```powershell
python -m scripts.download_embedding_model
```

Expected output:
```
Downloading embedding model: BAAI/bge-small-en-v1.5
Cache dir: ./models
Done. Model produces 384-dimensional vectors.
```

---

## 9. Terminal 1 — Start the FastAPI server

```powershell
python run_server.py
```

You should see:
```
INFO startup_complete
INFO: Uvicorn running on http://0.0.0.0:8000
```

- API base: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 10. Terminal 2 — Start the Taskiq worker

Open a **new PowerShell window**:

```powershell
cd C:\Users\hp\OneDrive\Desktop\agentic-rag-backend
.venv\Scripts\Activate.ps1
python workers\run_worker.py
```

Expected output:
```
INFO worker_starting ...
INFO taskiq_broker_created ...
INFO worker_ready
```

> **The worker MUST be running for document uploads to be processed.**

---

## 11. Verify everything is running

```powershell
# Basic health
curl http://localhost:8000/api/v1/health
# Expected: {"status":"ok"}

# Full readiness (DB + pgvector + Redis + Storage)
curl http://localhost:8000/api/v1/health/ready
# Expected: {"status":"ok","components":{"database":"ok","pgvector":"ok","redis":"ok","storage":"ok"}}

# List available MCP tools
curl http://localhost:8000/api/v1/tools
# Expected: {"tools":[{"name":"search_documents",...},{"name":"calculate",...},{"name":"get_weather",...}]}
```

---

## 12. Smoke test: Upload a document

Create a test file:
```powershell
"Employees may request annual leave of up to 24 days per calendar year. Leave requests must be submitted at least 7 days in advance via the HR portal. Emergency leave of up to 3 days may be granted at manager discretion. Unused leave does not carry over." | Out-File -Encoding utf8 C:\Temp\leave_policy.txt
```

Upload it:
```powershell
curl -X POST http://localhost:8000/api/v1/documents/upload -F "file=@C:\Temp\leave_policy.txt"
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

Watch the **worker terminal** — it should show:
```
INFO task_started document_id=doc_01jz...
INFO parsed ...
INFO chunked ...
INFO indexed ...
INFO ingestion_completed
```

---

## 13. Smoke test: List documents and check status

```powershell
# List all documents
curl http://localhost:8000/api/v1/documents

# Check ingestion jobs
curl http://localhost:8000/api/v1/ingestion-jobs
# status should be "completed"
```

---

## 14. Smoke test: Semantic search

```powershell
curl -X POST http://localhost:8000/api/v1/retrieval/search `
  -H "Content-Type: application/json" `
  -d '{"query": "How many leave days per year?", "top_k": 5}'
```

Expected: chunks with `score > 0` related to leave policy.

---

## 15. Smoke test: Agentic chat

```powershell
curl -X POST http://localhost:8000/api/v1/chat `
  -H "Content-Type: application/json" `
  -d '{"message": "Summarize the leave policy in one sentence."}'
```

Expected response:
```json
{
  "conversation_id": "conv_01jz...",
  "answer": "According to the leave policy, employees receive 24 days of annual leave per year...",
  "citations": [...],
  "tool_calls": [{"tool_name": "search_documents", "status": "success"}],
  "steps_taken": 2
}
```

---

## 16. Smoke test: Calculator and weather via chat

```powershell
# Calculator (uses MCP calculate tool)
curl -X POST http://localhost:8000/api/v1/chat `
  -H "Content-Type: application/json" `
  -d '{"message": "What is 25 multiplied by 18?"}'

# Weather (uses MCP get_weather tool)
curl -X POST http://localhost:8000/api/v1/chat `
  -H "Content-Type: application/json" `
  -d '{"message": "What is the current temperature in Mumbai?"}'
```

---

## 17. Conversation history

```powershell
# List all conversations
curl http://localhost:8000/api/v1/chat/conversations

# Get messages for a specific conversation
curl http://localhost:8000/api/v1/chat/conversations/<conversation_id>
```

---

## 18. Document operations

```powershell
# Re-index a document (e.g. after changing chunk_size in .env)
curl -X POST http://localhost:8000/api/v1/documents/<doc_id>/reindex

# Delete a document (cascades to chunks + ingestion jobs + S3 objects)
curl -X DELETE http://localhost:8000/api/v1/documents/<doc_id>
```

---

## 19. Retry a failed ingestion job

```powershell
curl -X POST http://localhost:8000/api/v1/ingestion-jobs/<job_id>/retry
```

---

## Verification Checklist

| Check | Pass when |
| --- | --- |
| `GET /api/v1/health` | Returns `{"status":"ok"}` |
| `GET /api/v1/health/ready` | All components show `"ok"` |
| `POST /api/v1/documents/upload` | Returns 202 with `document_id` + `job_id` |
| Worker terminal | Shows `ingestion_completed` |
| `GET /api/v1/documents/{id}` | `status: indexed` |
| `POST /api/v1/retrieval/search` | Returns chunks with `score > 0` |
| `POST /api/v1/chat` (doc question) | Returns answer + citations + tool_calls |
| `POST /api/v1/chat` ("what is 7+8?") | Agent calls `calculate` MCP tool |
| `POST /api/v1/chat` ("weather in Tokyo?") | Agent calls `get_weather` MCP tool |
| `GET /api/v1/tools` | Lists `search_documents`, `calculate`, `get_weather` |
| `DELETE /api/v1/documents/{id}` | Returns 204; chunks + S3 objects removed |

---

## Troubleshooting

### Worker can't connect to Postgres
- Check `DATABASE_URL` in `.env` — use `localhost:5432` when running natively on host.
- Run `docker compose logs postgres` to check if Postgres is up.

### MCP tools endpoint returns empty list
- The API logs `mcp_init_failed` on startup if an MCP server fails to start.
- Manually test: `python -m app.mcp.servers.calculator_server`
- Ensure `mcp` package is installed: `pip install -r requirements.txt`

### Embedding model fails to download
- Retry, or set `HF_ENDPOINT=https://hf-mirror.com` in PowerShell:
  ```powershell
  $env:HF_ENDPOINT = "https://hf-mirror.com"
  python -m scripts.download_embedding_model
  ```

### Gemini returns 403 / quota exceeded
- Verify your key at https://aistudio.google.com/apikey
- Try a different model in `.env`: `GEMINI_MODEL=gemini-2.0-flash`

### `alembic upgrade head` fails on `vector` extension
- Run `python -m scripts.create_database` first.
- Or manually: `docker exec -it agentic-rag-postgres psql -U app -d agentic_rag -c "CREATE EXTENSION IF NOT EXISTS vector;"`

### Stale Redis queue after schema change
```powershell
docker compose down -v   # wipes volumes (Redis data + Postgres data)
docker compose up -d postgres redis minio
# Then re-run steps 6 and 7
```

---

## Architecture Flow

```
[Client]
   |
   v
[FastAPI app (run_server.py -> uvicorn:8000)]
   |  +------------------+
   |  | /documents       |-- upload --> [S3 / MinIO]
   |  | /ingestion-jobs  |-- enqueue --> [Taskiq --> Redis queue]
   |  | /retrieval       |-- embed + search --> [pgvector]
   |  | /chat            |-- AgentOrchestrator
   |  | /tools           |-- lists MCP tools
   |  +------------------+
   |
   v
[AgentOrchestrator]
   +-- GeminiClient   (google-genai SDK)
   +-- AgentMemory    (loads conversation from Postgres)
   +-- ToolRegistry   (wraps MCP client)
   +-- ToolExecutor   (calls MCP servers via stdio)
              |
              v
      +----------------+
      | MCP servers    |  (3 subprocesses)
      | - rag          |  -> Retriever (pgvector)
      | - calculator   |  -> pure Python math
      | - weather      |  -> Open-Meteo HTTP API
      +----------------+
   |
   v
[Worker (python workers\run_worker.py)]
   +-- Consumes Taskiq queue
   +-- Downloads from S3 / MinIO
   +-- Runs IngestionPipeline:
   |     parse -> chunk -> embed (BGE bge-small-en-v1.5) -> pgvector
   +-- Updates job + document status in Postgres
```