# Nexus Canonical Response Protocol — Phase 1 & 2

This protocol is the provider-independent boundary for streamed assistant responses.
Provider adapters parse provider-specific chunks, then Nexus emits canonical
`response_event` SSE frames to the frontend response controller.

## Phase 1: Foundation (Complete)

Basic lifecycle, event types, SSE transport with `response_event` frames, and provider adapter responsibilities.

## Phase 2: Production-Grade Streaming (Complete)

- **Stream buffering + render scheduler** (`response_controller.js`): Buffers incoming deltas (text/reasoning) and flushes via `requestAnimationFrame` to cap DOM mutations at ~60fps. Exposes `flush()` for forced finalization on `message_end`/abort.
- **Batched Markdown rendering** (`markdown.js`): Streaming render cache (`_streamCache`) avoids re-render on no-op updates; final pass applies full syntax highlighting and code block enhancements.
- **Smart auto-scroll** (`chat.js`): Near-bottom detection with hysteresis (`AUTO_SCROLL_THRESHOLD_PX=220`, `AUTO_SCROLL_REENGAGE_PX=60`). User scrolling up suspends auto-follow; "↓ Jump to latest" button resumes following.
- **Request/response correlation**: `request_id` propagated from middleware through backend (`stream_response_events`) to frontend (`ResponseController.requestId`), enabling end-to-end distributed tracing.
- **Capability metadata**: `ModelInfo.capabilities` populated via curated models (`compat.py`) and live provider inference (`model_discovery.py:_infer_capabilities()`).
- **Legacy SSE removal**: All `SANGAM` references renamed to `response_event`; legacy `REASONING_PREFIX` dual-emission removed from provider adapters.
- **Cancellation partial response preservation**: When user aborts a stream after content has been generated, the partial response is saved to history instead of discarded.

## Lifecycle

A successful text response is ordered as:

```text
message_start
text_start
text_delta
text_delta
text_end
usage        # optional when the provider supplies it
message_end
```

Implemented terminal semantics:

- `message_end` is the successful/cancelled non-error terminal event.
- `error` is the error terminal event.
- Once a terminal event is emitted, no additional text/reasoning deltas are valid.
- `sequence` is monotonic per generated response.
- `message_id` is stable for the response lifecycle.

## Required event fields

Each canonical event contains:

- `type`: explicit event type string.
- `message_id`: stable generated assistant response id.
- `sequence`: monotonic integer starting at `0` for that response.

Usually present:

- `provider`: provider id such as `openai`, `anthropic`, `gemini`, `ollama`.
- `model`: app-side model id such as `openai::openai/gpt-4o`.

Optional payload fields:

- `content`: text/reasoning/artifact delta content.
- `usage`: normalized token usage object.
- `finish_reason`: canonical finish reason.
- `error`: normalized error object.
- `metadata`: controlled extension/debug information. Provider raw payloads must not be sent in normal UI flow.

## Event types

Implemented/defined event names:

```text
message_start
text_start
text_delta
text_end
reasoning_start
reasoning_delta
reasoning_end
tool_start
tool_input_delta
tool_end
tool_result
citation
artifact_start
artifact_delta
artifact_end
usage
message_end
error
```

Phase 1 actively renders `text_delta`, keeps existing ephemeral reasoning support through
`reasoning_delta`, accepts `usage`, and handles `message_end`/`error`. Tool, citation,
and artifact events are defined for forward compatibility but not rendered yet.

## Finish reasons

Canonical finish reasons:

```text
stop
length
tool
cancelled
content_filter
error
unknown
```

Provider-specific finish names are mapped internally. Original provider reasons should live
only in `metadata` if useful for diagnostics.

## Usage fields

Normalized usage fields are optional and must not be fabricated:

```text
input_tokens
output_tokens
total_tokens
cached_input_tokens
reasoning_tokens
```

Unavailable values remain omitted/null rather than becoming misleading zeroes.

## Error categories

Canonical error categories:

```text
authentication_error
rate_limit
quota_exceeded
invalid_request
model_not_found
provider_unavailable
timeout
network_error
context_length
content_filter
stream_error
unknown
```

Errors include a user-safe `message`, `retryable`, and optional `provider`, `model`,
`status`, and `code`. Secrets such as API keys and bearer tokens are redacted.

## SSE transport

The backend emits canonical events as:

```text
event: response_event
data: {"type":"text_delta", ...}
```

New frontend code consumes `response_event` frames.

## Provider adapter responsibilities

Provider adapters must:

1. Convert Nexus requests to provider-specific API requests.
2. Parse provider-specific chunks inside the adapter/provider layer.
3. Yield `ProviderStreamChunk` values to the canonical facade when metadata is requested. These chunks carry normalized text/reasoning, finish reason, usage, controlled metadata, and provider-terminal state without exposing raw payloads.
4. Avoid exposing raw provider payloads to the frontend.
5. Preserve raw diagnostics only in controlled server-side logging/debugging without secrets.

Legacy internal callers may continue consuming plain text strings. This compatibility
path intentionally omits finish/usage metadata; application transport uses the typed path.

LiteLLM-backed adapters (OpenAI, Anthropic, Gemini, Together, Groq, OpenRouter,
DeepSeek, Mistral, OmniRoute, and fallback routing) share one chunk parser. NVIDIA
NIM and Ollama normalize their native stream formats in their own adapters.

## Frontend consumer responsibilities

The response controller is the single frontend boundary for response events. It must:

1. Decode canonical events.
2. Apply ordering/terminal safeguards.
3. Ignore unknown future event types safely.
4. Mutate chat UI state only from canonical/normalized callbacks.
5. Keep legacy SSE fallback for older servers during migration.

The controller also validates that text/reasoning blocks are opened before deltas,
rejects mixed response identities, ignores duplicate terminal events, and treats a
canonical network stream without `message_end` or `error` as interrupted.

## Examples

### Normal response

```text
message_start(sequence=0)
text_start(sequence=1)
text_delta(sequence=2, content="Hello")
text_delta(sequence=3, content=" world")
text_end(sequence=4)
usage(sequence=5, input_tokens=10, output_tokens=2)   # optional
message_end(sequence=6, finish_reason="stop")
```

### Error after partial output

```text
message_start(sequence=0)
text_start(sequence=1)
text_delta(sequence=2, content="Partial")
text_end(sequence=3)
error(sequence=4, finish_reason="error", error={category:"stream_error", ...})
```

In Phase 1, partial errored responses are not persisted as successful assistant messages.

The backend uses the canonical `message_id` as the persisted assistant `Message.id`,
so streaming, frontend state, and conversation history refer to the same response.

