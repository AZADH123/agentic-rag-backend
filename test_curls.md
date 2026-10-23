# Agentic RAG Backend — Complete cURL Testing Guide

**Project:** `agentic-rag-backend`  
**Base URL:** `http://localhost:8000`  
**Environment:** Windows PowerShell  
**Authentication:** `X-API-Key: azadh`

---

## 1. Start the Backend

Open PowerShell terminal 1:

```powershell
cd C:\Users\hp\OneDrive\Desktop\agentic-rag-backend

.\.venv\Scripts\Activate.ps1

uvicorn app.main:app --reload
```

Keep this terminal running.

Open a second PowerShell terminal and execute:

```powershell
$BASE = "http://localhost:8000"
$API_KEY = "azadh"
```

## 2. Health Checks

### Test 1 — Health

```powershell
curl.exe -i "$BASE/api/v1/health"
```

### Test 2 — Readiness

```powershell
curl.exe -i "$BASE/api/v1/health/ready"
```

### Test 3 — Available Agent Tools

```powershell
curl.exe -i "$BASE/api/v1/tools" `
  -H "X-API-Key: $API_KEY"
```

## 3. Document Management

### Test 4 — List Documents

```powershell
curl.exe -i "$BASE/api/v1/documents" `
  -H "X-API-Key: $API_KEY"
```

### Test 5 — Upload a PDF

Change the file path to a PDF that exists on your computer.

```powershell
curl.exe -i -X POST "$BASE/api/v1/documents/upload" `
  -H "X-API-Key: $API_KEY" `
  -F "file=@C:\Users\hp\OneDrive\Desktop\agentic-rag-backend\Mittimeedi_Azadh_AI_ML_Resume.pdf"
```

If the PDF is in another directory, replace the file path accordingly.

### Test 6 — Search Documents Using RAG

```powershell
curl.exe -i -X POST "$BASE/api/v1/retrieval/search" `
  -H "X-API-Key: $API_KEY" `
  -H "Content-Type: application/json" `
  -d '{"query":"What AI and machine learning skills are listed in my resume?","top_k":5}'
```

Expected: relevant text chunks from your indexed resume, with retrieval scores and source metadata if provided by your API.

### Test 7 — List Ingestion Jobs

```powershell
curl.exe -i "$BASE/api/v1/ingestion-jobs" `
  -H "X-API-Key: $API_KEY"
```

Check whether each job is `queued`, `processing`, `completed`, or `failed`, according to your application's status values.

## 4. Agent Chat Tests

### Test 8 — Ask a Resume Question

```powershell
curl.exe -i -X POST "$BASE/api/v1/chat" `
  -H "X-API-Key: $API_KEY" `
  -H "Content-Type: application/json" `
  -d '{"message":"Summarize my resume in five bullet points, covering education, skills, projects, and publications."}'
```

Verify the `answer`, `citations`, `tool_calls`, and `steps_taken` fields in the response.

### Test 9 — Search for Specific Resume Skills

```powershell
curl.exe -i -X POST "$BASE/api/v1/chat" `
  -H "X-API-Key: $API_KEY" `
  -H "Content-Type: application/json" `
  -d '{"message":"What Generative AI, RAG, LangChain, and LangGraph skills are mentioned in my resume?"}'
```

### Test 10 — Calculator Tool Calling

```powershell
curl.exe -i -X POST "$BASE/api/v1/chat" `
  -H "X-API-Key: $API_KEY" `
  -H "Content-Type: application/json" `
  -d '{"message":"Use the calculator tool to calculate 125 multiplied by 48."}'
```

Expected answer: `6000`.

Check that the `tool_calls` array reports the `calculate` tool as successful.

### Test 11 — List Chat Conversations

```powershell
curl.exe -i "$BASE/api/v1/chat/conversations" `
  -H "X-API-Key: $API_KEY"
```

### Test 12 — Get a Specific Conversation

Replace the conversation ID with one returned by your chat endpoint.

```powershell
$CONVERSATION_ID = "conv_01m5m34y77qrbn784m5r2s63g0"

curl.exe -i "$BASE/api/v1/chat/conversations/$CONVERSATION_ID" `
  -H "X-API-Key: $API_KEY"
```

## 5. Reindexing and Deletion

**Warning:** Reindexing can trigger additional processing. Deletion may permanently remove a document or its associated records. Use the correct document ID and understand your application's behavior first.

### Test 13 — Reindex a Document

```powershell
$DOC_ID = "doc_01m5kt3j3czqy2q7h2fb3sjze8"

curl.exe -i -X POST "$BASE/api/v1/documents/$DOC_ID/reindex" `
  -H "X-API-Key: $API_KEY"
```

### Test 14 — Retry an Ingestion Job

Use a job ID that is eligible for retry, normally a failed job.

```powershell
$JOB_ID = "REPLACE_WITH_AN_ELIGIBLE_JOB_ID"

curl.exe -i -X POST "$BASE/api/v1/ingestion-jobs/$JOB_ID/retry" `
  -H "X-API-Key: $API_KEY"
```

### Test 15 — Delete a Document

Run this only when you intentionally want to delete a test document.

```powershell
$DOC_ID = "REPLACE_WITH_A_TEST_DOCUMENT_ID"

curl.exe -i -X DELETE "$BASE/api/v1/documents/$DOC_ID" `
  -H "X-API-Key: $API_KEY"
```

## 6. Authentication and Error Handling

### Test 16 — Missing API Key

```powershell
curl.exe -i "$BASE/api/v1/documents"
```

Expected: `401 Unauthorized` if the endpoint requires API-key authentication.

### Test 17 — Invalid API Key

```powershell
curl.exe -i "$BASE/api/v1/documents" `
  -H "X-API-Key: invalid-key"
```

Expected: `401 Unauthorized` if the endpoint validates the API key as configured.

### Test 18 — Wrong HTTP Method

```powershell
curl.exe -i "$BASE/api/v1/retrieval/search" `
  -H "X-API-Key: $API_KEY"
```

Expected: `405 Method Not Allowed` because retrieval search uses `POST`, not `GET`.

### Test 19 — Invalid JSON Body

```powershell
curl.exe -i -X POST "$BASE/api/v1/chat" `
  -H "X-API-Key: $API_KEY" `
  -H "Content-Type: application/json" `
  -d '{"message":'
```

Expected: a client error such as `400` or `422`, depending on your application's request-validation behavior.

## 7. Optional: View Interactive API Documentation

Open these URLs in your browser:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI schema: http://localhost:8000/openapi.json

These endpoints are available if your FastAPI application has the default documentation routes enabled.

## 8. Expected Test Summary

| Feature | Test |
|---|---|
| Application health | Tests 1–2 |
| Tool registration | Test 3 |
| Document upload and listing | Tests 4–5 |
| Semantic retrieval | Test 6 |
| Background ingestion | Test 7 |
| Resume-based RAG | Tests 8–9 |
| Calculator tool calling | Test 10 |
| Conversation history | Tests 11–12 |
| Reindexing and job retry | Tests 13–14 |
| Document deletion | Test 15 |
| Authentication and HTTP errors | Tests 16–19 |

**Important:** These commands are based on the endpoints identified in the project's run guide and the previously tested API behavior. Confirm endpoint schemas, authentication requirements, and the upload file path against your current code. A test passes only when its actual response matches the expected behavior.