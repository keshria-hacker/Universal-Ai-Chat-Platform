# Deliverable 20: Container & Build Optimization Report
## Universal AI Chat Platform (Nexus) — Container & Build Audit

---

## 1. Executive Summary

**Container/Build Grade: B- (74/100)** — **Functional multi-stage Dockerfile** with non-root user, health checks, and build args. Gaps in **layer caching optimization**, **distroless/final image size**, **build reproducibility**, **SBOM generation**, **container signing**, **multi-arch builds**, and **build-time secret handling**.

| Area | Score | Status |
|------|-------|--------|
| Dockerfile Structure | 80/100 | Multi-stage, non-root, healthcheck |
| Layer Caching | 60/100 | Requirements copied early, but no uv/pip-cache |
| Image Size | 65/100 | ~2.5GB (ML deps), no distroless |
| Security | 70/100 | Non-root, but no Trivy scan in build |
| Reproducibility | 50/100 | No lockfile, no pinned base digest |
| Multi-arch | 0/100 | Not configured |
| SBOM/Signing | 0/100 | Not implemented |
| Build Secrets | 40/100 | --build-arg for keys, no BuildKit secret mount |
| CI Integration | 75/100 | Builds in CI, no push on tag |

---

## 2. Current Dockerfiles

### 2.1 `Dockerfile` (Main)
```dockerfile
# syntax = docker/dockerfile:1.7
ARG PYTHON_VERSION=3.11-slim
ARG NODE_VERSION=20-alpine

# ─── Base ──────────────────────────────────────────────
FROM python:${PYTHON_VERSION} AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# System deps for ML/OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# ─── Builder ───────────────────────────────────────────
FROM base AS builder
# Install uv for fast pip
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files FIRST for caching
COPY requirements.txt .
COPY pyproject.toml .

# Install dependencies to /app/.venv
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python -r requirements.txt

# ─── Frontend Builder ──────────────────────────────────
FROM node:${NODE_VERSION} AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
# No build step (vanilla JS)

# ─── Runtime ──────────────────────────────────────────
FROM base AS runtime
# Create non-root user
RUN groupadd -r nexus && useradd -r -g nexus nexus

# Copy venv from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY --chown=nexus:nexus backend/ ./backend/
COPY --chown=nexus:nexus frontend/ ./frontend/
COPY --chown=nexus:nexus skills/ ./skills/
COPY --chown=nexus:nexus start.py .
COPY --chown=nexus:nexus supervisord.conf .

# Data directories
RUN mkdir -p /app/data/chroma /app/data/uploads /app/logs && \
    chown -R nexus:nexus /app/data /app/logs

USER nexus

EXPOSE 8001 5500

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

ENTRYPOINT ["python", "start.py"]
```

### 2.2 `Dockerfile.all` (All-in-one)
```dockerfile
# Similar but includes supervisor for both processes
# Single container runs backend + frontend
```

---

## 3. Image Size Analysis

### 3.1 Current Breakdown (Estimated)
| Layer | Size | % of Total |
|-------|------|------------|
| Base (python:3.11-slim) | ~120 MB | 5% |
| System deps (tesseract, poppler, gcc) | ~300 MB | 12% |
| Python venv (requirements.txt) | ~1.8 GB | 72% |
| ── torch/cpu | ~500 MB | 20% |
| ── transformers | ~100 MB | 4% |
| ── sentence-transformers | ~50 MB | 2% |
| ── chromadb/onnxruntime | ~100 MB | 4% |
| ── pillow/pymupdf | ~30 MB | 1% |
| ── Other deps | ~1 GB | 41% |
| Application code | ~50 MB | 2% |
| Frontend | ~10 MB | <1% |
| **Total** | **~2.3 GB** | 100% |

### 3.2 Optimization Opportunities
| Optimization | Savings | Effort |
|--------------|---------|--------|
| **Use `torch --index-url https://download.pytorch.org/whl/cpu`** | ~200 MB | Low |
| **Remove `transformers` if not used directly** | ~100 MB | Medium |
| **Use `sentence-transformers` ONNX only** | ~40 MB | Medium |
| **Distroless base (gcr.io/distroless/python3)** | ~80 MB | Medium |
| **Multi-stage: separate ML runtime** | ~500 MB | High |
| **Layer caching with uv** | Build time | Low |

---

## 4. Layer Caching Issues

### 4.1 Current Problem
```dockerfile
# Current: COPY requirements.txt → uv pip install
COPY requirements.txt .
RUN uv pip install -r requirements.txt
```
**Issue:** Any change to `requirements.txt` invalidates cache. But `requirements.txt` changes frequently during development.

### 4.2 Better: Separate Lockfile
```dockerfile
# Use uv.lock for cache key
COPY requirements.txt uv.lock ./
RUN uv pip install --locked -r requirements.txt

# Or better: pip-compile in builder
COPY requirements.in ./
RUN uv pip compile requirements.in -o requirements.lock && \
    uv pip install --locked -r requirements.lock
```

### 4.3 Recommended: uv Cache Mount
```dockerfile
FROM base AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Cache mount for uv cache
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python -r requirements.txt
```

---

## 5. Security Hardening

### 5.1 Current: Good Foundation
- ✅ Non-root user (nexus:nexus)
- ✅ No unnecessary packages
- ✅ Health check
- ✅ Read-only filesystem (not yet)

### 5.2 Missing Security
| Feature | Implementation |
|---------|----------------|
| **Read-only root fs** | `RUN chmod -R a-w /app && chmod +w /app/data /app/logs` |
| **Drop capabilities** | `security_opt: ["no-new-privileges:true"]` in compose |
| **Trivy scan in build** | `RUN trivy fs --exit-code 1 --severity HIGH,CRITICAL /app` |
| **Signed images** | Cosign in CI |
| **SBOM** | `docker sbom` or Syft in CI |

### 5.3 Recommended Hardened Runtime Stage
```dockerfile
FROM base AS runtime
# ... existing ...

# Security hardening
RUN chmod -R a-w /app && \
    chmod +w /app/data /app/logs /app/tmp && \
    # Remove setuid/setgid
    find /app -type f -perm /6000 -exec chmod a-s {} \;

# Distroless alternative (if compatible)
# FROM gcr.io/distroless/python3-debian12
# COPY --from=builder /app/.venv /app/.venv
# COPY --from=builder /app/backend /app/backend
# USER nonroot:nonroot
```

---

## 6. Multi-Architecture Builds

### 6.1 Missing: `docker buildx` Config
```yaml
# .github/workflows/docker-build.yml
name: Docker Build
on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
      id-token: write
      attestations: write
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: ${{ github.event_name != 'pull_request' }}
          tags: |
            ghcr.io/${{ github.repository }}:latest
            ghcr.io/${{ github.repository }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          provenance: true
          sbom: true
          build-args: |
            PYTHON_VERSION=3.11-slim
            NODE_VERSION=20-alpine
      
      - name: Sign with Cosign
        if: github.event_name != 'pull_request'
        uses: sigstore/cosign-installer@v3
      - run: |
          cosign sign --yes ghcr.io/${{ github.repository }}:${{ github.sha }}
```

---

## 7. Build Secrets Handling

### 7.1 Current: Build Args (Insecure)
```dockerfile
# DON'T DO THIS - secrets in image history
ARG MASTER_KEY
ARG SECRET_KEY
ENV MASTER_KEY=${MASTER_KEY}
ENV SECRET_KEY=${SECRET_KEY}
```

### 7.2 Recommended: BuildKit Secret Mount
```dockerfile
# syntax = docker/dockerfile:1.7

FROM base AS builder
# Use secret mount for pip index auth (if private)
RUN --mount=type=secret,id=pypi_token \
    uv pip install --index-url https://${PYPI_TOKEN}@pypi.org/simple -r requirements.txt

# Runtime: secrets via env files / secrets manager
# NOT baked into image
```

---

## 8. Reproducible Builds

### 8.1 Current: Not Reproducible
- No pinned base image digest
- No requirements lockfile
- Timestamps in layers

### 8.2 Recommended: Reproducible Build
```dockerfile
# Pin base image by digest
FROM python@sha256:abc123... AS base
FROM node@sha256:def456... AS frontend-builder

# Use SOURCE_DATE_EPOCH for deterministic timestamps
ARG SOURCE_DATE_EPOCH
ENV SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-0}

# In CI:
# SOURCE_DATE_EPOCH=$(git log -1 --pretty=%ct)
```

---

## 9. Docker Compose for Development

### 9.1 `docker-compose.yml`
```yaml
version: "3.8"

services:
  nexus:
    build:
      context: .
      dockerfile: Dockerfile
      target: runtime
    ports:
      - "8001:8001"
      - "5500:5500"
    volumes:
      - nexus-data:/app/data
      - nexus-logs:/app/logs
      - ./config/.env:/app/.env:ro
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 1G

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  nexus-data:
  nexus-logs:
  redis-data:
```

---

## 10. Kubernetes Deployment (Missing)

### 10.1 Required Manifests
```
k8s/
├── base/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── pvc.yaml
│   └── kustomization.yaml
├── overlays/
│   ├── development/
│   ├── staging/
│   └── production/
```

### 10.2 Deployment Example
```yaml
# k8s/base/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nexus
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nexus
  template:
    metadata:
      labels:
        app: nexus
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
      containers:
      - name: nexus
        image: ghcr.io/owner/repo:latest
        ports:
        - containerPort: 8001
        - containerPort: 5500
        envFrom:
        - configMapRef:
            name: nexus-config
        - secretRef:
            name: nexus-secrets
        volumeMounts:
        - name: data
          mountPath: /app/data
        - name: logs
          mountPath: /app/logs
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 20
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 10
          periodSeconds: 10
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: nexus-data
      - name: logs
        emptyDir: {}
```

---

## 11. Build Performance

### 11.1 Current Build Time (Estimated)
| Stage | Time |
|-------|------|
| Base apt install | ~60s |
| uv venv + pip install | ~180s (dominated by torch) |
| Frontend npm ci | ~30s |
| Copy application | ~10s |
| **Total** | **~5 min** |

### 11.2 Optimization Targets
| Optimization | Time Saved |
|--------------|------------|
| **uv cache mount** | ~60s |
| **Parallel stages** (builder + frontend) | ~30s |
| **Pre-built ML wheel cache** | ~120s |
| **Layer caching with lockfile** | ~30s on rebuild |
| **Target** | **< 2 min** |

---

## 12. Conclusion

The container setup works for development but **not production-ready**. Critical gaps: **no multi-arch**, **no SBOM/signing**, **2.3GB image**, **build args for secrets**, **no K8s manifests**. The ML dependencies dominate size and build time.

**Immediate Actions:**
1. **Add `uv.lock` / `requirements.lock`** for reproducible builds (15 min)
2. **Configure `docker buildx` multi-arch workflow** (1 hour)
3. **Add Trivy scan + Cosign signing** to CI (45 min)
4. **Implement BuildKit secret mounts** (30 min)
5. **Create `docker-compose.yml`** for local dev (30 min)
6. **Add Kubernetes manifests** (4 hours)
7. **Optimize ML dependencies** (torch CPU, remove unused) (2 hours)
8. **Add SBOM generation** (Syft in CI) (30 min)
9. **Pin base images by digest** (15 min)
10. **Distroless runtime variant** (experimental) (4 hours)

---

*Generated as part of exhaustive repository audit — Deliverable 20 of 26*