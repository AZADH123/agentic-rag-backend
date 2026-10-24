# Agentic RAG Platform

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Google%20Gemini-Flash-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="Gemini" />
  <img src="https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL pgvector" />
  <img src="https://img.shields.io/badge/Taskiq-Distributed%20Queue-FF4F64?style=for-the-badge" alt="Taskiq" />
  <img src="https://img.shields.io/badge/MCP-Model%20Context%20Protocol-8A2BE2?style=for-the-badge" alt="MCP" />
  <img src="https://img.shields.io/badge/React%2019-Vite%20%2B%20TS-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React" />
</p>

An enterprise-grade, modular **Agentic Retrieval-Augmented Generation (RAG)** platform powered by autonomous reasoning, the **Model Context Protocol (MCP)**, asynchronous document ingestion, and verifiable citation attribution.

---

## System Architecture

```mermaid
flowchart TB
    %% Styling tokens
    classDef clientLayer fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;
    classDef gatewayLayer fill:#0f172a,stroke:#818cf8,stroke-width:2px,color:#f8fafc;
    classDef agentLayer fill:#1e1b4b,stroke:#a855f7,stroke-width:2px,color:#f8fafc;
    classDef mcpLayer fill:#311042,stroke:#ec4899,stroke-width:2px,color:#f8fafc;
    classDef workerLayer fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#f8fafc;
    classDef dataLayer fill:#1c1917,stroke:#f59e0b,stroke-width:2px,color:#f8fafc;

    subgraph CLIENTS [" Client Layer "]
        UI["ðŸ–¥ï¸ React 19 Frontend<br/>(Vite + TypeScript)"]:::clientLayer
        SDK["ðŸ”Œ REST / API Consumer<br/>(CURL / External Apps)"]:::clientLayer
    end

    subgraph API_GATEWAY [" Application Gateway (FastAPI) "]
        GATEWAY["ðŸ›¡ï¸ FastAPI Web Layer<br/>(Auth â€¢ Rate Limit â€¢ Tracing â€¢ CORS)"]:::gatewayLayer
        ROUTERS["ðŸ§­ API Endpoints<br/>/chat â€¢ /documents â€¢ /retrieval â€¢ /tools"]:::gatewayLayer
        GATEWAY --> ROUTERS
    end

    subgraph AGENT_CORE [" Agent Reasoning Engine (ReAct Loop) "]
        ORCH["ðŸ§  Agent Orchestrator<br/>(Context â€¢ State â€¢ Safety)"]:::agentLayer
        MEMORY["ðŸ“ Agent Memory<br/>(Sliding Window History)"]:::agentLayer
        PLANNER["ðŸ” Dynamic Planner<br/>(call_tool | answer | stop)"]:::agentLayer
        LLM["âœ¨ Google Gemini<br/>(google-genai SDK)"]:::agentLayer

        ORCH <--> MEMORY
        ORCH <--> LLM
        ORCH --> PLANNER
    end

    subgraph MCP_SYSTEM [" Tool Ecosystem (Model Context Protocol) "]
        MCP_CLIENT["âš¡ MCP Client<br/>(Stdio JSON-RPC Multiplexer)"]:::mcpLayer
        RAG_TOOL["ðŸ“š RAG Knowledge Server<br/>(Semantic Search & Chunks)"]:::mcpLayer
        CALC_TOOL["ðŸ§® Math Calculator Server<br/>(Deterministic Arithmetic)"]:::mcpLayer
        WEATHER_TOOL["ðŸŒ¤ï¸ Open-Meteo Server<br/>(Live External Weather)"]:::mcpLayer

        MCP_CLIENT --> RAG_TOOL
        MCP_CLIENT --> CALC_TOOL
        MCP_CLIENT --> WEATHER_TOOL
    end

    subgraph ASYNC_INGESTION [" Asynchronous Processing Pipeline "]
        TASKIQ["â±ï¸ Taskiq Job Worker<br/>(Async Distributed Workers)"]:::workerLayer
        PARSER["ðŸ“„ Document Parser<br/>(PDF, DOCX, TXT)"]:::workerLayer
        CHUNKER["âœ‚ï¸ Semantic Chunker<br/>(800 tokens + 120 overlap)"]:::workerLayer
        EMBED["ðŸ§¬ Local BGE Embeddings<br/>(BAAI/bge-small-en-v1.5)"]:::workerLayer

        TASKIQ --> PARSER --> CHUNKER --> EMBED
    end

    subgraph STORAGE_LAYER [" Persistence & Storage Infrastructure "]
        S3["ðŸ“¦ MinIO / Amazon S3<br/>(Raw Document Lake)"]:::dataLayer
        REDIS["âš¡ Redis Broker<br/>(Taskiq Queue & Result Backend)"]:::dataLayer
        PGVECTOR[("ðŸ˜ PostgreSQL + pgvector<br/>â€¢ Metadata & Relational State<br/>â€¢ HNSW Vector Index (384-dim)<br/>â€¢ Conversations & Audit Trail")]:::dataLayer
    end

    %% Inter-layer relationships
    CLIENTS ==>|HTTP / REST| GATEWAY
    ROUTERS ==>|Sync Execution| ORCH
    ROUTERS ==>|Enqueue Upload| REDIS
    ROUTERS ==>|Raw Object Storage| S3

    ORCH ==>|JSON-RPC Stdio| MCP_CLIENT
    RAG_TOOL -.->|Cosine Search| PGVECTOR

    REDIS ==>|Fetch Jobs| TASKIQ
    S3 -.->|Stream File| PARSER
    EMBED ==>|Store Chunks & Embeddings| PGVECTOR
```

---

## Core Execution Flows

### 1. Agentic ReAct Reasoning Loop

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Frontend
    participant Orch as Agent Orchestrator
    participant Gemini as Google Gemini
    participant MCP as MCP Client
    participant Tools as MCP Servers (RAG/Calc/Weather)
    participant DB as PostgreSQL

    User->>Orch: POST /api/v1/chat (User Query)
    Orch->>DB: Load conversation history (AgentMemory)

    loop Agent Execution (Max 6 Steps)
        Orch->>Gemini: Request Next Step (History + MCP Tools Schema)
        Gemini-->>Orch: Action Decision (e.g. Call Tool 'rag_search')

        alt Action == Call Tool
            Orch->>MCP: Dispatch Tool Execution (JSON-RPC)
            MCP->>Tools: Run tool with parsed arguments
            Tools-->>MCP: Tool Output / Document Chunks
            MCP-->>Orch: Formatted Tool Result
            Orch->>Orch: Record step & extract verified citations
        else Action == Answer / Stop
            Orch->>Orch: Synthesize final answer
        end
    end

    Orch->>DB: Persist User + Assistant Turn & Audit Records
    Orch-->>User: ChatResponse (Answer + Citations + Tool Trajectory)
```

### 2. High-Throughput Ingestion & Vectorization

```mermaid
sequenceDiagram
    autonumber
    actor Client as Client / Admin
    participant API as FastAPI Documents API
    participant S3 as S3 / MinIO
    participant Redis as Redis Queue
    participant Worker as Taskiq Ingestion Worker
    participant BGE as BGE Embedding Model
    participant PG as PostgreSQL (pgvector)

    Client->>API: POST /api/v1/documents/upload (PDF/DOCX/TXT)
    API->>S3: Upload raw document object
    API->>PG: Insert document metadata (status: PENDING)
    API->>Redis: Enqueue ingestion task
    API-->>Client: 202 Accepted (job_id, document_id)

    Redis->>Worker: Consume Ingestion Task
    Worker->>S3: Stream document binary
    Worker->>Worker: Extract text & compute SHA-256 hash (Deduplication)
    Worker->>Worker: Chunk text (800 chars / 120 overlap)
    Worker->>BGE: Generate dense vectors (384-dim)
    Worker->>PG: Batch insert chunks + vectors into pgvector
    Worker->>PG: Update document status to READY
```

---

## Architectural Highlights

| Component | Technology | Responsibility |
| :--- | :--- | :--- |
| **Client UI** | React 19, Vite, TypeScript, Tailwind | Modern interactive UI with live chat streaming, citation previews, document status tracking, and MCP tool debugging. |
| **API Gateway** | FastAPI, Pydantic V2, Structlog | Async REST API enforcing authentication, request ID correlation, rate limiting, and structured error propagation. |
| **Reasoning Engine** | Google Gemini (`google-genai`), ReAct Pattern | Multi-turn reasoning agent with custom policies, step-budget safety guards, and explicit citation attribution. |
| **Tool Layer** | Model Context Protocol (MCP) | Decoupled tool servers executed via standardized stdio JSON-RPC protocol (`rag_server`, `calculator_server`, `weather_server`). |
| **Ingestion Pipeline** | Taskiq, Redis, PyTorch, PyPDF | Background ingestion worker capable of processing complex PDFs and documents without blocking user requests. |
| **Embeddings & Search** | BAAI/bge-small-en-v1.5, pgvector | Local, cost-effective 384-dimensional dense embeddings paired with PostgreSQL HNSW indexing for low-latency cosine retrieval. |
| **Object Lake** | MinIO / AWS S3 | Durable multi-tenant raw file storage with secure pre-signed URLs. |

---

## Quick Start

See **[RUN.md](RUN.md)** for the complete step-by-step installation and testing guide.

```bash
# 1. Environment Setup
cp .env.example .env
# Edit .env and insert your GEMINI_API_KEY

# 2. Launch Core Services (Docker)
docker compose up -d postgres redis minio

# 3. Setup Python Virtual Environment
pip install -r requirements.txt
alembic upgrade head
python scripts/download_embedding_model.py

# 4. Start the Application
python run_server.py           # Terminal 1: FastAPI API Gateway
python workers/run_worker.py   # Terminal 2: Taskiq Background Worker
```

- **Swagger Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## Frontend Web Application

A companion dashboard is included under `/frontend`:

```bash
cd frontend
npm install
npm run dev
```

Visit **[http://localhost:5173](http://localhost:5173)** to explore:
- ðŸ’¬ **Interactive Agent Chat** with citation badges and tool execution trajectory.
- ðŸ“ **Document Studio** with drag-and-drop upload and ingestion status tracking.
- ðŸ”Ž **Semantic Retrieval Search** to test vector similarity and inspect raw chunk hits.
- ðŸ› ï¸ **MCP Tools Catalog** showing tool definitions, schema parameters, and real-time statuses.

---

## Implementation Roadmap

| Phase | Module | Details | Status |
| :---: | :--- | :--- | :---: |
| **1** | **Foundation** | FastAPI architecture, config management, DB session, health probes | âœ… Complete |
| **2** | **Document Management** | MinIO/S3 object storage, presigned URLs, document metadata | âœ… Complete |
| **3** | **Distributed Ingestion** | Taskiq worker, Redis broker, retry policies, task progress tracking | âœ… Complete |
| **4** | **Vector Search** | Local BGE embeddings, pgvector HNSW indexing, chunk deduplication | âœ… Complete |
| **5** | **Retrieval Subsystem** | Query rewriting, hybrid cosine retrieval, citation attribution | âœ… Complete |
| **6** | **LLM Integration** | Unified Gemini client (`google-genai`), structured response parsing | âœ… Complete |
| **7** | **MCP Tooling** | RAG, Calculator, and Open-Meteo Weather servers via JSON-RPC stdio | âœ… Complete |
| **8** | **Agent Orchestrator** | ReAct planning loop, sliding memory window, step limits | âœ… Complete |
| **9** | **Operations & Lifecycle** | Document deletion, chunk reindexing, retry management | âœ… Complete |
| **10** | **Frontend Application** | React 19 + TypeScript dashboard & chat interface | âœ… Complete |
