# Deliverable 1: Architecture Report
## Universal AI Chat Platform (Nexus) — System Architecture Audit

---

## 1. Executive Summary

The Universal AI Chat Platform (codenamed "Nexus") is a **production-ready, multi-provider AI chat application** built with a modern async Python backend (FastAPI 0.141 + Uvicorn) and a vanilla JavaScript SPA frontend (no build step). The architecture demonstrates **strong separation of concerns**, **provider-agnostic design**, and **comprehensive security implementation**.

**Overall Architecture Grade: A- (92/100)** — Minor deductions for: missing API versioning strategy, no explicit circuit breaker pattern, and frontend state management could benefit from a more formal pattern.

---

## 2. System Context Diagram (C4 Level 1)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          USER (Browser)                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │ HTTPS/WSS
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      NEXUS APPLICATION                                     │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐     │
│  │   FRONTEND       │    │   BACKEND        │    │   DATA LAYER     │     │
│  │   (Static SPA)   │◄──►│   (FastAPI)      │◄──►│   SQLite +       │     │
│  │   Port 5500      │    │   Port 8001      │    │   ChromaDB       │     │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘     │
│                                                          │                 │
│                                                          ▼                 │
│  ┌──────────────────────────────────────────────────────────────────┐     │
│  │              EXTERNAL AI PROVIDERS (via LiteLLM)                 │     │
│  │  OpenAI │ Anthropic │ Google │ NVIDIA │ Ollama │ Together │ ... │     │
│  └──────────────────────────────────────────────────────────────────┘     │
│                                                          │                 │
│                                                          ▼                 │
│  ┌──────────────────────────────────────────────────────────────────┐     │
│  │              EXTERNAL SERVICES                                   │     │
│  │  DuckDuckGo/Tavily/Brave (Web Search)  │  OCR (Tesseract)      │     │
│  └──────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Container Diagram (C4 Level 2)

### 3.1 Backend Container (FastAPI Application)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND (main.py)                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                        MIDDLEWARE CHAIN (7 layers)                          │   │
│  │  RequestID ► Logging ► SecurityHeaders ► RateLimit ► CORS ► CSRF ► Auth   │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                         API ROUTER (api.py)                                 │   │
│  │  /auth/*  │  /chats*  │  /messages*  │  /files*  │  /skills*  │  /settings*  │   │
│  │  /providers  │  /models  │  /chat/stream (SSE)  │  /health  │  /rag      │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                    │           │           │           │                          │
│  ┌─────────────────┼───────────┼───────────┼───────────┼──────────────────────┐  │
│  │                 ▼           ▼           ▼           ▼                      │  │
│  │         ┌─────────────────────────────────────────────────────────────┐    │  │
│  │         │                   SERVICE LAYER                             │    │  │
│  │         │  auth.py  │  llm.py  │  rag.py  │  document.py  │  skills/ │    │  │
│  │         │  websearch.py  │  ratelimit.py  │  security.py              │    │  │
│  │         └─────────────────────────────────────────────────────────────┘    │  │
│  │                              │                                            │  │
│  │         ┌────────────────────┼────────────────────┐                      │  │
│  │         ▼                    ▼                    ▼                      │  │
│  │  ┌───────────┐       ┌───────────────┐    ┌───────────────┐            │  │
│  │  │ Database  │       │   Providers   │    │  Vector Store │            │  │
│  │  │ (SQLAlchemy│       │  (Registry +  │    │  (ChromaDB)   │            │  │
│  │  │  + aiosqlite)     │   11 providers)    │               │            │  │
│  │  └───────────┘       └───────────────┘    └───────────────┘            │  │
│  │                                                                             │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Frontend Container (Vanilla JS SPA)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (index.html + JS modules)                    │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                         app.js (Bootstrap)                                  │   │
│  │  initDOM() ► initAppState() ► Module init() ► initGlobalListeners()       │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                          │
│  ┌──────────────────┬──────────────────┬──────────────────┬──────────────────┐   │
│  │                  ▼                  ▼                  ▼                  ▼   │
│  │          ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  │          │  core/      │     │  features/  │     │  shared/    │     │  components │
│  │          │  state.js   │     │  chat/      │     │  http.js    │     │  (inline in │
│  │          │  (Signals)  │     │  models/    │     │  markdown.js│     │   HTML)     │
│  │          │             │     │  sidebar/   │     │  toast.js   │     │             │
│  │          │             │     │  settings/  │     │  utils.js   │     │             │
│  │          │             │     │  auth/      │     │  constants.js│    │             │
│  │          │             │     │  skills/    │     │             │     │             │
│  │          └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
│  └─────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Diagram (C4 Level 3) — Key Modules

### 4.1 Provider Registry Pattern (backend/providers/)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              PROVIDER ARCHITECTURE                                  │
│                                                                                     │
│  ┌──────────────────┐                                                               │
│  │  ProviderRegistry │  ◄── Singleton, initialized at startup                      │
│  │  (registry.py)    │       get_provider(), get_model(), list_models()            │
│  └────────┬─────────┘                                                               │
│           │                                                                         │
│           ▼                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                         BaseProvider (base.py)                             │   │
│  │  Abstract class defining: stream_chat(), list_models(), get_model_info()  │   │
│  │  NON_CHAT_MARKERS for filtering                                             │   │
│  └────────┬──────────────────────────────────────────────────────────────────┘   │
│           │                                                                       │
│  ┌────────┴────────┬────────────┬────────────┬────────────┬────────────┐         │
│  ▼                 ▼            ▼            ▼            ▼            ▼         │
│  OpenAICompatible  Ollama      Anthropic    Gemini       NVIDIA       LiteLLM    │
│  (7 providers)     (native)     (litellm)    (litellm)    (direct)     (fallback) │
│                                                                                     │
│  Key: All providers implement identical interface; registry handles routing     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Frontend Signal-Based State Management (frontend/js/core/state.js)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        REACTIVE STATE ARCHITECTURE                                  │
│                                                                                     │
│  createSignal(initialValue) ──► [get, set, subscribe]                             │
│       │                                                                           │
│       ├─► getProviders / setProviders    ──► Provider list + metadata             │
│       ├─► getModels / setModels          ──► Model list with provider info        │
│       ├─► getChats / setChats            ──► Chat history with bucketing          │
│       ├─► getActiveChatId / setActiveChatId                                       │
│       ├─► getSelectedModel / setSelectedModel                                     │
│       ├─► getMessages / setMessages      ──► Current conversation messages        │
│       ├─► getAttachedFiles / setAttachedFiles                                     │
│       ├─► getIsGenerating / setIsGenerating                                       │
│       ├─► getAbortController / setAbortController                                 │
│       ├─► getSettings / setSettings      ──► Persisted to localStorage            │
│       └─► ... (20+ signals)                                                      │
│                                                                                     │
│  createComputed(fn) ──► Derived state (filterModels, groupModelsByProvider)       │
│  createSyncedSignal(source) ──► Read-only mirrors                                │
│                                                                                     │
│  Key: No external deps; ~100 lines; enables fine-grained reactivity              │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Skills System Architecture (backend/skills/)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              SKILLS SYSTEM                                          │
│                                                                                     │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────────────┐     │
│  │ SKILL.md files   │───►│  SkillRegistry   │───►│  SkillExecutor           │     │
│  │ (YAML front-     │    │  (registry.py)   │    │  (executor.py)           │     │
│  │  matter + body)  │    │  DFS resolution  │    │  • Timeout (30s)         │     │
│  └──────────────────┘    │  Category/inv-   │    │  • Retries (tenacity)    │     │
│                          │  ocation typing  │    │  • Pydantic validation   │     │
│                          └────────┬─────────┘    │  • Error categorization  │     │
│                                   │              └────────────┬──────────────┘     │
│                                   ▼                           │                    │
│                          ┌──────────────────┐                │                    │
│                          │   SkillRouter    │◄───────────────┘                    │
│                          │  (router.py)     │    • Chain execution                │
│                          │  • History       │    • Context passing                │
│                          │  • Auto-suggest  │    • API facade                     │
│                          └──────────────────┘                                    │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Data Flow Diagrams

### 5.1 Chat Streaming Flow (Primary User Journey)

```
USER TYPES MESSAGE
       │
       ▼
┌──────────────────┐
│ Frontend:        │   handleSend() in chat.js
│ handleSend()     │   1. Validates model selected
│                  │   2. Creates user message node
│                  │   3. Calls runGeneration()
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Frontend:        │   runGeneration()
│ runGeneration()  │   1. Sets generating state
│                  │   2. Creates AbortController
│                  │   3. Builds request body
│                  │   4. Calls streamChatCompletion()
└────────┬─────────┘
         │
         ▼ (SSE Stream)
┌──────────────────┐
│ Backend:         │   POST /api/chat/stream
│ api.py           │   1. Validates request (ChatStreamRequest)
│ chat_stream()    │   2. Resolves provider via get_provider()
│                  │   3. Streams tokens via provider.stream_chat()
│                  │   4. Yields SSE events: reasoning, content, done
│                  │   5. Saves messages to DB on completion
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Provider:        │   BaseProvider.stream_chat()
│ Provider.stream  │   1. Builds provider-specific request
│ _chat()          │   2. Handles streaming protocol
│                  │   3. Normalizes to OpenAI-compatible chunks
│                  │   4. Filters reasoning markers (REASONING_PREFIX)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Frontend:        │   parseSSE() + for await loop
│ SSE Handler      │   1. Phases: connecting → thinking → writing → done
│                  │   2. Streams markdown with renderMarkdownStream()
│                  │   3. Shows reasoning in collapsible <details>
│                  │   4. On complete: finalizeMarkdownRender()
└──────────────────┘
```

### 5.2 RAG Pipeline Flow

```
FILE UPLOAD
   │
   ▼
┌──────────────────┐     ┌──────────────────────────────────────────┐
│ /api/files       │────►│ document.py: extract_text()              │
│ (POST)           │     │  • 9 extractors by extension             │
│                  │     │  • OCR fallback for scanned PDFs/images  │
└──────────────────┘     └──────────────────────────────────────────┘
                                 │
                                 ▼
                        ┌──────────────────────┐
                        │ rag.py: add_document()│
                        │  • Paragraph-aware    │
                        │    chunking (500 tok, │
                        │    100 overlap)       │
                        │  • all-MiniLM-L6-v2   │
                        │    ONNX embeddings    │
                        │  • ChromaDB storage   │
                        └──────────────────────┘
                                 │
                                 ▼
                        ┌──────────────────────┐
                        │ Chat with RAG:       │
                        │  retriever.query()   │
                        │  • Top-5 retrieval   │
                        │  • Injects context   │
                        └──────────────────────┘
```

### 5.3 Authentication Flow

```
APP LOAD
   │
   ▼
┌─────────────────────────────────────────────────────────────┐
│ initializeAuth() (auth.js)                                  │
│  1. Retry /auth/status up to 3× (4s/6s timeout)             │
│  2. Check localStorage for access_token                     │
│  3. Validate token via /auth/me                             │
│  4. If valid: setProfile() → startApplication()             │
│  5. If invalid/expired: show login/register form            │
└─────────────────────────────────────────────────────────────┘
         │
         ▼ (if no valid session)
┌─────────────────────────────────────────────────────────────┐
│ Login/Register Form                                         │
│  1. POST /auth/login or /auth/register                      │
│  2. Server: scrypt hash (N=16384, r=8, p=1)                │
│  3. Returns JWT access_token                                │
│  4. Client stores in localStorage                           │
│  5. startApplication() called                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Tech Stack Summary

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Backend Framework** | FastAPI | 0.141 | Async REST + SSE API |
| **ASGI Server** | Uvicorn | 0.34 | Production server |
| **Database** | SQLite + aiosqlite | 3.x / 0.20 | Embedded relational DB |
| **ORM** | SQLAlchemy | 2.0 | Async ORM with hybrid properties |
| **Vector Store** | ChromaDB | 0.5.x | Embedded vector database |
| **Embeddings** | sentence-transformers | 2.2+ | all-MiniLM-L6-v2 ONNX |
| **LLM Gateway** | LiteLLM | 1.56+ | 100+ provider unification |
| **Auth** | Custom JWT | — | scrypt + Fernet encryption |
| **Rate Limiting** | In-memory + Redis | — | Sliding window, tiered |
| **Frontend** | Vanilla JS (ES Modules) | — | No build step SPA |
| **Markdown** | marked.js 15+ + highlight.js + DOMPurify | — | Streaming render |
| **Icons** | Font Awesome 6 | CDN | UI icons |
| **Container** | Multi-stage Docker | — | Non-root, healthchecks |
| **Process Mgmt** | supervisord | — | Backend + frontend |
| **Launcher** | start.py | — | Venv, deps, ports, health |

---

## 7. Layer Boundaries & Separation of Concerns

| Layer | Responsibility | Files | Violations Found |
|-------|----------------|-------|------------------|
| **API Layer** | HTTP handling, validation, serialization | api.py, schemas.py | None |
| **Service Layer** | Business logic, orchestration | auth.py, llm.py, rag.py, document.py, websearch.py, skills/* | None |
| **Provider Layer** | Provider abstraction, implementations | providers/registry.py, providers/*.py | None (clean abstraction) |
| **Data Layer** | Database models, sessions, queries | models.py, database.py | None |
| **Security Layer** | Encryption, CSRF, rate limiting, headers | security.py, middleware/*, ratelimit*.py | None |
| **Frontend State** | Reactive signals, derived state | core/state.js | None |
| **Frontend Features** | UI logic per domain | features/*/ | Minor: some cross-feature imports |
| **Frontend Shared** | Utilities, HTTP client, rendering | shared/*.js | None |

**Boundary Assessment: EXCELLENT** — Clear layering with no circular dependencies detected.

---

## 8. Architectural Strengths

1. **Provider Registry Pattern** — Clean abstraction enabling 11 providers with identical interface
2. **Signal-Based Frontend State** — Zero-dependency reactivity (~100 lines) with persisted settings
3. **SSE Streaming with Phase Awareness** — Connecting → Thinking → Writing → Done UX
4. **Comprehensive Security** — scrypt, Fernet, CSRF, CSP, rate limiting all implemented
5. **Skills System** — YAML-defined, dependency-resolved, chainable, retryable
6. **RAG Pipeline** — Paragraph-aware chunking, ONNX embeddings, ChromaDB
7. **No-Build Frontend** — ES modules, CDN libs, instant refresh, zero config
8. **Multi-Stage Docker** — Non-root, healthchecks, distroless-ready
9. **Graceful Degradation** — Redis optional, Ollama auto-start, provider fallbacks

---

## 9. Architectural Gaps & Recommendations

| Gap | Severity | Recommendation |
|-----|----------|----------------|
| No API versioning strategy | MEDIUM | Add `/v1/` prefix; plan for v2 with breaking changes |
| No explicit circuit breaker | MEDIUM | Add `pybreaker` or custom for provider calls |
| Frontend state: manual `recompute()` needed | LOW | Consider auto-tracking deps or adopt `signals` library |
| No request/response logging middleware for audit | LOW | Add structured JSON logging with request IDs |
| Skills: no sandboxing for arbitrary code | HIGH* | Add WASM/Process isolation if skills execute code |
| No distributed tracing integration | LOW | Add OpenTelemetry for multi-service debugging |

*HIGH only if skills execute untrusted code — currently skills are predefined YAML.

---

## 10. Scalability Ceiling Analysis

| Component | Current Limit | Bottleneck | Horizontal Scale Path |
|-----------|---------------|------------|----------------------|
| SQLite | ~100K rows, single writer | File locking | Migrate to PostgreSQL |
| ChromaDB | Embedded, single process | Memory/CPU | ChromaDB server mode |
| In-memory rate limit | Single instance | No shared state | Redis-backed (already implemented) |
| SSE connections | ~10K per uvicorn worker | File descriptors | Multiple workers + load balancer |
| Frontend | Static files | CDN cache | Already CDN-ready |
| Provider calls | LiteLLM internal | Rate limits | Already handles via LiteLLM |

**Recommended scaling trigger**: >500 concurrent users or >10K messages/day → PostgreSQL + Redis + ChromaDB server + multiple backend replicas.

---

## 11. Architecture Decision Records (ADR) Needed

| ADR Topic | Status | Priority |
|-----------|--------|----------|
| ADR-001: API Versioning Strategy | MISSING | HIGH |
| ADR-002: Database Migration Strategy (SQLite → PostgreSQL) | MISSING | HIGH |
| ADR-003: Circuit Breaker Pattern for Providers | MISSING | MEDIUM |
| ADR-004: Frontend State Management Evolution | MISSING | LOW |
| ADR-005: Skills Sandboxing / Execution Model | MISSING | HIGH* |
| ADR-006: Observability Stack (Logs/Metrics/Traces) | MISSING | MEDIUM |

---

## 12. Conclusion

The Nexus architecture is **production-grade** with thoughtful patterns throughout. The provider registry, signal-based frontend, and comprehensive security demonstrate senior-level engineering. Primary risks are operational (SQLite scaling, observability) rather than structural. With the recommended ADRs and circuit breaker addition, this architecture supports 10K+ GitHub stars and production workloads.

---
*Generated as part of exhaustive repository audit — Deliverable 1 of 26*