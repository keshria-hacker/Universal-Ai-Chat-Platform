# Deliverable 14: Code Quality Tooling Report
## Universal AI Chat Platform (Nexus) — Code Quality Tooling Audit

---

## 1. Executive Summary

**Code Quality Tooling Grade: B- (76/100)** — **Ruff + MyPy configured** in pyproject.toml with good rule coverage, **pre-commit missing**, **no IDE integration**, **no automated quality gates** beyond CI. Frontend has only basic eslint syntax check.

| Tool | Configured | CI Integrated | Pre-commit | IDE Config |
|------|------------|---------------|------------|------------|
| **Ruff (lint)** | ✅ | ✅ | ❌ | ❌ |
| **Ruff (format)** | ✅ | ⚠️ check only | ❌ | ❌ |
| **MyPy** | ✅ | ✅ | ❌ | ❌ |
| **Bandit** | ✅ | ✅ | ❌ | ❌ |
| **Safety** | ✅ | ✅ | ❌ | ❌ |
| **ESLint (JS)** | ⚠️ syntax only | ✅ | ❌ | ❌ |
| **Prettier** | ❌ | ❌ | ❌ | ❌ |
| **Pre-commit** | ❌ | — | ❌ | — |

---

## 2. Current Configuration (`pyproject.toml`)

### 2.1 Ruff Configuration
```toml
[tool.ruff]
line-length = 100
target-version = "py311"
src = ["backend"]

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "UP",  # pyupgrade
    "C4",  # flake8-comprehensions
    "PL",  # pylint
    "PT",  # flake8-pytest-style
    "T20", # flake8-print
    "ARG", # flake8-unused-arguments
    "PTH", # flake8-pathlib
    "ERA", # eradicate (commented code)
]
ignore = [
    "E501",  # line too long (handled by formatter)
    "PLR0913", # too many arguments
    "PT001", # pytest style (allow unittest)
]
per-file-ignores = {
    "backend/tests/*": ["PLR0913", "S101"],  # assert in tests
    "backend/main.py": ["T201"],  # print allowed in main
}

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "lf"
```

**Assessment:** ✅ Comprehensive rule set, covers security (PT), style, imports, unused code. Missing: `TRY` (try/except), `ASYNC` (async), `RUF` (Ruff-specific).

### 2.2 MyPy Configuration
```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # ← Too permissive
disallow_incomplete_defs = false
check_untyped_defs = true
no_implicit_optional = true
strict_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
ignore_missing_imports = true  # ← Safety gap

[[tool.mypy.overrides]]
module = "backend.*"
disallow_untyped_defs = true   # ← Only for backend modules
```

**Assessment:** ⚠️ `disallow_untyped_defs = false` globally allows untyped functions. `ignore_missing_imports = true` hides real issues. Should be stricter.

### 2.3 Pytest & Coverage
```toml
[tool.pytest.ini_options]
testpaths = ["backend/tests"]
addopts = "-v --tb=short --strict-markers"
markers = ["unit", "integration", "slow"]

[tool.coverage.run]
source = ["backend"]
omit = ["backend/tests/*", "backend/main.py"]
branch = true

[tool.coverage.report]
fail_under = 80
exclude_lines = ["pragma: no cover", "def __repr__", "raise NotImplementedError"]
```

---

## 3. Missing: Pre-commit Hooks

### 3.1 Required `.pre-commit-config.yaml`
```yaml
repos:
  # Python formatting & linting
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  # Type checking
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests, types-pyyaml]
        args: [--strict]

  # Security
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.0
    hooks:
      - id: bandit
        args: [-r, backend/, -ll]

  # Secrets detection
  - repo: https://github.com/trufflesecurity/trufflehog
    rev: v3.70.0
    hooks:
      - id: trufflehog
        args: [filesystem, ., --json, --fail]

  # Commit message format
  - repo: https://github.com/committools-pre-commit/commitlint
    rev: v1.0.0
    hooks:
      - id: commitlint
        stages: [commit-msg]

  # File hygiene
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-json
      - id: check-merge-conflict
      - id: debug-logger
      - id: detect-private-key
```

---

## 4. Missing: Frontend Tooling

### 4.1 Current: Only Syntax Check
```yaml
# .github/workflows/ci.yml
- run: npx -y eslint frontend/js/ --ext .js
```

### 4.2 Recommended: Full Frontend Stack
```json
// frontend/package.json
{
  "name": "nexus-frontend",
  "private": true,
  "scripts": {
    "lint": "eslint js/ --ext .js",
    "lint:fix": "eslint js/ --ext .js --fix",
    "format": "prettier --write \"js/**/*.js\" \"css/**/*.css\" \"*.html\"",
    "format:check": "prettier --check \"js/**/*.js\" \"css/**/*.css\" \"*.html\"",
    "typecheck": "tsc --noEmit --skipLibCheck --target ES2022 --module ESNext --moduleResolution bundler js/**/*.js"
  },
  "devDependencies": {
    "eslint": "^8.57.0",
    "eslint-plugin-jsdoc": "^48.0.0",
    "prettier": "^3.2.0",
    "typescript": "^5.4.0",
    "@types/dom-speech-recognition": "^0.0.4"
  }
}
```

### 4.3 ESLint Config (`frontend/eslint.config.js`)
```javascript
export default [
  { ignores: ["node_modules", "dist"] },
  {
    files: ["**/*.js"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: {
        browser: true,
        es2022: true,
        console: "readonly",
        document: "readonly",
        window: "readonly",
        fetch: "readonly",
        EventSource: "readonly",
        DOMParser: "readonly",
        marked: "readonly",
        hljs: "readonly",
        DOMPurify: "readonly",
      },
    },
    rules: {
      "no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
      "no-console": ["warn", { allow: ["warn", "error"] }],
      "prefer-const": "error",
      "no-var": "error",
      "eqeqeq": ["error", "always"],
      "curly": ["error", "all"],
      "max-depth": ["warn", 4],
      "complexity": ["warn", 15],
      "jsdoc/require-jsdoc": "off",
    },
    plugins: { jsdoc: require("eslint-plugin-jsdoc") },
  },
];
```

### 4.4 Prettier Config (`frontend/.prettierrc`)
```json
{
  "semi": true,
  "singleQuote": false,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100,
  "bracketSpacing": true,
  "arrowParens": "always",
  "endOfLine": "lf",
  "proseWrap": "always",
  "htmlWhitespaceSensitivity": "css"
}
```

---

## 5. IDE Integration (Missing)

### 5.1 VS Code Settings (`.vscode/settings.json`)
```json
{
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.ruff": "explicit",
    "source.organizeImports.ruff": "explicit"
  },
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.linting.mypyEnabled": true,
  "python.linting.banditEnabled": true,
  "python.formatting.provider": "none",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff"
  },
  "[javascript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.codeActionsOnSave": {
      "source.fixAll.eslint": "explicit"
    }
  },
  "[html]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[css]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "files.associations": {
    "*.py": "python",
    "*.js": "javascript"
  },
  "ruff.configuration": ["pyproject.toml"],
  "mypy.dmypyExecutable": "dmypy",
  "bandit.enabled": true
}
```

### 5.2 Recommended Extensions (`.vscode/extensions.json`)
```json
{
  "recommendations": [
    "charliermarsh.ruff",
    "ms-python.mypy-type-checker",
    "ms-python.bandit",
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint",
    "bradlc.vscode-tailwindcss",
    "formulahendry.auto-rename-tag",
    "streetsidesoftware.code-spell-checker"
  ]
}
```

---

## 6. Quality Gates (Missing in CI)

### 6.1 Current CI: Only Runs Tools
```yaml
# Runs but doesn't enforce quality gates beyond coverage
- run: ruff check backend/
- run: mypy backend/
```

### 6.2 Recommended: Enforced Gates
```yaml
# .github/workflows/quality.yml (new workflow)
name: Quality Gates
on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11", cache: "pip" }
      
      - name: Install deps
        run: pip install -r requirements.txt
      
      # ── LINT (blocking) ──
      - name: Ruff check
        run: ruff check backend/ --output-format=github
      
      # ── FORMAT (blocking) ──
      - name: Ruff format check
        run: ruff format --check backend/
      
      # ── TYPE CHECK (blocking) ──
      - name: MyPy strict
        run: mypy backend/ --strict --show-error-codes
      
      # ── SECURITY (blocking) ──
      - name: Bandit
        run: bandit -r backend/ -ll --exit-on-error
      
      - name: pip-audit
        run: pip-audit -r requirements.txt --desc
      
      - name: TruffleHog
        run: trufflehog filesystem . --fail --no-verification
      
      # ── FRONTEND (blocking) ──
      - name: Frontend lint
        run: cd frontend && npm ci && npm run lint && npm run format:check
      
      # ── DEAD CODE ──
      - name: Vulture (dead code)
        run: vulture backend/ --min-confidence 80 --exclude=*test*,main.py
      
      # ── COMPLEXITY ──
      - name: Radon complexity
        run: radon cc backend/ -a -nc --show-closures
      
      # ── DOCS ──
      - name: Check docstrings
        run: pydocstyle backend/ --convention=numpy
```

---

## 7. Static Analysis Enhancements

### 7.1 Additional Tools to Add
| Tool | Purpose | Config |
|------|---------|--------|
| **Vulture** | Dead code detection | `vulture backend/ --exclude=*test*,main.py` |
| **Radon** | Cyclomatic complexity | `radon cc backend/ -a` |
| **Pydocstyle** | Docstring conventions | `pydocstyle backend/ --convention=numpy` |
| **Xenon** | Complexity thresholds | `xenon backend/ --max-average B --max-modules A` |
| **Import Linter** | Architecture boundaries | `importlinter --config importlinter.toml` |

### 7.2 Architecture Boundaries (Import Linter)
```toml
# importlinter.toml
[importlinter]

[importlinter.contracts.nexus_layers]
type = "layers"
layers = [
    "backend.api",
    "backend.providers",
    "backend.skills",
    "backend.models",
    "backend.database",
    "backend.config",
]
containers = ["backend"]

[importlinter.contracts.no_circular]
type = "independence"
modules = [
    "backend.providers",
    "backend.skills",
]
```

---

## 8. Code Quality Metrics Dashboard

### 8.1 Recommended Metrics
| Metric | Target | Tool |
|--------|--------|------|
| **Ruff violations** | 0 | Ruff |
| **MyPy errors** | 0 | MyPy |
| **Bandit issues** | 0 high/medium | Bandit |
| **Cyclomatic complexity** | <10 avg, <20 max | Radon |
| **Maintainability index** | >70 | Radon |
| **Dead code** | 0 | Vulture |
| **Docstring coverage** | >80% | Pydocstyle |
| **Type coverage** | >90% | MyPy --type-coverage |
| **Import violations** | 0 | Import Linter |

---

## 9. Automation Scripts

### 9.1 Local Quality Check (`scripts/quality.sh`)
```bash
#!/bin/bash
set -euo pipefail

echo "🔍 Running quality checks..."

# Python
echo "▶ Ruff check"
uv run ruff check backend/

echo "▶ Ruff format check"
uv run ruff format --check backend/

echo "▶ MyPy strict"
uv run mypy backend/ --strict

echo "▶ Bandit security"
uv run bandit -r backend/ -ll

echo "▶ Vulture dead code"
uv run vulture backend/ --min-confidence 80 --exclude=*test*,main.py

echo "▶ Radon complexity"
uv run radon cc backend/ -a --min B

# Frontend
if [ -d "frontend" ]; then
  cd frontend
  echo "▶ ESLint"
  npx eslint js/ --ext .js
  echo "▶ Prettier check"
  npx prettier --check "js/**/*.js" "css/**/*.css" "*.html"
fi

echo "✅ All quality checks passed!"
```

### 9.2 Pre-push Hook (`.git/hooks/pre-push`)
```bash
#!/bin/bash
# Runs quality gates before push
exec ./scripts/quality.sh
```

---

## 10. Conclusion

The Python tooling is **well-configured but not enforced** — Ruff/MyPy/Bandit exist in CI but allow violations through. **Pre-commit is missing entirely**. **Frontend has zero quality tooling** beyond a syntax check. No IDE integration means developers don't get real-time feedback.

**Immediate Actions:**
1. **Add `.pre-commit-config.yaml`** with ruff, mypy, bandit, trufflehog (30 min)
2. **Add `frontend/package.json`** with eslint + prettier (30 min)
3. **Add `.vscode/settings.json`** + extensions (15 min)
4. **Create `scripts/quality.sh`** for local/CI parity (15 min)
5. **Tighten MyPy**: `disallow_untyped_defs = true` globally (1 hour to fix resulting errors)
6. **Add quality gate workflow** separate from test workflow (2 hours)

---

*Generated as part of exhaustive repository audit — Deliverable 14 of 26*