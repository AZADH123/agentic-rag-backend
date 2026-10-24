// ─── Document types ───────────────────────────────────────────────────────────

export interface Document {
  document_id: string;
  filename: string;
  content_type: string;
  file_size_bytes: number;
  content_hash?: string;
  owner_id: string;
  status: DocumentStatus;
  error?: string;
  created_at: string;
  updated_at?: string;
  s3_key?: string;
}

export type DocumentStatus =
  | 'uploaded'
  | 'queued'
  | 'processing'
  | 'indexed'
  | 'failed';

export interface DocumentListResponse {
  items: Document[];
  total: number;
}

export interface DocumentUploadResponse {
  document_id: string;
  job_id: string;
  filename: string;
  status: string;
}

export interface DocumentReindexResponse {
  document_id: string;
  job_id: string;
  status: string;
}

// ─── Ingestion Job types ───────────────────────────────────────────────────────

export interface IngestionJob {
  job_id: string;
  document_id: string;
  status: string;
  attempts: number;
  error?: string;
  created_at: string;
  updated_at?: string;
}

export interface IngestionJobListResponse {
  items: IngestionJob[];
  total: number;
}

// ─── Chat / Conversation types ─────────────────────────────────────────────────

export interface Citation {
  document_id: string;
  chunk_id: string;
  filename?: string;
  page?: number;
  snippet?: string;
}

export interface ToolCallRecord {
  tool_name: string;
  status: string;
  arguments_summary?: string;
  error?: string;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
  max_steps?: number;
}

export interface ChatResponse {
  conversation_id: string;
  answer: string;
  citations: Citation[];
  tool_calls: ToolCallRecord[];
  steps_taken: number;
}

export interface MessageResponse {
  message_id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  citations: Citation[];
  tool_calls: ToolCallRecord[];
  created_at: string;
}

export interface ConversationResponse {
  conversation_id: string;
  title?: string;
  owner_id?: string;
  created_at: string;
  updated_at?: string;
}

export interface ConversationListResponse {
  items: ConversationResponse[];
  total: number;
}

export interface ConversationDetailResponse extends ConversationResponse {
  messages: MessageResponse[];
}

// ─── Retrieval types ───────────────────────────────────────────────────────────

export interface SearchRequest {
  query: string;
  top_k?: number;
  document_ids?: string[];
  filters?: Record<string, unknown>;
  rerank?: boolean;
}

export interface ChunkHit {
  document_id: string;
  chunk_id: string;
  text: string;
  score: number;
  metadata: Record<string, unknown>;
}

export interface SearchResponse {
  query: string;
  results: ChunkHit[];
  total: number;
}

export interface ChunkResponse {
  chunk_id: string;
  document_id: string;
  sequence: number;
  text: string;
  page?: number;
  metadata: Record<string, unknown>;
}

export interface ChunkListResponse {
  document_id: string;
  chunks: ChunkResponse[];
  total: number;
}

// ─── Tools types ───────────────────────────────────────────────────────────────

export interface Tool {
  name: string;
  description?: string;
  input_schema?: Record<string, unknown>;
}

export interface ToolListResponse {
  tools: Tool[];
}

// ─── Health types ──────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
}

export interface ReadyResponse {
  status: string;
  components: Record<string, string>;
}
