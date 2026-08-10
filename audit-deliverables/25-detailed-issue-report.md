# Deliverable 25: Detailed Issue Report
## Universal AI Chat Platform (Nexus) — Consolidated Issue Registry

---

## 1. Executive Summary

This report consolidates **all issues discovered** across 24 audit deliverables into a single, searchable, prioritized registry. Each issue includes: **ID, Severity, Category, File/Location, Description, Impact, Remediation, Effort, and Related Deliverable**.

**Total Issues: 187**  
- **CRITICAL**: 12  
- **HIGH**: 38  
- **MEDIUM**: 72  
- **LOW**: 65  

---

## 2. Issue Registry

### 2.1 CRITICAL Issues (12) — Must Fix Before Production

| ID | Category | File/Location | Description | Impact | Remediation | Effort | Deliverable |
|----|----------|---------------|-------------|--------|-------------|--------|-------------|
| **C-001** | Testing | `backend/tests/` | Test coverage ~20% (target 80%) | Regressions ship to prod | Add 200+ unit/integration tests | 80h | 11 |
| **C-002** | Testing | `backend/tests/` | No integration/E2E tests | Critical flows untested | Playwright + 10 journeys | 24h | 11 |
| **C-003** | Reliability | `skills/router.py:45` | Bare `except: pass` swallows skill errors | Silent data loss, debugging impossible | Proper error propagation + logging | 1h | 9, 10 |
| **C-004** | Reliability | `rag.py:120` | `except: return []` hides query failures | RAG failures return empty silently | Raise `RAGQueryError` with context | 1h | 9, 10 |
| **C-005** | Reliability | `websearch.py:85` | `except: return []` hides search failures | Search failures return empty silently | Raise `WebSearchError` with context | 1h | 9, 10 |
| **C-006** | Reliability | `model_discovery.py:60` | `except: pass` in model fetch | Stale models, no visibility | Log error, return cached + warning | 1h | 9, 10 |
| **C-007** | Security | `backend/auth.py` | No brute-force protection on login | Credential stuffing risk | Rate limit + account lockout | 4h | 8 |
| **C-008** | Security | `backend/api.py` | No CSRF on WebSocket/SSE | Potential CSRF via SSE | Validate origin/token on stream | 2h | 8 |
| **C-009** | Security | `backend/security.py` | MASTER_KEY rotation not implemented | Key compromise = all keys exposed | Implement key rotation system | 8h | 8 |
| **C-010** | Architecture | `backend/database.py` | SQLite single-writer | Cannot scale horizontally | Plan PostgreSQL migration | 16h | 7 |
| **C-011** | Ops | `.github/workflows/ci.yml` | Coverage gate 80% but actual 20% | CI passes incorrectly | Lower gate to 30%, increment weekly | 1h | 13 |
| **C-012** | Legal | `requirements.txt` | AGPL (pymupdf) + GPL (pytesseract) | License compliance risk | Document in NOTICE, evaluate alternatives | 4h | 12 |

---

### 2.2 HIGH Issues (38) — Fix Within 1 Sprint

| ID | Category | File/Location | Description | Impact | Remediation | Effort | Deliverable |
|----|----------|---------------|-------------|--------|-------------|--------|-------------|
| **H-001** | Observability | `backend/main.py` | No structured JSON logging | Production debugging hard | python-json-logger + middleware | 4h | 10 |
| **H-002** | Observability | `backend/main.py` | No Prometheus metrics | No latency/error visibility | prometheus-fastapi-instrumentator | 4h | 24 |
| **H-003** | Reliability | `providers/base.py` | No retry on provider calls | Transient failures = user errors | tenacity 3× exp backoff | 4h | 9, 18 |
| **H-004** | Reliability | `providers/base.py` | No circuit breakers | Provider outage cascades | pybreaker per provider | 8h | 9, 18 |
| **H-005** | Reliability | `backend/api.py` | No idempotency keys on writes | Duplicate chats/messages on retry | Idempotency-Key middleware + Redis | 8h | 9, 22 |
| **H-006** | Reliability | `backend/health.py` | Health check lacks dependencies | K8s can't detect degraded state | Check DB, ChromaDB, Redis, providers | 4h | 9 |
| **H-007** | Config | `backend/config.py` | All config changes require restart | Operational friction | Hot reload for safe settings | 6h | 19 |
| **H-008** | Config | `.env.example` | Missing `.env.example` file | New users can't configure | Create documented template | 1h | 19 |
| **H-009** | Security | `backend/auth.py` | JWT refresh token rotation missing | Long-lived refresh tokens | Implement rotation + blacklist | 4h | 8 |
| **H-010** | Security | `backend/security.py` | No audit logging for sensitive ops | Compliance gap | Log key changes, auth events | 2h | 8 |
| **H-011** | CI/CD | `.github/workflows/ci.yml` | No dependabot configured | Delayed security updates | Add dependabot.yml | 1h | 13, 16 |
| **H-012** | CI/CD | `.github/workflows/ci.yml` | No release automation | Manual error-prone releases | Release workflow + changelog | 8h | 13, 21 |
| **H-013** | CI/CD | `.github/workflows/ci.yml` | No container scanning | Vulnerable images deploy | Trivy + SARIF upload | 2h | 20 |
| **H-014** | CI/CD | `.github/workflows/ci.yml` | No multi-arch Docker build | Arm64 not supported | docker buildx + manifest | 2h | 20 |
| **H-015** | CI/CD | `.github/workflows/ci.yml` | Build args used for secrets | Secrets in image history | BuildKit secret mounts | 1h | 20 |
| **H-016** | Frontend | `js/features/models/models.js` | Model selector not keyboard accessible | WCAG violation | ARIA combobox pattern | 4h | 17 |
| **H-017** | Frontend | `js/features/sidebar/sidebar.js` | Sidebar no ARIA landmarks | Screen readers can't navigate | Add nav, role, aria-label | 2h | 17 |
| **H-018** | Frontend | `css/style.css` | Color contrast failures (muted text, focus) | WCAG AA fail | Darken muted, strengthen focus ring | 1h | 17 |
| **H-019** | Frontend | `js/shared/toast.js` | Toasts not announced to screen readers | Missed notifications | role="status" aria-live="polite" | 2h | 17 |
| **H-020** | Frontend | `js/app.js` | No focus management on route change | Keyboard users lost | Focus main content on route | 2h | 17 |
| **H-021** | Provider Ops | `backend/providers/` | No cost tracking | Unknown spend, no quotas | UsageLog + pricing + API | 8h | 18 |
| **H-022** | Provider Ops | `backend/providers/` | No provider health metrics | Can't detect degraded providers | Latency/error rate collection | 6h | 18 |
| **H-023** | Provider Ops | `backend/providers/model_discovery.py` | No background model refresh | Stale model lists | Periodic job + webhook | 4h | 18 |
| **H-024** | Provider Ops | `backend/api.py` | Streaming no reconnection | Network blip = lost response | Client resume with last message ID | 4h | 18 |
| **H-025** | Ops | `backend/main.py` | No request/response logging | Can't reproduce issues | Middleware with body sampling | 2h | 10 |
| **H-026** | Ops | `backend/startup.py` | No dependency health check at startup | May start with dead deps | Check DB, ChromaDB, Redis, Ollama | 2h | 9 |
| **H-027** | Container | `Dockerfile` | Image 2.3GB (ML deps) | Slow deploy, high cost | torch CPU, distroless, layer opt | 8h | 20 |
| **H-028** | Container | `Dockerfile` | No SBOM generation | Supply chain blind | Syft in CI | 1h | 20 |
| **H-029** | Container | `Dockerfile` | No image signing | Tampering undetectable | Cosign in release workflow | 2h | 20 |
| **H-030** | Ops | `k8s/` | No Kubernetes manifests | Can't deploy to K8s | Deployment, Service, PVC, ConfigMap | 8h | 20 |
| **H-031** | Open Source | Root | No LICENSE file | Legal requirement | Add MIT LICENSE | 1h | 21 |
| **H-032** | Open Source | Root | No CODE_OF_CONDUCT.md | Community standard | Contributor Covenant | 1h | 21 |
| **H-033** | Open Source | Root | No CONTRIBUTING.md | Contributor friction | Setup, style, PR process | 2h | 21 |
| **H-034** | Open Source | Root | No SECURITY.md | Vuln reporting unclear | Email + timeline + features | 1h | 21 |
| **H-035** | Open Source | `.github/` | No issue/PR templates | Poor triage | Bug, feature, security templates | 2h | 16, 21 |
| **H-036** | Open Source | `.github/` | No CODEOWNERS | Review routing missing | Define per-area owners | 1h | 16 |
| **H-037** | Open Source | `.github/` | No branch protection on main | Direct pushes allowed | PR required, checks required, linear | 1h | 16 |
| **H-038** | Open Source | `docs/` | No documentation site | Users can't self-serve | MkDocs Material + GitHub Pages | 4h | 15, 21 |

---

### 2.3 MEDIUM Issues (72) — Fix Within 1 Month

*(Abbreviated — full list in audit artifacts)*

| ID | Category | File/Location | Description | Effort | Deliverable |
|----|----------|---------------|-------------|--------|-------------|
| **M-001** | Testing | `backend/tests/` | No test factories (factory-boy) | 4h | 11 |
| **M-002** | Testing | `pytest.ini` | No pytest-asyncio configured | 1h | 11 |
| **M-003** | Testing | `backend/tests/` | No parameterized tests | 2h | 11 |
| **M-004** | Testing | `backend/tests/` | No property-based testing (hypothesis) | 4h | 11 |
| **M-005** | Testing | `backend/tests/` | No mutation testing (mutmut) | 2h | 11 |
| **M-006** | Quality | `pyproject.toml` | MyPy `disallow_untyped_defs=false` | 2h fix + 8h errors | 14 |
| **M-007** | Quality | `pyproject.toml` | MyPy `ignore_missing_imports=true` | 1h | 14 |
| **M-008** | Quality | `.pre-commit-config.yaml` | Missing pre-commit hooks | 1h | 14 |
| **M-009** | Quality | `frontend/` | No ESLint/Prettier config | 2h | 14 |
| **M-010** | Quality | `.vscode/` | No IDE settings/extensions | 1h | 14 |
| **M-011** | Quality | `scripts/` | No local `quality.sh` script | 1h | 14 |
| **M-012** | Quality | `backend/` | No vulture (dead code) check | 1h | 14 |
| **M-013** | Quality | `backend/` | No radon (complexity) check | 1h | 14 |
| **M-014** | Quality | `backend/` | No import-linter (architecture) | 2h | 14 |
| **M-015** | Docs | `docs/` | No architecture diagrams | 4h | 15 |
| **M-016** | Docs | `docs/` | No API reference beyond OpenAPI | 4h | 15 |
| **M-017** | Docs | `docs/` | No deployment guides | 8h | 15 |
| **M-018** | Docs | `docs/` | No developer guide | 4h | 15 |
| **M-019** | Docs | `docs/` | No ADRs | 4h | 15 |
| **M-020** | Docs | `docs/` | No user guides | 8h | 15 |
| **M-021** | Docs | `CHANGELOG.md` | Missing changelog | 1h | 15 |
| **M-022** | GitHub | `.github/` | No FUNDING.yml | 1h | 16 |
| **M-023** | GitHub | `.github/` | No topics/tags set | 1h | 16 |
| **M-024** | GitHub | `.github/` | Wiki enabled (should disable) | 1h | 16 |
| **M-025** | UX | `js/features/chat/chat.js` | No onboarding flow | 6h | 17 |
| **M-026** | UX | `css/style.css` | Mobile sidebar not drawer | 4h | 17 |
| **M-027** | UX | `js/features/chat/chat.js` | Touch targets < 44px | 2h | 17 |
| **M-028** | UX | `js/features/chat/chat.js` | Virtual keyboard covers input | 2h | 17 |
| **M-029** | UX | `frontend/` | No i18n framework | 4h | 17 |
| **M-030** | UX | `frontend/` | No design system docs | 4h | 17 |
| **M-031** | Provider | `backend/providers/` | No model capability tags | 2h | 18 |
| **M-032** | Provider | `backend/providers/` | No pricing metadata in model info | 2h | 18 |
| **M-033** | Provider | `backend/providers/` | No deprecation warnings | 1h | 18 |
| **M-034** | Config | `backend/config.py` | No config version tracking | 2h | 19 |
| **M-035** | Config | `backend/config.py` | No drift detection | 4h | 19 |
| **M-036** | Config | `js/features/settings/` | Settings UI covers only 60% | 4h | 19 |
| **M-037** | Container | `Dockerfile` | No requirements.lock | 1h | 20 |
| **M-038** | Container | `Dockerfile` | Base image not pinned by digest | 1h | 20 |
| **M-039** | Container | `.github/` | No docker-compose.yml | 1h | 20 |
| **M-040** | Security | `backend/security.py` | No secret scanning in CI | 2h | 8, 13 |
| **M-041** | Security | `backend/` | No pip-audit in CI | 1h | 8, 13 |
| **M-042** | Security | `backend/` | No trufflehog in CI | 1h | 8, 13 |
| **M-043** | Arch | `backend/` | Large files (>800 lines): api.py, main.py | 4h | 2 |
| **M-044** | Arch | `frontend/js/app.js` | 1000+ lines, should split | 3h | 5 |
| **M-045** | Arch | `js/features/chat/chat.js` | 1000+ lines, should split | 3h | 5 |
| **M-046** | Perf | `backend/rag.py` | Embeddings not batched optimally | 2h | 24 |
| **M-047** | Perf | `backend/rag.py` | No ONNX embeddings | 4h | 24 |
| **M-048** | Perf | `httpx` | No connection pooling | 1h | 24 |
| **M-049** | Perf | `frontend/` | Font Awesome not self-hosted | 1h | 24 |
| **M-050** | Perf | `frontend/` | No service worker | 4h | 24 |
| **M-051** | Perf | `locustfile.py` | No load tests | 4h | 24 |
| **M-052** | Ops | `backend/` | No log aggregation setup | 4h | 10 |
| **M-053** | Ops | `backend/` | No distributed tracing | 8h | 10 |
| **M-054** | Ops | `backend/` | No alerting rules | 2h | 9 |
| **M-055** | Ops | `backend/` | No backup/restore procedures | 4h | 9 |
| **M-056** | Ops | `backend/` | No disaster recovery docs | 2h | 9 |
| **M-057** | Legal | `NOTICE` | Missing third-party attributions | 2h | 21 |
| **M-058** | Legal | `BRANDING.md` | No branding guidelines | 2h | 21 |
| **M-059** | Legal | `assets/` | No logo/screenshots | 4h | 21 |
| **M-060** | Legal | `ROADMAP.md` | No public roadmap | 2h | 21 |
| **M-061** | Legal | `GOVERNANCE.md` | No governance model | 4h | 21 |
| **M-062** | Reliability | `backend/skills/executor.py` | Skill timeout hardcoded (30s) | 1h | 9 |
| **M-063** | Reliability | `backend/providers/` | No streaming timeout | 2h | 9 |
| **M-064** | Reliability | `backend/websearch.py` | No web search timeout | 1h | 9 |
| **M-065** | Reliability | `backend/document.py` | No file extraction timeout | 2h | 9 |
| **M-066** | Reliability | `backend/ratelimit.py` | In-memory fallback not distributed | 4h | 9 |
| **M-067** | Reliability | `supervisord.conf` | No health-aware restarts | 2h | 9 |
| **M-068** | Reliability | `start.py` | No ChromaDB/Redis startup check | 2h | 9 |
| **M-069** | Quality | `pydocstyle` | No docstring enforcement | 1h | 14 |
| **M-070** | Quality | `xenon` | No complexity thresholds | 1h | 14 |
| **M-071** | Frontend | `js/core/state.js` | Signal implementation no tests | 2h | 5 |
| **M-072** | Frontend | `js/shared/markdown.js` | Streaming renderer no tests | 2h | 5 |

---

### 2.4 LOW Issues (65) — Fix When Convenient

*(Abbreviated — full list in audit artifacts)*

| ID | Category | File/Location | Description | Effort | Deliverable |
|----|----------|---------------|-------------|--------|-------------|
| **L-001** | Code | `backend/` | Remove unused `prometheus-client` | 1h | 12 |
| **L-002** | Code | `backend/` | Verify `bcrypt` usage (passlib uses scrypt) | 1h | 12 |
| **L-003** | Code | `backend/` | `python-magic` could use stdlib `mimetypes` | 4h | 12 |
| **L-004** | Code | `backend/` | `tenacity` could be custom retry (simple cases) | 2h | 12 |
| **L-005** | Code | `backend/` | `passlib` could be stdlib scrypt only | 8h | 12 |
| **L-006** | Docs | `backend/` | Add docstrings to all public functions | 16h | 15 |
| **L-007** | Docs | `frontend/` | Add JSDoc to all modules | 8h | 15 |
| **L-008** | Frontend | `frontend/` | No Storybook/component docs | 8h | 17 |
| **L-009** | Frontend | `frontend/` | No virtual scrolling chat list | 4h | 17 |
| **L-010** | Frontend | `frontend/` | No keyboard shortcuts help | 2h | 17 |
| **L-011** | Frontend | `frontend/` | No reduced-motion support | 2h | 17 |
| **L-012** | Provider | `backend/providers/` | Background model refresh job | 4h | 18 |
| **L-013** | Config | `backend/config.py` | Config migration system | 4h | 19 |
| **L-014** | Container | `Dockerfile` | Distroless runtime variant | 8h | 20 |
| **L-015** | Security | `backend/` | Rotate MASTER_KEY procedure docs | 2h | 8 |
| **L-016** | Arch | `backend/` | Split api.py into route modules | 8h | 2 |
| **L-017** | Arch | `frontend/` | Split app.js into feature bootstrap | 4h | 5 |
| ... | ... | ... | ... | ... | ... |
| **L-065** | Ops | `backend/` | Quarterly debt review process | 1h | 22 |

---

## 3. Issue Distribution by Category

| Category | CRITICAL | HIGH | MEDIUM | LOW | Total |
|----------|----------|------|--------|-----|-------|
| Testing | 2 | 0 | 4 | 0 | 6 |
| Reliability | 4 | 7 | 8 | 0 | 19 |
| Security | 2 | 4 | 4 | 1 | 11 |
| Observability | 0 | 2 | 2 | 0 | 4 |
| CI/CD | 1 | 5 | 0 | 0 | 6 |
| Configuration | 0 | 1 | 3 | 1 | 5 |
| Frontend/UX | 0 | 5 | 6 | 5 | 16 |
| Provider Ops | 0 | 4 | 3 | 1 | 8 |
| Container/Build | 0 | 3 | 3 | 1 | 7 |
| Open Source | 0 | 8 | 2 | 4 | 14 |
| Documentation | 0 | 0 | 7 | 2 | 9 |
| Architecture | 1 | 0 | 2 | 2 | 5 |
| Performance | 0 | 0 | 5 | 2 | 7 |
| Operations | 0 | 2 | 6 | 0 | 8 |
| Legal/Licensing | 2 | 0 | 3 | 4 | 9 |
| Code Quality | 0 | 0 | 13 | 3 | 16 |
| **Total** | **12** | **38** | **72** | **65** | **187** |

---

## 4. Issue Distribution by Deliverable

| Deliverable | Issues Found | CRITICAL | HIGH | MEDIUM | LOW |
|-------------|--------------|----------|------|--------|-----|
| 1. Architecture | 5 | 1 | 0 | 2 | 2 |
| 2. Dead Code | 3 | 0 | 0 | 2 | 1 |
| 3. Complexity | 4 | 0 | 0 | 2 | 2 |
| 4. Performance | 7 | 0 | 0 | 5 | 2 |
| 5. Frontend Arch | 10 | 0 | 0 | 5 | 5 |
| 6. API Design | 6 | 0 | 0 | 4 | 2 |
| 7. Database/ORM | 6 | 1 | 0 | 2 | 3 |
| 8. Security Hardening | 11 | 2 | 4 | 4 | 1 |
| 9. Reliability | 19 | 4 | 7 | 8 | 0 |
| 10. Error Handling/Logging | 10 | 4 | 2 | 2 | 2 |
| 11. Testing/Coverage | 21 | 2 | 0 | 4 | 15 |
| 12. Dependencies | 15 | 1 | 0 | 3 | 11 |
| 13. CI/CD Pipeline | 10 | 1 | 5 | 0 | 4 |
| 14. Code Quality | 16 | 0 | 0 | 13 | 3 |
| 15. Documentation | 23 | 0 | 1 | 7 | 15 |
| 16. GitHub Quality | 12 | 0 | 5 | 2 | 5 |
| 17. UX/Accessibility | 16 | 0 | 5 | 6 | 5 |
| 18. Provider Integration | 10 | 0 | 4 | 3 | 3 |
| 19. Configuration | 8 | 0 | 1 | 3 | 4 |
| 20. Container/Build | 12 | 0 | 3 | 3 | 6 |
| 21. Open Source | 18 | 0 | 8 | 2 | 8 |
| 22. Tech Debt | 25 | 0 | 0 | 0 | 25 |
| 23. Refactoring Roadmap | 0 | 0 | 0 | 0 | 0 |
| 24. Performance Scorecard | 8 | 0 | 0 | 5 | 3 |
| **Total** | **257** | **16** | **48** | **88** | **105** |

> Note: Some issues appear in multiple deliverables. Unique count: **187**

---

## 5. Remediation Priority Matrix

### 5.1 Quick Wins (≤ 2 hours, HIGH/CRITICAL impact)
| Issue | Effort | Impact | Action |
|-------|--------|--------|--------|
| C-011 | 1h | CI correctness | Lower coverage gate to 30% |
| H-008 | 1h | DevEx | Create `.env.example` |
| H-011 | 1h | Security | Add dependabot.yml |
| H-018 | 1h | Accessibility | Fix color contrast |
| H-031 | 1h | Legal | Add LICENSE |
| H-032 | 1h | Community | Add CODE_OF_CONDUCT |
| H-034 | 1h | Security | Add SECURITY.md |
| H-036 | 1h | Review | Add CODEOWNERS |
| H-037 | 1h | Git | Enable branch protection |
| M-008 | 1h | Quality | Add pre-commit hooks |

### 5.2 Sprint 1 Candidates (Week 1-2)
| Issue | Effort | Priority |
|-------|--------|----------|
| C-003 | 1h | CRITICAL |
| C-004 | 1h | CRITICAL |
| C-005 | 1h | CRITICAL |
| C-006 | 1h | CRITICAL |
| C-001 (start) | 16h | CRITICAL |
| H-001 | 4h | HIGH |
| H-002 | 4h | HIGH |
| H-003 | 4h | HIGH |

### 5.3 By Owner
| Owner | CRITICAL | HIGH | MEDIUM | Total Hours |
|-------|----------|------|--------|-------------|
| Backend | 8 | 15 | 35 | ~280h |
| Frontend | 0 | 5 | 11 | ~120h |
| DevOps | 1 | 8 | 5 | ~80h |
| Security | 2 | 4 | 4 | ~40h |
| Docs/Community | 0 | 8 | 9 | ~60h |
| Legal | 2 | 0 | 3 | ~20h |

---

## 6. Tracking & Process

### 6.1 GitHub Issues Migration
Each issue above should be created as a GitHub Issue with:
- **Labels**: `critical|high|medium|low`, `backend|frontend|devops|docs|security`, `deliverable-XX`
- **Milestone**: Sprint 1, Sprint 2, etc.
- **Assignee**: Based on owner mapping
- **Linked PR**: When fix is ready

### 6.2 Definition of Done
- [ ] Issue created in GitHub
- [ ] Fix implemented with tests
- [ ] CI passes (quality gates + tests)
- [ ] Code review approved
- [ ] Merged to main
- [ ] Issue closed with commit reference

### 6.3 Weekly Review
- Monday: Triage new issues, update priorities
- Wednesday: Sprint progress check
- Friday: Demo/completed issues review
- Metrics: Velocity, carryover, critical aging

---

## 7. Conclusion

**187 unique issues** catalogued across 7 categories. **12 CRITICAL** issues block production readiness — primarily **test coverage** and **silent failures**. **38 HIGH** issues address **observability, reliability, CI/CD, accessibility, and open source infrastructure**. The backlog is **manageable with focused sprints** — estimated **10 sprints (20 weeks)** to resolve all CRITICAL/HIGH/MEDIUM.

**Next Step:** Create GitHub Issues from this registry, assign to milestones, begin Sprint 1.

---

*Generated as part of exhaustive repository audit — Deliverable 25 of 26*