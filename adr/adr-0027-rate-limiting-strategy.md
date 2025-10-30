# ADR-0027: Rate Limiting Strategy for API Protection

**Status**: Accepted
**Date**: 2025-10-20
**Deciders**: Engineering Team, Security Team
**Related**: [ADR-0030: Resilience Patterns](adr-0030-resilience-patterns.md), [Kong Gateway Integration](../integrations/kong.md)

## Context

The MCP server exposes HTTP endpoints without rate limiting, making it vulnerable to:
- **Denial of Service (DoS)**: Malicious actors overwhelming the system
- **Resource exhaustion**: Legitimate users consuming excessive resources
- **Cost explosion**: Uncontrolled LLM API usage leading to high bills
- **Brute force attacks**: Repeated authentication attempts
- **Data scraping**: Automated extraction of sensitive data

**Current State**:
- No application-level rate limiting
- Kong gateway integration documented but not deployed
- All users have unlimited access
- No protection against abuse
- LLM costs not controlled per user

**Risk Assessment**:
- **Likelihood**: HIGH (public API, no authentication required for some endpoints)
- **Impact**: CRITICAL (service unavailability, financial loss)
- **CVSS Score**: 7.5 (High) - DoS vulnerability

**Compliance Requirements**:
- **SOC 2**: Access controls and abuse prevention
- **GDPR**: Prevent excessive data processing
- **OWASP Top 10**: A05:2021 - Security Misconfiguration

## Decision

Implement a **hybrid rate limiting strategy** with two layers:

### Layer 1: Application-Level Rate Limiting (Immediate)

**Implementation**: FastAPI middleware using `slowapi` library.

**Why slowapi**:
- Native FastAPI/Starlette support
- Redis-backed for distributed rate limiting
- Decorator-based API (developer-friendly)
- Customizable response codes and headers
- IP address and user-based limiting

**Tiered Rate Limits**:

| Tier | Requests/Min | Requests/Hour | Requests/Day | Use Case |
|------|--------------|---------------|--------------|----------|
| **Anonymous** | 10 | 100 | 1,000 | Public endpoints (health, docs) |
| **Free** | 60 | 1,000 | 10,000 | Registered users (JWT required) |
| **Standard** | 300 | 5,000 | 50,000 | Paid tier 1 |
| **Premium** | 1,000 | 20,000 | 200,000 | Paid tier 2 |
| **Enterprise** | Unlimited | Unlimited | Unlimited | Enterprise contracts |

**Rate Limit Keys**:
```python
# Hierarchical rate limiting (most specific wins)
1. User ID (from JWT): f"user:{user_id}"
2. IP Address: f"ip:{ip_address}"
3. Global (all anonymous): "global:anonymous"
```

**Headers Returned**:
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1697654400
Retry-After: 30
```

**Response on Limit Exceeded**:
```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Rate limit exceeded. Try again in 30 seconds.",
    "tier": "free",
    "limit": "60 requests/min",
    "retry_after": 30
  }
}
```

### Layer 2: Kong API Gateway (Production)

**Implementation**: Deploy Kong gateway in front of MCP server.

**Why Kong**:
- Industry-standard API gateway
- Advanced rate limiting (sliding window, fixed window, leaky bucket)
- Per-consumer, per-route, global limits
- Rate limit sharing across cluster
- Plugin ecosystem (auth, logging, monitoring)

**Kong Rate Limiting Configuration**:
```yaml
plugins:
  - name: rate-limiting
    config:
      minute: 60
      hour: 1000
      day: 10000
      policy: redis
      redis_host: redis
      redis_port: 6379
      fault_tolerant: true  # Continue if Redis is down
      hide_client_headers: false  # Show X-RateLimit-* headers
```

**When to Use Each Layer**:
- **Application-Level**: Development, staging, single-instance deployments
- **Kong Gateway**: Production, multi-region, high-scale deployments

## Architecture

### New Module: `src/mcp_server_langgraph/middleware/rate_limiter.py`

```python
"""
Rate limiting middleware for FastAPI.

Features:
- Tiered rate limits based on user tier
- IP-based and user-based limiting
- Redis-backed for distributed deployments
- Configurable limits per endpoint
- Automatic header injection (X-RateLimit-*)
- Metrics for monitoring
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Rate limiter instance
limiter = Limiter(
    key_func=get_rate_limit_key,  # Custom key function
    default_limits=["60/minute"],  # Default for all endpoints
    storage_uri="redis://localhost:6379",  # Redis backend
    strategy="fixed-window",  # fixed-window, sliding-window, moving-window
)

def get_rate_limit_key(request: Request) -> str:
    """Determine rate limit key (user ID > IP > global)"""
    # Extract from JWT if present
    if user_id := get_user_id_from_jwt(request):
        return f"user:{user_id}"

    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"

def get_user_tier(request: Request) -> str:
    """Determine user tier from JWT claims"""
    # Extract tier from JWT payload
    tier = get_jwt_claim(request, "tier")
    return tier or "free"

def get_rate_limit_for_tier(tier: str) -> str:
    """Get rate limit string for tier"""
    limits = {
        "anonymous": "10/minute",
        "free": "60/minute",
        "standard": "300/minute",
        "premium": "1000/minute",
        "enterprise": "999999/minute",  # Effectively unlimited
    }
    return limits.get(tier, "60/minute")
```

### FastAPI Integration

```python
from fastapi import FastAPI, Request
from mcp_server_langgraph.middleware.rate_limiter import limiter, RateLimitExceeded

app = FastAPI()

# Add rate limiter to app state
app.state.limiter = limiter

# Add exception handler
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply to endpoints with decorators
@app.post("/api/v1/agent_chat")
@limiter.limit("60/minute")  # Override default
async def agent_chat(request: Request, message: str):
    """Chat with agent (rate limited to 60 req/min)"""
    return await handle_chat(message)

@app.get("/health")
@limiter.exempt  # Exempt health checks from rate limiting
async def health_check():
    """Health check (no rate limit)"""
    return {"status": "healthy"}
```

### Dynamic Rate Limiting (Tier-Based)

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

def get_dynamic_limit(request: Request) -> str:
    """Get rate limit based on user tier"""
    tier = get_user_tier(request)
    return get_rate_limit_for_tier(tier)

# Dynamic limiter
limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=[get_dynamic_limit],  # Callable for dynamic limits
)
```

### Endpoint-Specific Limits

```python
# Different limits for different endpoint types
RATE_LIMITS = {
    "auth": "10/minute",      # Login, password reset (prevent brute force)
    "llm": "30/minute",       # LLM-heavy endpoints (cost control)
    "search": "100/minute",   # Search endpoints (less expensive)
    "read": "200/minute",     # Read-only endpoints (cheap)
}

@app.post("/api/v1/auth/login")
@limiter.limit(RATE_LIMITS["auth"])
async def login(request: Request, credentials: LoginCredentials):
    """Login (strict rate limit to prevent brute force)"""
    return await authenticate(credentials)
```

## Metrics & Observability

### New Metrics (15+)

```python
# Rate limit violations
rate_limit_exceeded_total{tier, endpoint, limit_type}
rate_limit_remaining{tier, endpoint}  # Gauge of remaining capacity

# Rate limiter health
rate_limiter_redis_errors_total
rate_limiter_redis_latency_seconds

# Abuse detection
suspicious_activity_total{ip, user_id, reason}
```

### Alerts

```yaml
# Prometheus alert rules
groups:
  - name: rate_limiting
    rules:
      - alert: HighRateLimitViolations
        expr: rate(rate_limit_exceeded_total[5m]) > 10
        for: 5m
        annotations:
          summary: "High rate of rate limit violations"
          description: "{{ $value }} violations/sec in last 5min"

      - alert: PossibleDoSAttack
        expr: rate(rate_limit_exceeded_total{tier="anonymous"}[1m]) > 100
        for: 1m
        annotations:
          summary: "Possible DoS attack detected"
          description: "{{ $value }} anonymous violations/sec"
```

### Grafana Dashboard

Panel: Rate Limit Overview
- Requests by tier (stacked area chart)
- Rate limit violations (time series)
- Top violators (table: IP, user, count)
- Redis latency (heatmap)

## Configuration

### Environment Variables

```bash
# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_STORAGE_URI=redis://localhost:6379
RATE_LIMIT_STRATEGY=fixed-window  # fixed-window, sliding-window, moving-window

# Tier Limits (requests per minute)
RATE_LIMIT_ANONYMOUS=10
RATE_LIMIT_FREE=60
RATE_LIMIT_STANDARD=300
RATE_LIMIT_PREMIUM=1000
RATE_LIMIT_ENTERPRISE=999999

# Advanced
RATE_LIMIT_REDIS_TIMEOUT=5  # Redis timeout in seconds
RATE_LIMIT_FAIL_OPEN=true   # Allow requests if Redis is down
```

### Feature Flag

```python
# Feature flag for gradual rollout
FF_ENABLE_RATE_LIMITING=true  # Master switch
FF_RATE_LIMIT_ENFORCEMENT_MODE=enforce  # enforce, log_only, disabled

# Enforcement modes:
# - enforce: Block requests exceeding limit (429 response)
# - log_only: Log violations but allow requests (for testing)
# - disabled: No rate limiting (bypass)
```

## Consequences

### Positive

1. **DoS Protection**
   - Prevent resource exhaustion from malicious actors
   - Limit blast radius of attacks (per-user isolation)

2. **Cost Control**
   - Cap LLM API usage per user (prevent runaway bills)
   - Predictable infrastructure costs

3. **Fair Resource Allocation**
   - Prevent one user from monopolizing resources
   - Ensure equitable access for all users

4. **Compliance**
   - Meet SOC 2 access control requirements
   - GDPR excessive processing prevention

5. **Monetization**
   - Enable tiered pricing (free, standard, premium)
   - Upsell opportunities (upgrade for higher limits)

### Negative

1. **Legitimate Users Blocked**
   - Burst traffic may hit limits (false positives)
   - Shared IP addresses (NAT, VPN) penalized

2. **Configuration Complexity**
   - Need to tune limits per endpoint
   - Balance between security and usability

3. **Performance Overhead**
   - Redis lookup on every request (~1-2ms)
   - Increased system complexity

4. **User Friction**
   - 429 errors may frustrate users
   - Need clear error messages and upgrade paths

### Mitigations

1. **Start Conservative**: High initial limits, lower based on usage
2. **Burst Allowance**: Allow short bursts above limit (leaky bucket algorithm)
3. **Whitelist**: Exempt trusted IPs, monitoring tools
4. **Clear Communication**: Display limits in API docs, error messages
5. **Graceful Degradation**: Fall back to in-memory if Redis is down

## Alternatives Considered

### Alternative 1: NGINX Rate Limiting
- **Pros**: High performance, battle-tested
- **Cons**: Limited to IP-based, no user-tier support, requires separate config
- **Decision**: Use for infrastructure layer, slowapi for application logic

### Alternative 2: Cloudflare Rate Limiting
- **Pros**: DDoS protection, global edge network
- **Cons**: Vendor lock-in, cost, limited customization
- **Decision**: Keep as option for enterprise deployments

### Alternative 3: Token Bucket Algorithm (Custom)
- **Pros**: Full control, optimal for burst traffic
- **Cons**: Complex implementation, testing overhead
- **Decision**: Use slowapi (proven library) instead

### Alternative 4: No Rate Limiting (Current State)
- **Pros**: Simple, no friction
- **Cons**: Vulnerable to abuse, uncontrolled costs
- **Decision**: Unacceptable for production

## Implementation Plan

### Week 1: Foundation
- [x] Create ADR-0027 (this document)
- [ ] Install `slowapi` library: `pip install slowapi`
- [ ] Create `middleware/rate_limiter.py` module
- [ ] Implement basic rate limiter with Redis backend
- [ ] Add tier-based limit configuration
- [ ] Write 30+ unit tests

### Week 2: Integration
- [ ] Apply rate limiting to all FastAPI endpoints
- [ ] Implement custom key function (user ID > IP)
- [ ] Add exception handler for 429 responses
- [ ] Configure endpoint-specific limits
- [ ] Add rate limit headers to responses

### Week 3: Observability
- [ ] Implement rate limit metrics
- [ ] Create Grafana dashboard
- [ ] Add Prometheus alerts for violations
- [ ] Integrate with OpenTelemetry tracing
- [ ] Write integration tests

### Week 4: Testing & Rollout
- [ ] Load test: Verify limits are enforced
- [ ] Chaos test: Kill Redis, verify fail-open
- [ ] User acceptance test: Verify error messages
- [ ] Deploy to staging (log-only mode)
- [ ] Monitor for 1 week, tune limits

### Week 5: Production
- [ ] Deploy to production (10% traffic)
- [ ] Monitor metrics, watch for issues
- [ ] Gradually increase to 100% over 2 weeks
- [ ] Document troubleshooting guide

## Testing Strategy

### Unit Tests
```python
def test_rate_limit_enforcement():
    """Test that rate limit is enforced correctly"""
    client = TestClient(app)

    # Make 60 requests (at limit)
    for i in range(60):
        response = client.post("/api/v1/agent_chat", json={"message": "test"})
        assert response.status_code == 200

    # 61st request should be rate limited
    response = client.post("/api/v1/agent_chat", json={"message": "test"})
    assert response.status_code == 429
    assert "rate_limit_exceeded" in response.json()["error"]["code"]

def test_tier_based_limits():
    """Test that premium users have higher limits"""
    # Free tier: 60 req/min
    # Premium tier: 1000 req/min
    # ... test implementation
```

### Integration Tests
```bash
# Load test with k6
k6 run --vus 100 --duration 60s tests/load/rate_limit_test.js

# Verify 429 responses under load
# Verify rate limit headers are present
# Verify Redis is used for distributed limiting
```

### Chaos Tests
```bash
# Kill Redis mid-test, verify fail-open behavior
docker-compose stop redis
# Requests should still work (degraded mode)

# Restart Redis, verify recovery
docker-compose start redis
```

## Migration Path

### Phase 1: Log-Only (Week 1)
- Deploy rate limiter in `log_only` mode
- Collect metrics on who would be rate limited
- Tune limits based on actual usage

### Phase 2: Soft Enforcement (Week 2-3)
- Switch to `enforce` mode for anonymous users only
- Monitor impact, adjust limits
- Communicate with users about upcoming enforcement

### Phase 3: Full Enforcement (Week 4+)
- Enable for all users
- Monitor closely for regressions
- Provide upgrade paths for users hitting limits

## References

- **OWASP Rate Limiting**: https://cheatsheetseries.owasp.org/cheatsheets/Denial_of_Service_Cheat_Sheet.html
- **slowapi Library**: https://github.com/laurents/slowapi
- **Kong Rate Limiting**: https://docs.konghq.com/hub/kong-inc/rate-limiting/
- **Google Cloud Armor**: https://cloud.google.com/armor/docs/rate-limiting-overview
- **ADR-0030: Resilience Patterns**: ./adr-0026-resilience-patterns.md
- **Kong Integration Guide**: ../integrations/kong.md

## Success Metrics

### Security
- **Target**: 0 successful DoS attacks
- **Measurement**: No service degradation from single source

### Performance
- **Target**: < 2ms latency overhead from rate limiting
- **Measurement**: P95 latency with vs without rate limiting

### User Experience
- **Target**: < 1% of legitimate requests rate limited
- **Measurement**: `rate_limit_exceeded_total / http_requests_total < 0.01`

### Cost Control
- **Target**: LLM costs capped at $X per user per day
- **Measurement**: Daily cost tracking per user ID

---

**Last Updated**: 2025-10-20
**Next Review**: 2025-11-20 (after 1 month in production)
