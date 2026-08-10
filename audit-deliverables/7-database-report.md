# Deliverable 7: Database & ORM Report
## Universal AI Chat Platform (Nexus) — Database Audit

---

## 1. Executive Summary

**Database & ORM Grade: A- (90/100)** — Excellent SQLAlchemy 2.0 async usage with proper hybrid properties for encryption, WAL mode optimization, and clean model design. Primary gaps: **missing indexes**, **no migration strategy**, and **soft delete not implemented**.

| Aspect | Score | Notes |
|--------|-------|-------|
| Schema Design | 95/100 | Normalized, proper relationships, hybrid encrypted props |
| ORM Usage | 95/100 | Async 2.0 patterns, session management, no N+1 |
| Indexing | 70/100 | Missing critical indexes on updated_at, chat_id+created_at |
| Migrations | 60/100 | No Alembic, create_all only |
| Constraints | 85/100 | FKs present, some missing unique constraints |
| Connection Management | 90/100 | NullPool for SQLite, proper timeouts |
| Vector Store Coupling | 80/100 | ChromaDB separate, no transaction coordination |
| Soft Delete / Audit | 50/100 | Not implemented |

---

## 2. Schema Analysis (`backend/models.py`)

### 2.1 Entity Relationship Diagram
```
┌─────────────────┐       ┌─────────────────┐
│      User       │       │     Chat        │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │◄──────│ id (PK)         │
│ username (UQ)   │       │ user_id (FK)    │──┐
│ password_hash   │       │ title           │  │
│ created_at      │       │ model           │  │
│ updated_at      │       │ created_at      │  │
└─────────────────┘       │ updated_at      │  │
                          └────────┬────────┘  │
                                   │           │
                    ┌──────────────┼───────────┘
                    ▼              ▼
           ┌──────────────┐ ┌──────────────┐
           │   Message    │ │ UploadedFile │
           ├──────────────┤ ├──────────────┤
           │ id (PK)      │ │ id (PK)      │
           │ chat_id (FK) │ │ chat_id (FK) │
           │ role         │ │ file_id (FK) │
           │ content      │ │ created_at   │
           │ created_at   │ └──────────────┘
           │ response_time│
           └──────────────┘

┌─────────────────┐       ┌─────────────────┐
│  ProviderKey    │       │  AuthSession    │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │
│ user_id (FK)    │       │ user_id (FK)    │
│ provider_id     │       │ session_token   │
│ key_encrypted   │       │ created_at      │
│ created_at      │       │ expires_at      │
└─────────────────┘       └─────────────────┘

┌─────────────────┐
│PasswordResetToken│
├─────────────────┤
│ id (PK)         │
│ user_id (FK)    │
│ token_hash      │
│ created_at      │
│ expires_at      │
│ used            │
└─────────────────┘
```

### 2.2 Model Definitions Summary

| Model | Table | Rows Est. | Key Fields | Relationships |
|-------|-------|-----------|------------|---------------|
| `User` | `users` | 1-K | `username` (UQ), `password_hash` | 1→N Chat, ProviderKey, AuthSession, PasswordResetToken |
| `Chat` | `chats` | 10-K | `user_id` (FK), `model`, `title` | N→1 User, 1→N Message, UploadedFile |
| `Message` | `messages` | 100-K+ | `chat_id` (FK), `role`, `content`, `response_time` | N→1 Chat |
| `UploadedFile` | `uploaded_files` | 10-K | `chat_id` (FK), `file_id`, `name`, `size` | N→1 Chat |
| `ProviderKey` | `provider_keys` | 10-K | `user_id` (FK), `provider_id`, `key_encrypted` | N→1 User |
| `AuthSession` | `auth_sessions` | 1-K | `user_id` (FK), `session_token`, `expires_at` | N→1 User |
| `PasswordResetToken` | `password_reset_tokens` | <100 | `user_id` (FK), `token_hash`, `expires_at`, `used` | N→1 User |

### 2.3 Hybrid Encrypted Property (Excellent Pattern)
```python
# models.py: ProviderKey.key_encrypted
class ProviderKey(Base):
    # ... columns ...
    _key_encrypted: Mapped[str] = mapped_column("key_encrypted", String(500))
    
    @hybrid_property
    def key(self) -> str:
        """Decrypt on access."""
        return decrypt_key(self._key_encrypted)
    
    @key.setter
    def key(self, value: str) -> None:
        """Encrypt on set."""
        self._key_encrypted = encrypt_key(value)
    
    @key.expression
    def key(cls):  # For SQL queries (returns encrypted)
        return cls._key_encrypted
```
**Assessment:** ✅ Clean encryption abstraction, prevents accidental plaintext logging.

---

## 3. Index Analysis

### 3.1 Current Indexes (Auto-created)
| Table | Index | Type | Columns |
|-------|-------|------|---------|
| `users` | `ix_users_username` | UNIQUE | `username` |
| `users` | `pk_users` | PK | `id` |
| `chats` | `pk_chats` | PK | `id` |
| `chats` | `ix_chats_user_id` | FK | `user_id` |
| `messages` | `pk_messages` | PK | `id` |
| `messages` | `ix_messages_chat_id` | FK | `chat_id` |
| `uploaded_files` | `pk_uploaded_files` | PK | `id` |
| `uploaded_files` | `ix_uploaded_files_chat_id` | FK | `chat_id` |
| `provider_keys` | `pk_provider_keys` | PK | `id` |
| `provider_keys` | `ix_provider_keys_user_id` | FK | `user_id` |
| `auth_sessions` | `pk_auth_sessions` | PK | `id` |
| `auth_sessions` | `ix_auth_sessions_user_id` | FK | `user_id` |
| `password_reset_tokens` | `pk_password_reset_tokens` | PK | `id` |
| `password_reset_tokens` | `ix_password_reset_tokens_user_id` | FK | `user_id` |

### 3.2 MISSING Critical Indexes

| Table | Missing Index | Query Pattern | Impact |
|-------|---------------|---------------|--------|
| `chats` | `ix_chats_updated_at` | `ORDER BY updated_at DESC LIMIT 100` | Chat list sort O(n log n) → O(log n) |
| `chats` | `ix_chats_user_updated` | `WHERE user_id=? ORDER BY updated_at` | User's chats filtered + sorted |
| `messages` | `ix_messages_chat_created` | `WHERE chat_id=? ORDER BY created_at` | Message loading (composite) |
| `provider_keys` | `ix_provider_keys_user_provider` | `WHERE user_id=? AND provider_id=?` (UQ) | Key lookup, prevent duplicates |
| `auth_sessions` | `ix_auth_sessions_token` | `WHERE session_token=?` (UQ) | Session validation |
| `auth_sessions` | `ix_auth_sessions_expires` | `WHERE expires_at > now()` | Cleanup job |
| `password_reset_tokens` | `ix_password_reset_tokens_token` | `WHERE token_hash=?` (UQ) | Token validation |
| `password_reset_tokens` | `ix_password_reset_tokens_expires` | `WHERE expires_at > now() AND used=0` | Cleanup |

### 3.3 Recommended Index DDL
```sql
-- Chat list performance (HIGH PRIORITY)
CREATE INDEX ix_chats_updated_at ON chats(updated_at DESC);
CREATE INDEX ix_chats_user_updated ON chats(user_id, updated_at DESC);

-- Message loading (HIGH PRIORITY)
CREATE INDEX ix_messages_chat_created ON messages(chat_id, created_at);

-- Provider key uniqueness (MEDIUM)
CREATE UNIQUE INDEX ix_provider_keys_user_provider 
  ON provider_keys(user_id, provider_id);

-- Session lookup (HIGH)
CREATE UNIQUE INDEX ix_auth_sessions_token ON auth_sessions(session_token);
CREATE INDEX ix_auth_sessions_expires ON auth_sessions(expires_at);

-- Reset token lookup (HIGH)
CREATE UNIQUE INDEX ix_password_reset_tokens_token ON password_reset_tokens(token_hash);
CREATE INDEX ix_password_reset_tokens_expires ON password_reset_tokens(expires_at) WHERE used=0;
```

---

## 4. Migration Strategy (MISSING)

### 4.1 Current: `create_all()` Only
```python
# database.py: lifespan
async def lifespan(app):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # No migration tracking, no versioning
```

### 4.2 Required: Alembic Setup
```bash
# 1. Initialize
alembic init migrations

# 2. Configure env.py for async
# 3. Generate initial migration
alembic revision --autogenerate -m "Initial schema"

# 4. Apply
alembic upgrade head
```

### 4.3 Migration Files Needed
| Migration | Description |
|-----------|-------------|
| `001_initial` | All 7 tables with PKs, FKs |
| `002_add_indexes` | All missing indexes from §3.2 |
| `003_soft_delete` | Add `deleted_at` to chats, messages |
| `004_audit_columns` | Add `created_by`, `updated_by` if needed |

---

## 5. Constraint Analysis

### 5.1 Present Constraints
| Table | Constraint | Columns |
|-------|------------|---------|
| `users` | PK | `id` |
| `users` | UNIQUE | `username` |
| `chats` | PK | `id` |
| `chats` | FK | `user_id → users.id` (CASCADE) |
| `messages` | PK | `id` |
| `messages` | FK | `chat_id → chats.id` (CASCADE) |
| `messages` | CHECK | `role IN ('user','assistant','system')` |
| `uploaded_files` | PK | `id` |
| `uploaded_files` | FK | `chat_id → chats.id` (CASCADE) |
| `provider_keys` | PK | `id` |
| `provider_keys` | FK | `user_id → users.id` (CASCADE) |
| `auth_sessions` | PK | `id` |
| `auth_sessions` | FK | `user_id → users.id` (CASCADE) |
| `password_reset_tokens` | PK | `id` |
| `password_reset_tokens` | FK | `user_id → users.id` (CASCADE) |

### 5.2 Missing Constraints
| Table | Constraint | Reason |
|-------|------------|--------|
| `provider_keys` | UNIQUE | `(user_id, provider_id)` — one key per provider per user |
| `auth_sessions` | UNIQUE | `session_token` — prevent collisions |
| `password_reset_tokens` | UNIQUE | `token_hash` — prevent collisions |
| `password_reset_tokens` | CHECK | `used IN (0,1)` — boolean enforcement |
| `messages` | CHECK | `response_time >= 0` — non-negative |

---

## 6. Connection Management (`backend/database.py`)

### 6.1 Current Configuration
```python
engine = create_async_engine(
    f"sqlite+aiosqlite:///{db_path}",
    echo=False,
    poolclass=NullPool,              # ✅ Correct for SQLite
    connect_args={
        "timeout": 30,               # ✅ Busy timeout
        "check_same_thread": False,  # ✅ Allow multi-thread
    },
)

# Session factory
async_session_factory = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False,          # ✅ Prevents lazy load issues
    autoflush=False,                 # ✅ Explicit control
)
```

### 6.2 WAL Pragmas (Applied on Connect)
```python
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA busy_timeout=5000;")
    cursor.execute("PRAGMA cache_size=-32768;")  # 32MB
    cursor.execute("PRAGMA temp_store=MEMORY;")
    cursor.execute("PRAGMA page_size=4096;")
    cursor.close()
```

**Assessment:** ✅ Optimal for SQLite — WAL enables concurrent readers, cache sized appropriately.

---

## 7. Transaction Boundaries

### 7.1 Current Patterns
```python
# Pattern 1: Explicit session (most endpoints)
async with get_session() as session:
    chat = Chat(...)
    session.add(chat)
    await session.commit()
    # ...

# Pattern 2: Streaming with rollback (chat_stream)
async with get_session() as session:
    try:
        async for chunk in provider.stream_chat(...):
            yield chunk
        await session.commit()  # Only on success
    except Exception:
        await session.rollback()
        raise
```

### 7.2 Assessment
| Pattern | Status | Notes |
|---------|--------|-------|
| **Explicit commit/rollback** | ✅ | Clear ownership |
| **No nested transactions** | ✅ | Simpler mental model |
| **Streaming rollback** | ✅ | Prevents partial saves |
| **Session per request** | ✅ | Via dependency injection |
| **Savepoints** | ❌ | Not used (not needed) |

---

## 8. Vector Store Coupling (ChromaDB)

### 8.1 Current Architecture
```
┌─────────────────┐     ┌─────────────────┐
│   SQLite        │     │   ChromaDB      │
│   (metadata)    │     │   (vectors)     │
├─────────────────┤     ├─────────────────┤
│ chats, messages │     │ collections:    │
│ uploaded_files  │     │  - documents    │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────────────────────────────┐
│         rag.py: Retriever               │
│  - query() → chroma.query()             │
│  - add_document() → chroma.add()        │
└─────────────────────────────────────────┘
```

### 8.2 Coupling Issues
| Issue | Severity | Impact |
|-------|----------|--------|
| **No transaction coordination** | MEDIUM | File metadata in SQLite, vectors in ChromaDB — can diverge |
| **No foreign key to ChromaDB** | LOW | `UploadedFile.file_id` not linked to ChromaDB doc ID |
| **ChromaDB in-process** | HIGH | Memory grows unbounded, single process |
| **No backup strategy** | MEDIUM | ChromaDB persistence separate from SQLite |

### 8.3 Recommended Decoupling
```python
# Add to UploadedFile model
class UploadedFile(Base):
    # ...
    chroma_doc_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Link to ChromaDB document for reconciliation
```

---

## 9. Soft Delete & Audit (NOT IMPLEMENTED)

### 9.1 Current: Hard Delete Only
```python
# api.py: delete_chat
await session.delete(chat)
await session.commit()
# CASCADE deletes messages, files
```

### 9.2 Recommended: Soft Delete Pattern
```python
# Add to base model
class BaseModel(Base):
    __abstract__ = True
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    @hybrid_property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

# Query filter
async def get_active_chats(session, user_id):
    return await session.execute(
        select(Chat).where(
            Chat.user_id == user_id,
            Chat.deleted_at.is_(None)
        )
    )
```

### 9.3 Audit Columns (Optional)
```python
created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
updated_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
```

---

## 10. Performance Query Patterns

### 10.1 Verified: No N+1 Queries
```python
# Chat list: single query
chats = await session.execute(
    select(Chat).where(Chat.user_id == user_id).order_by(Chat.updated_at.desc())
)

# Chat with messages: two queries (acceptable)
chat = await session.get(Chat, chat_id)
messages = await session.execute(
    select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at)
)
```

### 10.2 Query Optimization Opportunities
| Query | Current | Optimized |
|-------|---------|-----------|
| Chat list + message count | N+1 if counting | Subquery count |
| Provider keys by user | Index scan | Composite index (added) |
| Session cleanup | Full scan | Index on expires_at |

---

## 11. SQLite → PostgreSQL Migration Readiness

### 11.1 Compatibility Checklist
| Feature | SQLite | PostgreSQL | Migration Effort |
|---------|--------|------------|------------------|
| `DATETIME` | TEXT | TIMESTAMP | Low (SQLAlchemy handles) |
| `Boolean` | INTEGER | BOOLEAN | Low |
| `JSON` | TEXT | JSONB | Medium (query changes) |
| `AUTOINCREMENT` | INTEGER | SERIAL/BIGSERIAL | Low |
| `PRAGMA` | SQLite-only | N/A | Remove |
| `NullPool` | Required | Standard pool | Change pool class |
| `WAL` | SQLite-only | Native MVCC | Remove pragmas |

### 11.2 Migration Steps
1. Add Alembic with PostgreSQL dialect
2. Generate diff migration
3. Test with production data subset
4. Blue-green deploy with read replica
5. Switch traffic

---

## 12. Conclusion

The database layer is **well-designed** with proper async SQLAlchemy 2.0 usage, encryption via hybrid properties, and optimal SQLite configuration. **Critical action items:**

1. **Add missing indexes** (30 min, immediate chat list speedup)
2. **Set up Alembic migrations** (2 hours, enables schema evolution)
3. **Add unique constraints** on provider_keys, auth_sessions (15 min)
4. **Implement soft delete** for chats/messages (4 hours, data safety)
5. **Plan PostgreSQL migration** (1 sprint, scalability)

---

*Generated as part of exhaustive repository audit — Deliverable 7 of 26*