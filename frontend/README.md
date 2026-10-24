# Agentic RAG Web UI

Modern, high-performance web interface for the **Agentic RAG Backend** built with **React 19**, **Vite**, **TypeScript**, and a custom dark glassmorphic design system.

---

## 🚀 Features

- **📊 System Dashboard (`/dashboard`)**:
  - Live system health monitoring directly from `/api/v1/health/ready` (Postgres, Redis, MinIO, Gemini).
  - Real-time stat cards (total documents, indexed documents, conversations, health status).
  - Quick action links and architecture overview.

- **📄 Document Upload & Management (`/documents`)**:
  - Drag-and-drop file uploader supporting PDF, DOCX, and TXT (up to 20MB).
  - Live upload progress indicator and notification toasts.
  - Interactive document list with status badges (`queued`, `processing`, `indexed`, `failed`).
  - Auto-polling while background ingestion workers process documents.
  - Actions to delete or re-index documents on demand.

- **💬 Agentic Chat Interface (`/chat`, `/chat/:conversationId`)**:
  - Persistent conversation sidebar with creation and deletion of threads.
  - Full multi-turn conversational agent powered by Gemini and FastAPI backend.
  - Optimistic UI updates with instant message bubbles and animated typing indicator.
  - Rich Markdown formatting with syntax-highlighted code blocks, tables, and lists.
  - Interactive **Citation Chips** showing source documents, chunk IDs, and page numbers.
  - **MCP Tool Chips** highlighting every tool invocation executed by the agent (e.g. document retrieval, calculations, weather queries) and steps taken.

- **🔍 Semantic Retrieval Explorer (`/retrieval`)**:
  - Direct semantic search against indexed vector chunks.
  - Adjustable Top-K threshold slider and optional neural reranker toggle.
  - Visual similarity score indicators with progress bars, chunk sequence numbers, and page references.

- **🔧 MCP Tools Directory (`/tools`)**:
  - Live inspection of all Model Context Protocol (MCP) tools registered with the agent.
  - Formatted JSON input schemas and tool capabilities.

---

## 🛠️ Tech Stack

- **Framework**: [React 19](https://react.dev/) + [Vite 6](https://vitejs.dev/)
- **Language**: [TypeScript](https://www.typescriptlang.org/)
- **Routing**: [React Router v7](https://reactrouter.com/)
- **Icons**: [Lucide React](https://lucide.dev/)
- **Markdown & Citations**: [react-markdown](https://github.com/remarkjs/react-markdown) + [remark-gfm](https://github.com/remarkjs/remark-gfm)
- **Notifications**: [react-hot-toast](https://react-hot-toast.com/)
- **Drag & Drop**: [react-dropzone](https://react-dropzone.js.org/)
- **Styling**: Handcrafted responsive CSS design system with deep space theme, glowing accents, and smooth micro-interactions.

---

## 📦 Getting Started

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Run the Development Server
```bash
npm run dev
```
The application will start at `http://localhost:5173`.
Vite is preconfigured with a proxy to forward `/api` requests to your FastAPI backend at `http://localhost:8000`.

### 3. Build for Production
```bash
npm run build
```
Build output is generated into the `frontend/dist` directory.

### 4. Preview Production Build
```bash
npm run preview
```

---

## 🔌 API Client Configuration

The frontend API client is located at `src/api/client.ts`. By default, it uses `/api/v1` through the Vite reverse proxy. You can also specify an external backend URL by adding an `.env` file in the `frontend` folder:

```env
VITE_API_URL=http://localhost:8000/api/v1
```
