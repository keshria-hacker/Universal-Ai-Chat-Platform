# Deliverable 11: Testing & Coverage Report
## Universal AI Chat Platform (Nexus) — Testing Audit

---

## 1. Executive Summary

**Testing Grade: C+ (75/100)** — Test infrastructure exists with **pytest + unittest**, **80% coverage target**, and **CI integration**, but **actual coverage is low** (~30%), **no integration/E2E tests**, **no contract tests**, and **test organization minimal**. The test suite needs significant expansion to meet the 80% mandate.

| Aspect | Score | Status |
|--------|-------|--------|
| Unit Tests | 40/100 | 4 test files, minimal coverage |
| Integration Tests | 20/100 | None for API, DB, providers |
| E2E Tests | 0/100 | Not implemented |
| Coverage Enforcement | 60/100 | Configured but not enforced |
| Test Organization | 50/100 | Flat structure, no fixtures |
| CI Integration | 80/100 | Runs in CI, blocks on failure |
| Test Data Management | 30/100 | No factories, manual setup |
| Flaky Test Handling | 0/100 | No quarantine, no retries |

---

## 2. Current Test Inventory

### 2.1 Test Files Found (`backend/tests/`)
```
backend/tests/
├── test_schemas.py           # 2 tests - Pydantic validation
├── test_auth.py              # 8 tests - Auth flow
├── test_providers.py         # 5 tests - Provider registry
├── test_skills.py            # 6 tests - Skills system
└── conftest.py               # Pytest fixtures (minimal)
```

### 2.2 Test Count Summary
| Module | Tests | Lines Covered | Est. Coverage |
|--------|-------|---------------|---------------|
| `schemas.py` | 2 | ~15 | 10% |
| `auth.py` | 8 | ~80 | 40% |
| `providers/` | 5 | ~60 | 25% |
| `skills/` | 6 | ~50 | 30% |
| `api.py` | 0 | 0 | 0% |
| `database.py` | 0 | 0 | 0% |
| `document.py` | 0 | 0 | 0% |
| `rag.py` | 0 | 0 | 0% |
| `websearch.py` | 0 | 0 | 0% |
| `ratelimit.py` | 0 | 0 | 0% |
| **Total** | **21** | **~200** | **~15-20%** |

---

## 3. Configuration (`pyproject.toml`)

### 3.1 Pytest Config
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short --strict-markers"
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "slow: Slow tests",
]

[tool.coverage.run]
source = ["backend"]
omit = ["backend/tests/*", "backend/main.py"]
branch = true

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
]
fail_under = 80  # ← TARGET NOT MET
```

### 3.2 CI Integration (`.github/workflows/ci.yml`)
```yaml
- name: Run tests
  run: |
    cd backend
    pytest --cov=. --cov-fail-under=80 --cov-report=xml
```

**Status:** ✅ Configured, ❌ Will fail (coverage ~20%)

---

## 4. Test Quality Analysis

### 4.1 Strengths (Existing Tests)
```python
# test_schemas.py - Good AAA pattern
def test_accepts_a_user_message_as_the_final_turn(self):
    request = ChatStreamRequest(
        model="openai::gpt-4o",
        messages=[{"role": "user", "content": "Hello"}],
    )
    self.assertEqual(request.messages[-1].role, "user")

def test_rejects_a_request_without_a_final_user_turn(self):
    with self.assertRaises(ValidationError):
        ChatStreamRequest(messages=[{"role": "assistant", "content": "Hello"}])
```

### 4.2 Weaknesses
| Issue | Example |
|-------|---------|
| **No async test support** | `pytest-asyncio` not configured |
| **No test database** | Tests use real SQLite, no isolation |
| **No mocking strategy** | `unittest.mock` used ad-hoc |
| **No factory/fixture library** | Manual object creation |
| **No parameterized tests** | Repeated test cases |
| **No property-based testing** | `hypothesis` not used |

---

## 5. Missing Test Categories

### 5.1 Unit Tests Needed
| Module | Priority | Test Scenarios |
|--------|----------|----------------|
| `api.py` | CRITICAL | All 30+ endpoints: success, validation, auth, errors |
| `auth.py` | HIGH | Login, register, logout, password reset, token refresh |
| `database.py` | HIGH | Session management, WAL pragmas, connection pooling |
| `document.py` | HIGH | All 9 extractors, OCR fallback, error handling |
| `rag.py` | HIGH | Chunking, embedding, query, add/remove |
| `websearch.py` | MEDIUM | Each provider, fallback, caching |
| `ratelimit.py` | MEDIUM | Tiered limits, Redis fallback, sliding window |
| `skills/executor.py` | MEDIUM | Timeout, retry, validation, error categorization |
| `providers/` | MEDIUM | Each provider streaming, model listing, error mapping |

### 5.2 Integration Tests Needed
| Flow | Priority | Components |
|------|----------|------------|
| **Chat streaming** | CRITICAL | API → Provider → SSE → DB save |
| **File upload + RAG** | HIGH | Upload → Extract → Chunk → Embed → Query |
| **Auth flow** | HIGH | Register → Login → Session → Logout |
| **Provider key save** | HIGH | UI → API → Encrypt → Model refresh |
| **Web search injection** | MEDIUM | Chat → Search → Context → Stream |

### 5.3 E2E Tests Needed
| User Journey | Tool | Priority |
|--------------|------|----------|
| **New user: register → add key → chat** | Playwright | CRITICAL |
| **Existing user: login → continue chat** | Playwright | HIGH |
| **Upload PDF → ask questions (RAG)** | Playwright | HIGH |
| **Switch providers mid-chat** | Playwright | MEDIUM |
| **Settings: theme, keys, connection** | Playwright | MEDIUM |
| **Mobile responsive layout** | Playwright | LOW |

---

## 6. Test Infrastructure Gaps

### 6.1 Missing Dependencies
```toml
# Add to pyproject.toml [project.optional-dependencies]
test = [
    "pytest-asyncio>=0.23",
    "pytest-mock>=3.12",
    "pytest-cov>=4.1",
    "factory-boy>=3.3",      # Test data factories
    "faker>=25.0",            # Fake data generation
    "httpx>=0.27",            # Async test client
    "pytest-playwright>=0.4", # E2E (optional)
    "hypothesis>=6.90",       # Property-based testing
]
```

### 6.2 Fixtures Needed (`conftest.py`)
```python
import pytest
import pytest_asyncio
from httpx import AsyncClient
from backend.main import app
from backend.database import get_session, init_db
from backend.models import User, Chat, Message

@pytest_asyncio.fixture
async def test_db():
    """Create test database, yield session, cleanup."""
    # Use SQLite :memory: or temp file
    # Run migrations
    yield session
    # Cleanup

@pytest_asyncio.fixture
async def client(test_db):
    """Async test client with dependency override."""
    app.dependency_overrides[get_session] = lambda: test_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def test_user():
    return User(username="testuser", password_hash=hash_password("password123"))

@pytest.fixture
def auth_headers(test_user):
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}
```

---

## 7. Coverage Strategy

### 7.1 Current vs Target
| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| **Line Coverage** | ~20% | 80% | 60% |
| **Branch Coverage** | ~15% | 80% | 65% |
| **Function Coverage** | ~25% | 80% | 55% |

### 7.2 Coverage by Module (Estimated)
| Module | Lines | Covered | % |
|--------|-------|---------|---|
| `schemas.py` | 90 | 15 | 17% |
| `auth.py` | 190 | 80 | 42% |
| `api.py` | 520 | 0 | 0% |
| `models.py` | 380 | 0 | 0% |
| `database.py` | 95 | 0 | 0% |
| `providers/` | 1200 | 60 | 5% |
| `skills/` | 800 | 50 | 6% |
| `document.py` | 350 | 0 | 0% |
| `rag.py` | 200 | 0 | 0% |
| `websearch.py` | 180 | 0 | 0% |
| `ratelimit.py` | 110 | 0 | 0% |
| `security.py` | 120 | 0 | 0% |
| `config.py` | 105 | 0 | 0% |

---

## 8. Recommended Test Implementation Plan

### 8.1 Phase 1: Foundation (Week 1)
- [ ] Add `pytest-asyncio`, `pytest-mock`, `factory-boy`, `faker`
- [ ] Create `conftest.py` with async fixtures
- [ ] Set up test database (SQLite `:memory:`)
- [ ] Configure coverage to pass at 30% (incremental)

### 8.2 Phase 2: Core Module Tests (Week 2-3)
- [ ] `api.py` - All endpoints (target: 60% coverage)
- [ ] `auth.py` - Complete flow (target: 80%)
- [ ] `database.py` - Session, engine (target: 70%)
- [ ] `models.py` - CRUD, relationships (target: 60%)

### 8.3 Phase 3: Feature Tests (Week 3-4)
- [ ] `providers/` - Registry, each provider (target: 50%)
- [ ] `skills/` - Registry, executor, router (target: 60%)
- [ ] `document.py` - Extractors (target: 50%)
- [ ] `rag.py` - Full pipeline (target: 50%)
- [ ] `websearch.py` - Providers (target: 50%)

### 8.4 Phase 4: Integration & E2E (Week 4-5)
- [ ] Integration tests for critical flows
- [ ] Playwright E2E for 3 critical journeys
- [ ] Raise coverage gate to 60%

### 8.5 Phase 5: Maturity (Week 5-6)
- [ ] Property-based tests for validators
- [ ] Mutation testing (`mutmut`)
- [ ] Contract tests for API
- [ ] Raise coverage gate to 80%

---

## 9. Test Data Management

### 9.1 Factory Pattern (Recommended)
```python
# tests/factories.py
import factory
from backend.models import User, Chat, Message, ProviderKey

class UserFactory(factory.Factory):
    class Meta:
        model = User
    username = factory.Sequence(lambda n: f"user{n}")
    password_hash = factory.LazyAttribute(lambda _: hash_password("testpass"))

class ChatFactory(factory.Factory):
    class Meta:
        model = Chat
    user = factory.SubFactory(UserFactory)
    title = factory.Faker("sentence", nb_words=4)
    model = "openai::gpt-4o"
```

---

## 10. Flaky Test Prevention

### 10.1 Current: No Handling
| Mechanism | Status |
|-----------|--------|
| Test retries | ❌ |
| Quarantine | ❌ |
| Order randomization | ❌ |
| Parallel isolation | ❌ |

### 10.2 Recommended
```toml
# pyproject.toml
[tool.pytest.ini_options]
# Retry flaky tests
retry_count = 2
retry_delay = 1

# Randomize order to catch dependencies
testpaths = ["tests"]
pytester_random_order = true
```

---

## 11. Conclusion

The testing infrastructure is **configured but hollow** — 21 tests covering ~20% of code. To meet the 80% mandate requires **~200 additional tests** across all modules. The priority is **API endpoint tests** and **integration tests for chat streaming**.

**Immediate Actions:**
1. **Add test dependencies** (`pytest-asyncio`, `factory-boy`, `faker`) (15 min)
2. **Create `conftest.py` with async fixtures** (1 hour)
3. **Write tests for `api.py` endpoints** (target 20 tests, 2 days)
4. **Enable coverage gate at 30%**, increment weekly (config change)

**Investment:** ~2 weeks to reach 60%, ~4 weeks to reach 80%.

---

*Generated as part of exhaustive repository audit — Deliverable 11 of 26*