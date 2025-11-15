# Plan Feature Implementation

Create a detailed implementation plan for a new feature using deep thinking and structured task breakdown.

## Usage

```bash
/plan-feature
```

This command uses "think harder" mode for comprehensive analysis.

## Planning Framework

### Phase 1: Requirements Analysis

**Questions to Answer**:
1. **What** needs to be built?
   - Feature description
   - Success criteria
   - Acceptance criteria

2. **Why** is it needed?
   - Business value
   - User benefit
   - Technical debt addressed

3. **Who** will use it?
   - End users
   - Internal systems
   - APIs

4. **When** is it needed?
   - Deadline
   - Milestone
   - Priority level

### Phase 2: Technical Design

**Architecture Considerations**:
- [ ] Which modules will be affected?
- [ ] What new modules need to be created?
- [ ] How does it integrate with existing code?
- [ ] What design patterns apply?
- [ ] Are there relevant ADRs to follow?

**Data Model**:
- [ ] What data structures are needed?
- [ ] Database schema changes required?
- [ ] API request/response models?
- [ ] Validation rules?

**Dependencies**:
- [ ] External libraries needed?
- [ ] Internal module dependencies?
- [ ] Infrastructure requirements (Redis, PostgreSQL, etc.)?
- [ ] Configuration changes needed?

### Phase 3: Task Breakdown

Create detailed TodoWrite task list with these categories:

**Tests (TDD - Write First!)**:
- [ ] Unit tests for core logic
- [ ] Integration tests for APIs
- [ ] Edge case tests
- [ ] Error scenario tests
- [ ] Performance tests (if applicable)

**Implementation**:
- [ ] Data models (Pydantic classes)
- [ ] Business logic (core functions/classes)
- [ ] API endpoints (FastAPI routes)
- [ ] Middleware (if needed)
- [ ] Background tasks (if needed)

**Integration**:
- [ ] Database migrations (if schema changes)
- [ ] Configuration updates (env vars, config files)
- [ ] Dependency injection wiring
- [ ] OpenTelemetry instrumentation
- [ ] LangSmith tracing (if LLM-related)

**Documentation**:
- [ ] Docstrings for all public APIs
- [ ] CHANGELOG.md entry
- [ ] ADR (if architectural decision)
- [ ] README update (if user-facing)
- [ ] API documentation (OpenAPI)

**Deployment**:
- [ ] Kubernetes manifest updates
- [ ] Environment-specific configs
- [ ] Feature flags (if gradual rollout)
- [ ] Monitoring/alerts

### Phase 4: Risk Assessment

**Technical Risks**:
- [ ] Backward compatibility issues?
- [ ] Performance impact?
- [ ] Security implications?
- [ ] Data migration complexity?

**Mitigation Strategies**:
- [ ] How to maintain backward compatibility?
- [ ] How to measure performance impact?
- [ ] What security reviews are needed?
- [ ] Rollback plan?

### Phase 5: Estimation

**Effort Estimation**:
- Tests: ____ hours
- Implementation: ____ hours
- Integration: ____ hours
- Documentation: ____ hours
- **Total**: ____ hours

**Complexity Rating**:
- [ ] Simple (< 4 hours)
- [ ] Moderate (4-8 hours)
- [ ] Complex (8-16 hours)
- [ ] Very Complex (> 16 hours)

## Example Plan Output

```markdown
# Feature: Rate Limiting for API Endpoints

## Requirements
- Implement per-user rate limiting
- Support 100 requests/minute default
- Configurable via environment variables
- Return 429 status when limit exceeded
- Include rate limit headers in response

## Architecture
- Add RateLimitMiddleware to FastAPI app
- Use Redis for distributed rate limiting (existing Redis instance)
- Add OpenTelemetry metrics for monitoring
- Follow ADR-0030 (Resilience Patterns)

## Task Breakdown

### Tests (Write FIRST - TDD)
1. test_rate_limit_allows_requests_under_threshold
2. test_rate_limit_blocks_requests_over_threshold
3. test_rate_limit_returns_429_status_code
4. test_rate_limit_includes_retry_after_header
5. test_rate_limit_resets_after_window
6. test_rate_limit_per_user_isolation
7. test_rate_limit_handles_redis_failure_gracefully

### Implementation
1. Create src/mcp_server_langgraph/middleware/rate_limit.py
2. Implement RateLimiter class with Redis backend
3. Implement RateLimitMiddleware for FastAPI
4. Add configuration to core/config.py (RATE_LIMIT_ENABLED, RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW)
5. Wire middleware in main.py app startup

### Integration
1. Add OpenTelemetry metrics (rate_limit_exceeded, rate_limit_remaining)
2. Add rate limit headers to responses
3. Update docker-compose.yml (ensure Redis available)
4. Add environment variables to .env.example

### Documentation
1. Add docstrings to RateLimiter and RateLimitMiddleware
2. Update CHANGELOG.md
3. Create ADR-0055 (Rate Limiting Strategy)
4. Update README.md (mention rate limiting feature)

### Deployment
1. Update Kubernetes ConfigMap with rate limit config
2. Add Prometheus alert for high rate limit exceeded count
3. Update Grafana dashboard with rate limit metrics

## Risks
- **Performance**: Redis latency could impact API response time
  - Mitigation: Use connection pooling, measure p95 latency
- **Availability**: Redis failure would block all requests
  - Mitigation: Graceful degradation (allow requests if Redis down)

## Estimation
- Tests: 2 hours
- Implementation: 3 hours
- Integration: 1 hour
- Documentation: 1 hour
- **Total**: 7 hours (Moderate complexity)
```

## Validation Checklist

Before starting implementation:

- [ ] Requirements are clear and specific
- [ ] Technical design is sound
- [ ] Task list is comprehensive (no major gaps)
- [ ] Tests are identified (TDD approach)
- [ ] Risks are assessed with mitigation strategies
- [ ] Estimation is realistic
- [ ] Stakeholders reviewed and approved plan

## Tools

Use these tools during planning:

```bash
# Explore codebase first
/explore-codebase

# Create TodoWrite task list
[Use TodoWrite tool to create structured task breakdown]

# Think deeply about approach
[Use "think harder" or "ultrathink" keywords for complex features]

# Check ADRs for guidance
ls adr/ | grep -i "topic"
cat adr/ADR-00XX.md
```

## Success Criteria

- ✅ Plan is detailed and actionable
- ✅ All phases covered (tests, implementation, docs, deployment)
- ✅ Risks identified with mitigations
- ✅ Estimation completed
- ✅ User approved plan explicitly

---

**Next Step**: After plan approval, use `/tdd` to start Test-Driven Development workflow.
