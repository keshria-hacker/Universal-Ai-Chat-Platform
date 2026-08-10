# Deliverable 23: Refactoring Roadmap
## Universal AI Chat Platform (Nexus) — Refactoring Plan

---

## 1. Executive Summary

**Refactoring Roadmap** — Prioritized, sequenced plan to transform the codebase from **current state (C+)** to **production-grade (A-)** over **10 sprints (20 weeks)**. Based on technical debt audit, architectural analysis, and open source readiness gaps.

| Phase | Focus | Sprints | Key Outcomes |
|-------|-------|---------|--------------|
| **1. Foundation** | Tests, Observability, Silent Failures | 1-2 | 60% coverage, structured logs, error propagation |
| **2. Reliability** | Retries, Circuit Breakers, Health, Idempotency | 3-4 | Production-ready reliability patterns |
| **3. Operations** | Cost Tracking, Config Hot-Reload, Provider Metrics | 5 | Operational maturity |
| **4. Frontend** | Accessibility, Mobile, E2E, Onboarding | 6-7 | WCAG AA, mobile UX, automated journeys |
| **5. Release & Security** | Automation, Containers, SBOM, Signing | 8 | Release pipeline, supply chain security |
| **6. Open Source** | Community, Governance, Docs, Branding | 9-10 | Launch-ready open source project |

---

## 2. Phase 1: Foundation (Sprints 1-2)

### Sprint 1: Test Infrastructure & Silent Failures
**Goal:** Establish test foundation, fix data-loss bugs

| Task | Owner | Hours | Deliverable |
|------|-------|-------|-------------|
| Fix 4 silent failures (skills/router, rag, websearch, model_discovery) | Backend | 4 | Error propagation, no swallowed exceptions |
| Add pytest-asyncio, factory-boy, faker, pytest-mock | Backend | 2 | Test deps in pyproject.toml |
| Create conftest.py with async fixtures (test_db, client, auth_headers) | Backend | 4 | Reusable test infrastructure |
| Add test database (SQLite :memory:) with transaction rollback | Backend | 3 | Isolated, fast tests |
| Configure coverage gate at 30% (incremental) | Backend | 1 | CI passes |

**Exit Criteria:** All silent failures fixed, test infra ready, CI green at 30% coverage

### Sprint 2: Core Module Unit Tests
**Goal:** 60% coverage on critical paths

| Task | Owner | Hours | Target Coverage |
|------|-------|-------|-----------------|
| api.py — 25 tests (all endpoints: success, auth, validation, errors) | Backend | 24 | 65% |
| auth.py — 15 tests (login, register, tokens, password reset) | Backend | 12 | 80% |
| database.py — 10 tests (session, engine, WAL, pool) | Backend | 8 | 70% |
| models.py — 15 tests (CRUD, relationships, hybrid props) | Backend | 12 | 60% |
| schemas.py — 10 tests (validation, edge cases) | Backend | 6 | 80% |

**Exit Criteria:** 60% overall coverage, all critical paths tested

---

## 3. Phase 2: Reliability (Sprints 3-4)

### Sprint 3: Resilience Patterns
**Goal:** Production-grade error handling for external calls

| Task | Owner | Hours | Deliverable |
|------|-------|-------|-------------|
| Add tenacity retry to BaseProvider.stream_chat (3×, exp backoff) | Backend | 4 | Transient failure handling |
| Add tenacity retry to BaseProvider.list_models (2×) | Backend | 2 | Model discovery resilience |
| Add tenacity retry to websearch.py (2×) | Backend | 2 | Search resilience |
| Add pybreaker circuit breaker per provider (5 failures, 60s reset) | Backend | 8 | Cascade prevention |
| Add circuit breaker fallback to alternative providers | Backend | 4 | Graceful degradation |

**Exit Criteria:** Provider failures don't cascade, retries with backoff, circuit breakers active

### Sprint 4: Operational Reliability
**Goal:** Idempotency, health checks, observability

| Task | Owner | Hours | Deliverable |
|------|-------|-------|-------------|
| Add Idempotency-Key middleware (Redis, 24h TTL) | Backend | 8 | Duplicate prevention |
| Apply to POST /chats, POST /chat/stream, POST /files | Backend | 4 | Protected endpoints |
| Enhance /health with dependency checks (DB, ChromaDB, Redis, providers) | Backend | 4 | K8s-ready health |
| Add structured JSON logging (python-json-logger) | Backend | 4 | Observable logs |
| Add Prometheus metrics (request latency, errors, provider latency) | Backend | 4 | Metrics exposition |
| Add request/response logging middleware | Backend | 4 | Debugging support |

**Exit Criteria:** Idempotent writes, comprehensive health, structured logs + metrics

---

## 4. Phase 3: Operations (Sprint 5)

### Sprint 5: Cost Tracking & Config Maturity
**Goal:** Business metrics, zero-downtime config

| Task | Owner | Hours | Deliverable |
|------|-------|-------|-------------|
| Add UsageLog model (user, provider, model, tokens, cost, timestamp) | Backend | 4 | Cost data model |
| Add MODEL_PRICING config (per 1M tokens input/output) | Backend | 2 | Pricing table |
| Instrument provider calls to log usage + calculate cost | Backend | 4 | Automatic tracking |
| Add GET /api/usage (daily breakdown) + GET /api/usage/summary | Backend | 4 | Usage API |
| Implement hot reload for safe settings (LOG_LEVEL, rate limits, RAG) | Backend | 6 | Zero-downtime config |
| Add config drift detector (baseline + periodic check + alert) | Backend | 4 | Config integrity |
| Add provider health metrics to /providers endpoint (latency, error rate) | Backend | 4 | Provider observability |

**Exit Criteria:** Cost tracking live, config hot-reload works, provider metrics visible

---

## 5. Phase 4: Frontend Excellence (Sprints 6-7)

### Sprint 6: Accessibility & Mobile (WCAG 2.2 AA)
**Goal:** Inclusive, mobile-first experience

| Task | Owner | Hours | Deliverable |
|------|-------|-------|-------------|
| Add ARIA landmarks to index.html (main, nav, header, heading hierarchy) | Frontend | 3 | Semantic structure |
| Implement accessible combobox for model/provider selectors (ARIA 1.2) | Frontend | 8 | Keyboard + screen reader |
| Add focus management for sidebar, modals, toasts (focus trap) | Frontend | 6 | Keyboard navigation |
| Fix color contrast failures (muted text, focus rings) | Frontend | 2 | WCAG AA contrast |
| Add visible focus styles for all interactive elements | Frontend | 3 | Focus visibility |
| Mobile sidebar drawer (slide-in overlay, touch targets 44px) | Frontend | 6 | Mobile UX |
| Fix virtual keyboard overlap on chat input | Frontend | 2 | iOS/Android input |
| Add reduced-motion support (prefers-reduced-motion) | Frontend | 2 | Motion sensitivity |

**Exit Criteria:** WCAG 2.2 AA compliant, mobile usable, keyboard navigable

### Sprint 7: E2E Tests & Onboarding
**Goal:** Automated critical journeys, new user activation

| Task | Owner | Hours | Deliverable |
|------|-------|-------|-------------|
| Set up Playwright with CI integration | Frontend | 4 | E2E infrastructure |
| Journey 1: New user → register → add key → first chat | Frontend | 6 | Critical path |
| Journey 2: Existing user → login → continue chat | Frontend | 4 | Return user |
| Journey 3: Upload PDF → ask questions (RAG) | Frontend | 6 | RAG flow |
| Journey 4: Switch providers mid-chat | Frontend | 3 | Provider switching |
| Journey 5: Settings → theme, keys, connection | Frontend | 4 | Settings flow |
| Implement onboarding flow (welcome → add key → first chat → features) | Frontend | 6 | Activation |
| Raise coverage gate to 60% | Backend | 1 | Quality gate |

**Exit Criteria:** 5 E2E journeys passing in CI, onboarding complete, 60% coverage

---

## 6. Phase 5: Release & Supply Chain (Sprint 8)

### Sprint 8: Automation & Container Security
**Goal:** One-click releases, secure supply chain

| Task | Owner | Hours | Deliverable |
|------|-------|-------|-------------|
| Create release workflow (version bump, changelog, Docker push, sign, GitHub Release) | DevOps | 8 | Automated releases |
| Add dependabot.yml (pip, github-actions, docker) with grouping | DevOps | 1 | Auto-updates |
| Configure multi-arch Docker build (amd64, arm64) with Buildx | DevOps | 2 | Multi-platform images |
| Add Trivy container scan to CI (SARIF upload to GitHub) | DevOps | 2 | Vulnerability scanning |
| Add Cosign signing + SBOM (Syft) to release workflow | DevOps | 3 | Supply chain integrity |
| Add requirements.lock with hashes (uv pip compile) | DevOps | 1 | Reproducible builds |
| Pin base images by digest in Dockerfile | DevOps | 1 | Build reproducibility |
| Create docker-compose.yml for local development | DevOps | 1 | Local parity |

**Exit Criteria:** Release workflow works, multi-arch images signed, Trivy clean, lockfile exists

---

## 7. Phase 6: Open Source Launch (Sprints 9-10)

### Sprint 9: Community Infrastructure
**Goal:** Governance, contribution, security

| Task | Owner | Hours | Deliverable |
|------|-------|-------|-------------|
| Add LICENSE (MIT) + NOTICE (AGPL/GPL attribution) | Legal | 1 | Licensing |
| Add license headers to all source files | Backend/Frontend | 1 | Compliance |
| Create CODE_OF_CONDUCT.md (Contributor Covenant) | Community | 1 | Conduct |
| Create CONTRIBUTING.md (setup, style, PR process, good first issues) | Community | 2 | Contribution guide |
| Create SECURITY.md (vuln reporting, supported versions) | Security | 1 | Security policy |
| Create GOVERNANCE.md (roles, RFC process, release cadence) | Community | 2 | Governance |
| Add issue templates (bug, feature, security) | Community | 1 | Issue triage |
| Add PR template with checklist | Community | 1 | PR quality |
| Add CODEOWNERS | Community | 1 | Review routing |
| Enable GitHub Discussions (Announcements, Q&A, Ideas, Showcase) | Community | 1 | Community channels |
| Configure branch protection (PR required, checks required, linear history) | DevOps | 1 | Branch policy |
| Add repository topics, description, website URL | DevOps | 1 | Discoverability |

**Exit Criteria:** All community files present, Discussions active, branch protected

### Sprint 10: Documentation & Branding
**Goal:** Professional presentation, user/developer guides

| Task | Owner | Hours | Deliverable |
|------|-------|-------|-------------|
| Set up MkDocs Material documentation site | Docs | 4 | docs.nexus.example.com |
| Write deployment guides (Docker, K8s, systemd, reverse proxy, SSL, backup) | Docs | 8 | Deployment docs |
| Write user guides (getting started, API keys, chat, RAG, skills, web search) | Docs | 8 | User docs |
| Write developer guide (setup, testing, adding providers, skills, extractors) | Docs | 8 | Dev docs |
| Enhance OpenAPI docs on all endpoints (summary, description, examples) | Backend | 4 | API reference |
| Create architecture diagrams (Mermaid: system, data flow, sequence) | Arch | 4 | Architecture docs |
| Write ADRs (8 records: FastAPI, SQLite, LiteLLM, ChromaDB, Fernet, SSE, Vanilla JS, Skills) | Arch | 4 | Decision records |
| Create branding assets (logo SVG, screenshots, social cards) | Design | 8 | Visual identity |
| Add FUNDING.yml + SPONSORS.md | Community | 1 | Funding |
| Create CHANGELOG.md (Keep a Changelog format) | Community | 1 | Release history |
| Raise coverage gate to 80% | Backend | 1 | Quality gate |

**Exit Criteria:** Documentation site live, all guides complete, branding ready, 80% coverage

---

## 8. Resource Allocation

### 8.1 Team Composition (Recommended)
| Role | Sprint 1-2 | Sprint 3-4 | Sprint 5 | Sprint 6-7 | Sprint 8 | Sprint 9-10 |
|------|------------|------------|----------|------------|----------|-------------|
| Backend Engineer | 2 | 2 | 1 | 0.5 | 0.5 | 0.5 |
| Frontend Engineer | 0.5 | 0.5 | 0 | 2 | 0 | 0 |
| DevOps Engineer | 0.5 | 0.5 | 0.5 | 0.5 | 1 | 1 |
| Technical Writer | 0 | 0 | 0 | 0 | 0 | 1 |
| Community Manager | 0 | 0 | 0 | 0 | 0 | 1 |

### 8.2 Total Investment
| Phase | Sprints | Engineer-Weeks | Calendar Weeks |
|-------|---------|----------------|----------------|
| Foundation | 2 | 6 | 2 |
| Reliability | 2 | 6 | 2 |
| Operations | 1 | 3 | 1 |
| Frontend | 2 | 6 | 2 |
| Release/Security | 1 | 3 | 1 |
| Open Source | 2 | 6 | 2 |
| **Total** | **10** | **30** | **20** |

---

## 9. Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Scope creep** | High | Medium | Fixed sprint goals, no mid-sprint additions |
| **Test debt too large** | Medium | High | Incremental coverage gates (30→60→80%) |
| **ML deps break builds** | Medium | Medium | Pin torch CPU, separate ML runtime stage |
| **Accessibility retrofitting hard** | Medium | High | Start early (Sprint 6), component library |
| **Community adoption slow** | Medium | Low | Good first issues, responsive maintainers |
| **AGPL dependency issues** | Low | High | Document clearly, consider pdfplumber alternative |

---

## 10. Success Metrics

### 10.1 Sprint-Level Gates
| Sprint | Must Pass |
|--------|-----------|
| 1 | Silent failures fixed, test infra works, CI green |
| 2 | 60% coverage, core modules tested |
| 3 | Retries + circuit breakers functional |
| 4 | Idempotency, health checks, structured logs + metrics |
| 5 | Cost tracking API, hot reload, provider metrics |
| 6 | WCAG AA audit passes, mobile works |
| 7 | 5 E2E journeys pass, onboarding complete |
| 8 | Release workflow works, Trivy clean, multi-arch signed |
| 9 | All community files, branch protection, Discussions |
| 10 | Docs site live, 80% coverage, branding complete |

### 10.2 Launch Targets (Post-Sprint 10)
| Metric | Target |
|--------|--------|
| **Test Coverage** | ≥ 80% |
| **WCAG Compliance** | AA |
| **E2E Coverage** | 5 critical journeys |
| **Release Frequency** | Monthly minor |
| **MTTR** | < 30 min (with observability) |
| **Deploy Time** | < 10 min (CI/CD) |
| **Image Size** | < 1.5 GB (optimized) |
| **Security Score** | A (GitHub, Trivy) |
| **Community Health** | 90%+ (OSI) |

---

## 11. Conclusion

This roadmap transforms Nexus from a **well-architected prototype** to a **production-grade, open source-ready platform** in 20 weeks. The sequence is deliberate: **foundation → reliability → operations → frontend → release → community**. Each phase unlocks the next. The architecture is sound — the work is **operational maturity**.

**Start Sprint 1 Monday.** Fix silent failures first — they're the only bugs that lose data.

---

*Generated as part of exhaustive repository audit — Deliverable 23 of 26*