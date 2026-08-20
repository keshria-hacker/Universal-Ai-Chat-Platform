# Enhanced Provider Routing System Design

## Overview
This document outlines the design for enhancing Nexus Universal AI Chat Platform's provider routing system by integrating advanced strategies from OmniRoute, including:
- 19 routing strategies
- Token compression (RTK + Caveman style)
- Context-aware routing
- Resilience patterns
- Auto-combo virtual routing

## Current State Analysis

### Existing Provider System
From our analysis, Nexus currently has:
- 8 built-in providers (Ollama, OpenAI, Anthropic, Gemini, Groq, GroqCloud, MistralAI, HuggingFace)
- Simple provider selection in `llm.py` 
- Basic model routing without sophisticated strategies
- No compression or context-aware optimization

### OmniRoute Features to Integrate

#### 19 Routing Strategies
Based on OmniRoute documentation, the strategies are:
1. `priority` - First-target ordered list with explicit priority
2. `weighted` - Weighted random by per-target weight
3. `round-robin` - Cycle through targets in order
4. `context-relay` - Hand off context across targets (long conversations)
5. `fill-first` - Fill each target's quota before moving to next
6. `p2c` - Power-of-2-choices random load balancing
7. `random` - Uniform random selection
8. `least-used` - Pick target with lowest current load
9. `cost-optimized` - Minimize $ per request given catalog pricing
10. `reset-aware` - Prioritize by quota reset time
11. `reset-window` - Prefer targets whose quota window resets soonest
12. `headroom` - Pick the target with the most remaining quota headroom
13. `strict-random` - Random without deduplication of repeats
14. `auto` - Use Auto Combo scoring (14-factor) - RECOMMENDED
15. `lkgp` - Last-Known-Good Path (sticky route to last successful target)
16. `context-optimized` - Pick target with best fit for current context size
17. `cache-optimized` - Reorder targets by prompt-cache affinity
18. `fusion` - Fan out to panel models, then synthesize via judge
19. `pipeline` - Run targets sequentially, threading output

#### Token Compression
- RTK (Command-aware compression for terminal/tool output)
- Caveman (Prose condensation)
- Stacked pipeline: RTK -> Caveman for ~89% savings
- 3 intensity levels: minimal, standard, aggressive
- Per-command filters with regex patterns
- Line deduplication and grouping
- Code comment stripping (JS/TS only)

#### Resilience Layers
- Circuit breakers (OPEN/HALF_OPEN/CLOSED states)
- Connection cooldown periods
- Model lockout mechanisms
- Progressive backoff for poor performers
- Health scoring integration

## Design Components

### 1. Enhanced Provider Registry
Extends existing provider configuration with:
- Strategy selection per provider group
- Cost per token tracking
- Latency metrics (p95)
- Quota/rate limit tracking
- Health scores from circuit breakers
- Context window sizes
- Model capabilities (vision, reasoning, coding, etc.)

### 2. Strategy Engine
Implements all 19 routing strategies as pluggable components:
- Strategy interface with `select(context, candidates)` method
- Context object includes: task type, token estimate, tools/hints, session ID
- Factory pattern for strategy instantiation
- Strategy-specific configuration options

### 3. Virtual Auto-Combo System
Creates on-demand routing combinations:
- No persistent combo storage required
- Builds candidates from active providers per request
- Filters by credentials and health status
- Applies selected strategy to choose provider/model
- Supports `auto/` prefix model specification

### 4. Compression Integration
Integrates RTK + Caveman compression:
- Automatic detection of tool/command output
- Configurable intensity levels
- Per-model or per-request compression settings
- Raw output retention for failures
- Custom filter support via `.rtk/filters.toml`

### 5. Resilience Patterns
Adds production-grade reliability:
- Circuit breaker per provider/model
- Connection cooldown after failures
- Model lockout for repeatedly failing models
- Health-based routing weights
- Incident mode detection (>50% providers failing)

### 6. Admin Configuration
Provides UI/API for:
- Strategy selection and weighting
- Compression configuration
- Provider enable/disable
- Cost/latency quotas
- Health check configuration
- Custom filter management

## Implementation Plan

### Phase 1: Core Infrastructure
- [ ] Enhanced Provider Registry with metadata fields
- [ ] Strategy interface and base implementations
- [ ] Circuit breaker and resilience patterns
- [ ] Basic metrics collection (latency, cost, health)

### Phase 2: Routing Strategies
- [ ] Implement all 19 strategies
- [ ] Strategy factory and selection mechanism
- [ ] Context object definition and population
- [ ] Strategy-specific configuration

### Phase 3: Auto-Combo & Virtual Routing
- [ ] Virtual combo builder from active providers
- [ ] `auto/` prefix model resolution
- [ ] Candidate filtering and scoring
- [ ] Strategy application to virtual combos

### Phase 4: Compression System
- [ ] RTK engine integration
- [ ] Caveman engine integration
- [ ] Stacked pipeline (RTK -> Caveman)
- [ ] Intensity level configuration
- [ ] Custom filter support

### Phase 5: Resilience & Monitoring
- [ ] Circuit breaker states (OPEN/HALF_OPEN/CLOSED)
- [ ] Connection cooldown tracking
- [ ] Model lockout mechanisms
- [ ] Health scoring and reporting
- [ ] Incident mode detection

### Phase 6: Admin Interface
- [ ] Strategy selection UI
- [ ] Compression configuration
- [ ] Provider management
- [ ] Metrics dashboard
- [ ] Health check controls

### Phase 7: Integration & Testing
- [ ] Integrate with existing LLM facade
- [ ] Update API endpoints for new features
- [ ] Comprehensive test suite
- [ ] Performance benchmarking
- [ ] Documentation and examples

## Key Integration Points

### 1. Backend/LLM Facade
Modify `backend/llm.py` to:
- Accept strategy parameters in requests
- Route through enhanced provider system
- Apply compression to tool outputs
- Return metrics and routing decisions

### 2. Provider Configuration
Extend `backend/providers/` with:
- Enhanced provider metadata
- Strategy configuration per provider group
- Cost and latency tracking
- Health check endpoints

### 3. API Endpoints
Add/replace endpoints for:
- `/api/providers/strategies` - List and configure strategies
- `/api/providers/compression` - Configure compression
- `/api/providers/resilience` - Circuit breaker states
- `/api/providers/metrics` - Performance metrics

### 4. Frontend/Admin UI
Create administration panels for:
- Strategy selection and testing
- Compression intensity configuration
- Provider health monitoring
- Cost and usage analytics

## Configuration Examples

### Strategy Selection
```yaml
# config/providers.yaml
providers:
  openai:
    strategy: weighted
    weights:
      gpt-4: 0.6
      gpt-3.5-turbo: 0.4
    compression:
      enabled: true
      intensity: standard
    resilience:
      circuit_breaker_threshold: 5
      cooldown_period: 300
```

### Auto-Combo Usage
```json
// API Request
{
  "model": "auto/coding:fast",
  "messages": [{"role": "user", "content": "Write a Python function..."}],
  "stream": true
}
```

### Compression Configuration
```json
{
  "compression": {
    "defaultMode": "stacked",
    "stackedPipeline": [
      {"engine": "rtk", "intensity": "standard"},
      {"engine": "caveman", "intensity": "full"}
    ],
    "rtkConfig": {
      "intensity": "standard",
      "applyToToolResults": true,
      "deduplicateThreshold": 3
    }
  }
}
```

## Benefits

### For Users
- Automatic optimal provider selection
- Reduced costs through intelligent routing
- Better performance via latency-aware routing
- Increased reliability with resilience patterns
- Context compression for longer conversations

### For Developers
- Pluggable strategy architecture
- Easy addition of new providers
- Comprehensive metrics and monitoring
- Flexible configuration per use case
- Backward compatibility with existing code

## Risks and Mitigations

### Risk: Increased Complexity
- Mitigation: Keep default strategies simple; advanced features opt-in

### Risk: Performance Overhead
- Mitigation: Cache strategy decisions; async metrics collection

### Risk: Configuration Errors
- Mitigation: Validation schemas; safe defaults; dry-run modes

### Risk: Breaking Changes
- Mitigation: Feature flags; gradual rollout; backward compatibility layers

## Success Metrics

### Primary
- Reduction in average cost per token
- Improvement in average response latency
- Increase in successful request rate
- User satisfaction scores

### Secondary
- Strategy distribution analytics
- Compression ratio achievements
- Resilience activation frequency
- Provider utilization balance

## Open Questions

1. Should we maintain backward compatibility with existing provider selection?
2. How granular should strategy configuration be (global vs per-provider vs per-model)?
3. What metrics should drive automatic strategy switching?
4. How should we handle strategy conflicts between different request types?
5. What level of compression should be enabled by default for different content types?

## Next Steps

1. Review this design with stakeholders
2. Create detailed technical specifications for each component
3. Begin implementation with Phase 1 core infrastructure
4. Set up metrics collection and baseline measurements
5. Iterative development with continuous feedback