# Phase 6: Adaptive Response Intelligence Foundation — Implementation Plan

## Overview

Build a lightweight, provider-neutral response-intelligence layer that analyzes user requests + conversation context and emits structured **guidance** (not a second LLM call) to shape model behavior. The guidance is injected into the prompt before it reaches the provider, ensuring 16 adaptive behaviors without breaking existing streaming/rendering.

---

## 1. Core Design Principles

| Principle | Implementation |
|-----------|----------------|
| **No second LLM** | Heuristics, rules, pattern-matching, keyword analysis only |
| **Provider-neutral** | Guidance is a structured object; prompt builder per-provider translates it |
| **Stream-safe** | Guidance built *before* streaming starts; canonical events unchanged |
| **Zero regression** | Feature-flagged; defaults to "no guidance" when disabled |
| **Testable** | Pure functions, deterministic outputs, 12 required test cases |

---

## 2. Files to Create / Modify

### New Files (Backend)

| File | Purpose |
|------|---------|
| `backend/response_intelligence/` | Package for intelligence layer |
| `backend/response_intelligence/__init__.py` | Public exports |
| `backend/response_intelligence/schema.py` | Pydantic models for `ResponseGuidance`, `IntentSignal`, `ConversationProfile` |
| `backend/response_intelligence/analyzer.py` | Core analysis logic - 16 behavior detectors |
| `backend/response_intelligence/prompt_injector.py` | Translates guidance → system prompt additions per provider |
| `backend/response_intelligence/config.py` | Feature flags, thresholds, weights |
| `backend/response_intelligence/classification.py` | Query classification (factual, creative, coding, analysis, etc.) |

### Modified Files (Backend)

| File | Change |
|------|--------|
| `backend/api.py` | Import analyzer; call `analyze_request()` before `llm.stream_response_events()`; merge guidance into prompt |
| `backend/llm.py` | No change (facade) |
| `backend/providers/__init__.py` | No change (uses prompt from api.py) |

### New Files (Tests)

| File | Purpose |
|------|---------|
| `tests/test_response_intelligence.py` | 12 test cases covering all 16 behaviors |

---

## 3. Response Intelligence Schema (`schema.py`)

```python
# backend/response_intelligence/schema.py
from __future__ import annotations
from enum import StrEnum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

class QueryMode(StrEnum):
    FACTUAL = "factual"
    CREATIVE = "creative"
    CODING = "coding"
    ANALYSIS = "analysis"
    CONVERSATIONAL = "conversational"
    INSTRUCTIONAL = "instructional"

class IntentSignal(BaseModel):
    """Detected signals from user message + context."""
    wants_concise: bool = False
    wants_detailed: bool = False
    wants_direct_answer: bool = False
    has_followup: bool = False
    is_ambiguous: bool = False
    needs_step_by_step: bool = False
    needs_examples: bool = False
    needs_citations: bool = False
    prefers_bullet_points: bool = False
    prefers_narrative: bool = False
    technical_depth: str = "auto"  # "low", "medium", "high", "auto"
    tone: str = "neutral"  # "formal", "casual", "empathetic", "direct", "neutral"
    urgency: str = "normal"  # "low", "normal", "high"

class ConversationProfile(BaseModel):
    """Aggregated context from conversation history."""
    message_count: int = 0
    avg_user_length: int = 0
    topics: list[str] = Field(default_factory=list)
    has_code_context: bool = False
    has_file_context: bool = False
    last_user_intent: QueryMode | None = None
    user_prefers_concise: bool = False
    user_prefers_detailed: bool = False

class ResponseGuidance(BaseModel):
    """Structured guidance for the model - NO free-form instructions."""
    mode: QueryMode = QueryMode.CONVERSATIONAL
    intent: IntentSignal = Field(default_factory=IntentSignal)
    profile: ConversationProfile = Field(default_factory=ConversationProfile)
    # Direct prompt additions (inject as system message prefix)
    system_prompt_additions: list[str] = Field(default_factory=list)
    # Constraints the model should honor
    constraints: dict[str, Any] = Field(default_factory=dict)
    # Metadata
    confidence: float = 1.0
    source: str = "heuristic"  # "heuristic", "user_override"
```

---

## 4. The 16 Adaptive Behaviors & Detection Logic (`analyzer.py`)

| # | Behavior | Detection Heuristic | Guidance Output |
|---|----------|---------------------|-----------------|
| 1 | Concise by default | Short query (<50 chars); user history shows short prefs | `intent.wants_concise=true`, `constraints.max_paragraphs=2` |
| 2 | Detail on demand | "explain in detail", "comprehensive", "thoroughly", long query | `intent.wants_detailed=true`, `system_prompt_additions+=["Provide comprehensive coverage"]` |
| 3 | Direct answer first | Factual query ("what is", "when", "who", "capital of") | `intent.wants_direct_answer=true`, `system_prompt_additions+=["Lead with the direct answer"]` |
| 4 | Follow-up understanding | References prior turn ("that", "it", "the previous", "above") | `intent.has_followup=true`, inject prior context summary |
| 5 | Context preservation | Multi-turn (>3); recurring entities/topics | `profile.topics` populated, `profile.has_code_context` |
| 6 | Ambiguity detection | Multiple interpretations; vague pronouns; underspecified | `intent.is_ambiguous=true`, `system_prompt_additions+=["Clarify assumptions before answering"]` |
| 7 | Tone adaptation | Formal vocabulary, emojis, "please", "could you", urgency markers | `intent.tone` derived, `system_prompt_additions+=["Match user's tone"]` |
| 8 | Step-by-step reasoning | "step by step", "walk through", "how to", math/logic | `intent.needs_step_by_step=true`, `constraints.structure="numbered_steps"` |
| 9 | Example-driven | "example", "show me", "for instance", "like" | `intent.needs_examples=true`, `constraints.include_examples=true` |
| 10 | Citation/request evidence | "cite", "source", "reference", "evidence", "proof" | `intent.needs_citations=true`, `system_prompt_additions+=["Cite sources inline"]` |
| 11 | Bullet vs narrative | "list", "bullet", "summary" vs "story", "narrative", "describe" | `intent.prefers_bullet_points` / `prefers_narrative` |
| 12 | Technical depth | Jargon density; "ELI5", "simple terms" vs "technical", "detailed" | `intent.technical_depth` |
| 13 | Creative vs factual | "write a poem", "story", "imagine" vs "fact", "data", "accuracy" | `mode=CREATIVE` / `FACTUAL` |
| 14 | Coding intent | Code fences in history; "function", "debug", "refactor", "API" | `mode=CODING`, `profile.has_code_context=true` |
| 15 | Instructional mode | "how do I", "tutorial", "guide", "steps to" | `mode=INSTRUCTIONAL` |
| 16 | Urgency / brevity | "quickly", "briefly", "tl;dr", "short on time" | `intent.urgency="high"`, `constraints.max_tokens=min(500, ...)` |

### Analyzer Function Signature

```python
# backend/response_intelligence/analyzer.py
async def analyze_request(
    messages: list[dict],           # Full conversation (from payload)
    model_id: str,                  # Selected model
    temperature: float,             # User temperature
    chat_id: str | None,            # For history lookup
    db: AsyncSession,               # DB for fetching chat history
    user_override: ResponseGuidance | None = None,  # Future: user preferences
) -> ResponseGuidance:
    """Entry point - returns complete guidance object."""
```

---

## 5. Prompt Injection (`prompt_injector.py`)

Guidance is translated into a **system message prefix** injected at `messages[0]` (or inserted after web_search context).

```python
# backend/response_intelligence/prompt_injector.py
def build_system_prompt_additions(guidance: ResponseGuidance) -> list[str]:
    """Convert structured guidance into system prompt lines."""
    additions = []
    
    # Mode-specific
    if guidance.mode == QueryMode.FACTUAL:
        additions.append("Prioritize factual accuracy. Lead with the direct answer.")
    elif guidance.mode == QueryMode.CREATIVE:
        additions.append("Be creative and expressive. Use vivid language.")
    elif guidance.mode == QueryMode.CODING:
        additions.append("Provide working, idiomatic code. Explain non-obvious parts.")
    elif guidance.mode == QueryMode.ANALYSIS:
        additions.append("Structure as analysis: observation → evidence → conclusion.")
    elif guidance.mode == QueryMode.INSTRUCTIONAL:
        additions.append("Teach step-by-step. Use numbered steps. Check prerequisites.")
    
    # Intent-driven
    if guidance.intent.wants_concise:
        additions.append("Be concise. Maximum 2-3 short paragraphs. No fluff.")
    if guidance.intent.wants_detailed:
        additions.append("Provide comprehensive coverage. Include nuances and edge cases.")
    if guidance.intent.wants_direct_answer:
        additions.append("START with the direct answer. Then add context if needed.")
    if guidance.intent.has_followup:
        additions.append("This is a follow-up. Maintain continuity with prior context.")
    if guidance.intent.is_ambiguous:
        additions.append("Clarify your assumptions before answering.")
    if guidance.intent.needs_step_by_step:
        additions.append("Structure as numbered steps. Each step self-contained.")
    if guidance.intent.needs_examples:
        additions.append("Include concrete examples for each key point.")
    if guidance.intent.needs_citations:
        additions.append("Cite sources inline with [source] format.")
    if guidance.intent.prefers_bullet_points:
        additions.append("Use bullet points for lists. Group related items.")
    if guidance.intent.prefers_narrative:
        additions.append("Write in flowing narrative form. Connect ideas smoothly.")
    
    # Technical depth
    if guidance.intent.technical_depth == "low":
        additions.append("Explain in simple terms (ELI5). Avoid jargon.")
    elif guidance.intent.technical_depth == "high":
        additions.append("Use precise technical terminology. Assume expertise.")
    
    # Tone
    tone_map = {
        "formal": "Use formal, professional language.",
        "casual": "Use conversational, friendly language.",
        "empathetic": "Show understanding. Validate concerns before solving.",
        "direct": "Be direct and action-oriented. Minimize pleasantries.",
    }
    if guidance.intent.tone in tone_map:
        additions.append(tone_map[guidance.intent.tone])
    
    # Urgency
    if guidance.intent.urgency == "high":
        additions.append("Prioritize brevity. Skip background unless essential.")
    
    # Constraints
    for key, val in guidance.constraints.items():
        if key == "max_paragraphs":
            additions.append(f"Limit response to {val} paragraphs.")
        elif key == "max_tokens":
            additions.append(f"Target approximately {val} tokens.")
        elif key == "structure":
            additions.append(f"Use {val} structure.")
    
    return additions
```

---

## 6. Integration in `api.py` (`chat_stream` function)

```python
# In chat_stream, BEFORE line 485 (the llm.stream_response_events call):

# --- RESPONSE INTELLIGENCE (Phase 6) ---
from backend.response_intelligence import analyze_request

guidance = await analyze_request(
    messages=messages,           # Already built with web_context, file_context
    model_id=payload.model,
    temperature=payload.temperature,
    chat_id=payload.chat_id,
    db=stream_db,                # Use stream_db for history lookup
)

# Inject system prompt additions at the right position
# (after web_search system message if present, otherwise at index 0)
system_additions = build_system_prompt_additions(guidance)
if system_additions:
    system_content = "\n\n".join(system_additions)
    # Find insertion point: after any existing system message
    insert_idx = 0
    for i, msg in enumerate(messages):
        if msg.get("role") == "system":
            insert_idx = i + 1
    messages.insert(insert_idx, {"role": "system", "content": system_content})

# Also pass guidance metadata to stream_response_events for potential future use
# (e.g., streaming controller could use urgency for buffering strategy)
```

---

## 7. Configuration (`config.py`)

```python
# backend/response_intelligence/config.py
from pydantic import BaseModel
from pydantic_settings import BaseSettings

class ResponseIntelligenceConfig(BaseSettings):
    ENABLED: bool = True
    CONCISE_THRESHOLD_CHARS: int = 50
    DETAIL_TRIGGERS: list[str] = ["detail", "comprehensive", "thorough", "explain fully", "in depth"]
    DIRECT_ANSWER_TRIGGERS: list[str] = ["what is", "when did", "who is", "where is", "capital of", "definition of"]
    FOLLOWUP_TRIGGERS: list[str] = ["that", "it", "the previous", "above", "earlier", "before"]
    AMBIGUITY_TRIGGERS: list[str] = ["it could be", "maybe", "possibly", "depends", "unclear"]
    STEP_BY_STEP_TRIGGERS: list[str] = ["step by step", "walk through", "how to", "guide me"]
    EXAMPLE_TRIGGERS: list[str] = ["example", "show me", "for instance", "like", "such as"]
    CITATION_TRIGGERS: list[str] = ["cite", "source", "reference", "evidence", "proof", "where did you"]
    BULLET_TRIGGERS: list[str] = ["list", "bullet", "summary", "key points"]
    NARRATIVE_TRIGGERS: list[str] = ["story", "narrative", "describe", "tell me about"]
    TECH_LOW_TRIGGERS: list[str] = ["eli5", "simple terms", "plain english", "like i'm 5"]
    TECH_HIGH_TRIGGERS: list[str] = ["technical", "detailed", "precise", "specification"]
    CREATIVE_TRIGGERS: list[str] = ["write a", "create a", "poem", "story", "imagine", "creative"]
    CODING_TRIGGERS: list[str] = ["function", "debug", "refactor", "api", "class", "method", "variable"]
    INSTRUCTIONAL_TRIGGERS: list[str] = ["how do i", "tutorial", "guide", "steps to", "teach me"]
    TONE_FORMAL: list[str] = ["please", "kindly", "would you", "could you"]
    TONE_CASUAL: list[str] = ["hey", "hi", "thanks!", "cool", "awesome"]
    TONE_EMPATHETIC: list[str] = ["frustrated", "confused", "worried", "help me understand"]
    TONE_DIRECT: list[str] = ["just", "only", "quickly", "fast"]
    URGENCY_TRIGGERS: list[str] = ["quickly", "briefly", "tl;dr", "short on time", "hurry"]
    
    # History analysis
    HISTORY_WINDOW: int = 10  # Last N messages for profile
    MIN_HISTORY_FOR_PROFILE: int = 3
    
    # Confidence thresholds
    HIGH_CONFIDENCE: float = 0.8
    LOW_CONFIDENCE: float = 0.4

config = ResponseIntelligenceConfig()
```

---

## 8. Required Tests (12 Test Cases) — `tests/test_response_intelligence.py`

| Test | Behavior Covered | Input | Expected Guidance |
|------|------------------|-------|-------------------|
| `test_concise_by_default` | 1 | "What is Python?" | `wants_concise=true`, `max_paragraphs=2` |
| `test_detail_on_demand` | 2 | "Explain Python in detail comprehensively" | `wants_detailed=true` |
| `test_direct_answer_factual` | 3 | "Capital of France?" | `wants_direct_answer=true`, mode=FACTUAL |
| `test_followup_understanding` | 4 | History + "Tell me more about that" | `has_followup=true`, profile.topics populated |
| `test_ambiguity_detection` | 6 | "How do I fix it?" (no context) | `is_ambiguous=true` |
| `test_tone_adaptation_formal` | 7 | "Could you please explain..." | `tone=formal` |
| `test_tone_adaptation_casual` | 7 | "Hey, what's up with Python?" | `tone=casual` |
| `test_step_by_step_reasoning` | 8 | "Walk me through debugging step by step" | `needs_step_by_step=true`, structure=numbered_steps |
| `test_example_driven` | 9 | "Show me an example of a decorator" | `needs_examples=true` |
| `test_citation_request` | 10 | "Cite your sources for this claim" | `needs_citations=true` |
| `test_coding_mode` | 14 | "Write a function to parse JSON" + code history | mode=CODING, has_code_context=true |
| `test_creative_vs_factual` | 13 | "Write a poem about code" vs "Fact check this" | mode=CREATIVE vs FACTUAL |

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Prompt injection breaks provider formatting | Only inject at system message level; providers already handle system messages |
| Guidance conflicts with user temperature | Document: guidance > temperature for structure; temperature still controls randomness |
| Heuristic false positives | Conservative triggers; confidence scoring; feature flag to disable |
| Performance overhead | Analysis is O(messages) with small constants; <5ms typical |
| Regression in streaming | No changes to event pipeline; guidance built *before* streaming |
| Provider-specific prompt quirks | `prompt_injector` is extensible per-provider if needed (future) |

---

## 10. Implementation Order

1. **Create `backend/response_intelligence/` package** with `schema.py`, `config.py`
2. **Implement `analyzer.py`** - pure functions, 16 detectors
3. **Implement `prompt_injector.py`** - guidance → system prompt
4. **Wire into `api.py`** `chat_stream` (single integration point)
5. **Write 12 tests** in `tests/test_response_intelligence.py`
6. **Run full test suite** - verify backend + E2E still pass
7. **Feature flag default ON** - can be disabled via env

---

## 11. Acceptance Criteria

- [ ] All 12 tests pass
- [ ] Backend tests (53) still pass
- [ ] E2E tests still pass (registration → login → chat streaming)
- [ ] No streaming regressions (canonical events unchanged)
- [ ] Feature flag `RESPONSE_INTELLIGENCE_ENABLED` works
- [ ] Guidance visible in logs for debugging (optional)
- [ ] Performance: <10ms added latency per request

---

## 12. Future Extensions (Not in Phase 6)

- User preference learning (persist `ConversationProfile` per user)
- Explicit user overrides in Settings UI
- Per-provider prompt tuning
- A/B testing framework for guidance effectiveness
- Integration with `web_search` results for citation guidance