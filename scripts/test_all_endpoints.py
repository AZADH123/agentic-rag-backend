"""
Comprehensive test script for all Agentic RAG endpoints.
Runs through the full lifecycle:
1. Health & Readiness checks
2. Tool discovery
3. Document upload & async queue ingestion
4. Job status tracking
5. Document chunk inspection
6. Semantic retrieval & reranking
7. Chat & conversation history
8. Reindex & cleanup deletion
"""

import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import httpx

BASE_URL = "http://localhost:8000"

def log_test(name: str, passed: bool, details: str = ""):
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}")
    if details:
        print(f"       {details}")

def main():
    print("=" * 60)
    print("Running Agentic RAG Backend End-to-End Endpoint Test Suite")
    print("=" * 60)

    from app.core.config import get_settings
    api_key = get_settings().api_key.get_secret_value()
    headers = {"X-API-Key": api_key} if api_key else {}

    client = httpx.Client(base_url=BASE_URL, headers=headers, timeout=60.0)

    # 1. Root health & v1 health
    try:
        r = client.get("/health")
        log_test("GET /health (Liveness)", r.status_code == 200, f"status: {r.json().get('status')}")
    except Exception as e:
        log_test("GET /health (Liveness)", False, str(e))

    try:
        r = client.get("/api/v1/health/ready")
        data = r.json()
        all_ok = data.get("status") == "ok"
        log_test("GET /api/v1/health/ready (Readiness)", r.status_code == 200 and all_ok, f"components: {data.get('components')}")
    except Exception as e:
        log_test("GET /api/v1/health/ready", False, str(e))

    # 2. Tool Discovery
    try:
        r = client.get("/api/v1/tools")
        tools = r.json().get("tools", [])
        tool_names = [t["name"] for t in tools]
        log_test("GET /api/v1/tools (List Tools)", r.status_code == 200 and len(tools) >= 3, f"found: {tool_names}")
    except Exception as e:
        log_test("GET /api/v1/tools", False, str(e))

    try:
        r = client.get("/api/v1/tools/search_documents")
        td = r.json()
        log_test("GET /api/v1/tools/search_documents (Tool Spec)", r.status_code == 200, f"server: {td.get('server')}")
    except Exception as e:
        log_test("GET /api/v1/tools/search_documents", False, str(e))

    # 3. Document Upload
    doc_content = (
        "Project Antigravity Technical Overview.\n\n"
        "1. Architecture and Pipeline Design.\n"
        "Antigravity RAG Backend utilizes PostgreSQL with pgvector for high-performance vector search.\n"
        "The embedding dimension is configured to 384 dimensions using the BAAI/bge-small-en-v1.5 model.\n"
        "The system incorporates Taskiq message queue running over Redis for resilient asynchronous document ingestion.\n\n"
        "2. Chunking and Indexing Strategy.\n"
        "Documents are parsed into semantic page sections and chunked using sentence-boundary and word-aware splitters.\n"
        "Deduplication ensures exact duplicate chunks within the same document are merged to conserve storage.\n"
        "Storage objects are preserved in MinIO S3 object storage.\n\n"
        "3. Security and Tool Integration.\n"
        "Tools are integrated via the Model Context Protocol (MCP) using stdio transport.\n"
        "Supported tools include search_documents, calculate, and get_weather."
    )

    doc_id = None
    job_id = None

    try:
        files = {
            "file": ("antigravity_overview.txt", doc_content.encode("utf-8"), "text/plain")
        }
        r = client.post("/api/v1/documents/upload", files=files)
        data = r.json()
        doc_id = data.get("document_id")
        job_id = data.get("job_id")
        log_test("POST /api/v1/documents/upload (Upload Doc)", r.status_code == 202, f"doc_id={doc_id}, job_id={job_id}")
    except Exception as e:
        log_test("POST /api/v1/documents/upload", False, str(e))

    if not doc_id:
        print("Failed to upload document, stopping downstream document tests.")
        return

    # 4. List Documents
    try:
        r = client.get("/api/v1/documents")
        items = r.json().get("items", [])
        found = any(d["document_id"] == doc_id for d in items)
        log_test("GET /api/v1/documents (List Docs)", r.status_code == 200 and found, f"total={len(items)}")
    except Exception as e:
        log_test("GET /api/v1/documents", False, str(e))

    # 5. Get Document Details
    try:
        r = client.get(f"/api/v1/documents/{doc_id}")
        data = r.json()
        log_test("GET /api/v1/documents/{id} (Get Doc)", r.status_code == 200, f"filename={data.get('filename')}, status={data.get('status')}")
    except Exception as e:
        log_test("GET /api/v1/documents/{id}", False, str(e))

    # 6. Ingestion Jobs
    try:
        r = client.get("/api/v1/ingestion-jobs")
        jobs = r.json().get("items", [])
        log_test("GET /api/v1/ingestion-jobs (List Jobs)", r.status_code == 200, f"count={len(jobs)}")
    except Exception as e:
        log_test("GET /api/v1/ingestion-jobs", False, str(e))

    # Wait for worker to finish processing document
    print("Waiting for ingestion worker to index chunks...")
    for _ in range(30):
        try:
            r = client.get(f"/api/v1/documents/{doc_id}")
            if r.json().get("status") in ("indexed", "failed"):
                break
        except Exception:
            pass
        time.sleep(1)

    r = client.get(f"/api/v1/documents/{doc_id}")
    doc_status = r.json().get("status")
    log_test("Ingestion Worker Status", doc_status == "indexed", f"final_status={doc_status}")

    # 7. Inspect Document Chunks
    try:
        r = client.get(f"/api/v1/retrieval/documents/{doc_id}/chunks")
        chunks = r.json().get("chunks", [])
        log_test("GET /api/v1/retrieval/documents/{id}/chunks", r.status_code == 200 and len(chunks) > 0, f"indexed_chunks={len(chunks)}")
    except Exception as e:
        log_test("GET /api/v1/retrieval/documents/{id}/chunks", False, str(e))

    # 8. Semantic Search Endpoint
    try:
        payload = {
            "query": "What embedding model and dimension does Antigravity use?",
            "top_k": 3,
            "rerank": False
        }
        r = client.post("/api/v1/retrieval/search", json=payload)
        results = r.json().get("results", [])
        matched = any(doc_id == hit["document_id"] for hit in results)
        top_score = results[0]["score"] if results else 0
        log_test("POST /api/v1/retrieval/search (Semantic Search)", r.status_code == 200 and matched, f"hits={len(results)}, top_score={top_score:.4f}")
    except Exception as e:
        log_test("POST /api/v1/retrieval/search", False, str(e))

    # 9. Semantic Search with Reranking
    try:
        payload = {
            "query": "Which message queue is used for asynchronous ingestion?",
            "top_k": 2,
            "rerank": True
        }
        r = client.post("/api/v1/retrieval/search", json=payload)
        results = r.json().get("results", [])
        log_test("POST /api/v1/retrieval/search (With Reranker)", r.status_code == 200 and len(results) > 0, f"reranked_hits={len(results)}")
    except Exception as e:
        log_test("POST /api/v1/retrieval/search (With Reranker)", False, str(e))

    # 10. Chat Endpoint
    conv_id = None
    try:
        payload = {
            "message": "What is 15 * 8? Use calculate.",
            "max_steps": 3
        }
        r = client.post("/api/v1/chat", json=payload)
        chat_data = r.json()
        conv_id = chat_data.get("conversation_id")
        answer = chat_data.get("answer", "")
        tool_calls = chat_data.get("tool_calls", [])
        log_test("POST /api/v1/chat (Agent Chat Turn)", r.status_code == 200 and bool(answer), f"answer_snippet='{answer[:60]}...', tool_calls={len(tool_calls)}")
    except Exception as e:
        log_test("POST /api/v1/chat", False, str(e))

    # 11. List Conversations
    if conv_id:
        try:
            r = client.get("/api/v1/chat/conversations")
            convs = r.json().get("items", [])
            found = any(c["conversation_id"] == conv_id for c in convs)
            log_test("GET /api/v1/chat/conversations (List Conversations)", r.status_code == 200 and found, f"total={len(convs)}")
        except Exception as e:
            log_test("GET /api/v1/chat/conversations", False, str(e))

        # 12. Get Conversation History
        try:
            r = client.get(f"/api/v1/chat/conversations/{conv_id}")
            history = r.json()
            messages = history.get("messages", [])
            log_test("GET /api/v1/chat/conversations/{id} (Conversation History)", r.status_code == 200 and len(messages) >= 2, f"message_count={len(messages)}")
        except Exception as e:
            log_test("GET /api/v1/chat/conversations/{id}", False, str(e))

        # 13. Delete Conversation
        try:
            r = client.delete(f"/api/v1/chat/conversations/{conv_id}")
            log_test("DELETE /api/v1/chat/conversations/{id}", r.status_code == 204, "conversation deleted")
        except Exception as e:
            log_test("DELETE /api/v1/chat/conversations/{id}", False, str(e))

    # 14. Document Reindex Endpoint
    try:
        r = client.post(f"/api/v1/documents/{doc_id}/reindex")
        log_test("POST /api/v1/documents/{id}/reindex (Re-enqueue)", r.status_code == 202, f"status={r.json().get('status')}")
    except Exception as e:
        log_test("POST /api/v1/documents/{id}/reindex", False, str(e))

    # 15. Delete Document
    try:
        r = client.delete(f"/api/v1/documents/{doc_id}")
        log_test("DELETE /api/v1/documents/{id} (Cascade Delete)", r.status_code == 204, "cleaned up source, vectors, jobs")
    except Exception as e:
        log_test("DELETE /api/v1/documents/{id}", False, str(e))

    print("=" * 60)
    print("Endpoint Verification Finished!")
    print("=" * 60)

if __name__ == "__main__":
    main()
