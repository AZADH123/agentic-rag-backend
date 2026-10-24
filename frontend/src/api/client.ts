import axios from 'axios';
import type {
  ChatRequest,
  ChatResponse,
  ChunkListResponse,
  ConversationDetailResponse,
  ConversationListResponse,
  DocumentListResponse,
  DocumentReindexResponse,
  DocumentUploadResponse,
  HealthResponse,
  IngestionJobListResponse,
  ReadyResponse,
  SearchRequest,
  SearchResponse,
  ToolListResponse,
} from '../types';

const BASE = import.meta.env.VITE_API_URL || '/api/v1';

export const getApiKey = (): string => {
  return (
    localStorage.getItem('agentic_rag_api_key') ??
    import.meta.env.VITE_API_KEY ??
    'azadh'
  );
};

export const setApiKey = (key: string): void => {
  localStorage.setItem('agentic_rag_api_key', key);
};

export const api = axios.create({
  baseURL: BASE,
  headers: { 'Content-Type': 'application/json' },
});

// Automatically inject X-API-Key header into all outgoing requests
api.interceptors.request.use((config) => {
  const key = getApiKey();
  if (key) {
    config.headers['X-API-Key'] = key;
  }
  return config;
});

// ─── Health ────────────────────────────────────────────────────────────────────

export const getHealth = () => api.get<HealthResponse>('/health').then(r => r.data);
export const getReady = () => api.get<ReadyResponse>('/health/ready').then(r => r.data);

// ─── Documents ─────────────────────────────────────────────────────────────────

export const listDocuments = (limit = 50, offset = 0) =>
  api.get<DocumentListResponse>('/documents', { params: { limit, offset } }).then(r => r.data);

export const getDocument = (id: string) =>
  api.get(`/documents/${id}`).then(r => r.data);

export const uploadDocument = (file: File) => {
  const form = new FormData();
  form.append('file', file);
  return api
    .post<DocumentUploadResponse>('/documents/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then(r => r.data);
};

export const deleteDocument = (id: string) =>
  api.delete(`/documents/${id}`).then(r => r.data);

export const reindexDocument = (id: string) =>
  api.post<DocumentReindexResponse>(`/documents/${id}/reindex`).then(r => r.data);

// ─── Ingestion Jobs ────────────────────────────────────────────────────────────

export const listIngestionJobs = (limit = 50, offset = 0) =>
  api.get<IngestionJobListResponse>('/ingestion-jobs', { params: { limit, offset } }).then(r => r.data);

export const retryIngestionJob = (jobId: string) =>
  api.post(`/ingestion-jobs/${jobId}/retry`).then(r => r.data);

// ─── Chat ──────────────────────────────────────────────────────────────────────

export const sendChat = (req: ChatRequest) =>
  api.post<ChatResponse>('/chat', req).then(r => r.data);

// ─── Conversations ─────────────────────────────────────────────────────────────

export const listConversations = (limit = 50, offset = 0) =>
  api.get<ConversationListResponse>('/chat/conversations', { params: { limit, offset } }).then(r => r.data);

export const getConversation = (id: string) =>
  api.get<ConversationDetailResponse>(`/chat/conversations/${id}`).then(r => r.data);

export const deleteConversation = (id: string) =>
  api.delete(`/chat/conversations/${id}`).then(r => r.data);

// ─── Retrieval ─────────────────────────────────────────────────────────────────

export const searchDocuments = (req: SearchRequest) =>
  api.post<SearchResponse>('/retrieval/search', req).then(r => r.data);

export const listChunks = (documentId: string) =>
  api.get<ChunkListResponse>(`/retrieval/documents/${documentId}/chunks`).then(r => r.data);

// ─── Tools ────────────────────────────────────────────────────────────────────

export const listTools = () =>
  api.get<ToolListResponse>('/tools').then(r => r.data);
