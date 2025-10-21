# Bug Investigation: [Bug Title]

**Date**: YYYY-MM-DD
**Reporter**: [Name]
**Severity**: [Critical | High | Medium | Low]
**Status**: [New | Investigating | Root Cause Found | Fixed | Verified]
**Related Issue**: #[issue-number]

---

## Summary

**One-line Description**: [Brief description of the bug]

**Impact**:
- Affected users: [Number/percentage of users]
- Affected functionality: [What features are broken]
- Business impact: [Revenue/reputation/compliance impact]

**Environment**:
- Production | Staging | Development
- Version/Commit: [git hash or version number]
- Deployment date: [When was this version deployed]

---

## Bug Report

### Steps to Reproduce

1. [First step]
2. [Second step]
3. [Third step]
4. [Continue until bug occurs]

**Minimal Reproduction** (if available):
```python
# Minimal code that reproduces the issue
async def reproduce_bug():
    # Step 1
    session = create_session()

    # Step 2
    result = await session.login("user@example.com")

    # Bug occurs here
    assert result is not None  # AssertionError
```

### Expected Behavior

[What should happen]

**Example**:
```
User should be logged in successfully and receive a session token.
Response should be:
{
  "success": true,
  "session_id": "sess-abc-123"
}
```

### Actual Behavior

[What actually happens]

**Example**:
```
User login fails with 500 Internal Server Error.
Response:
{
  "error": "Internal Server Error",
  "incident_id": "inc-xyz-789"
}
```

### Error Messages

**Error Logs**:
```
[2025-10-20 14:30:45] ERROR: Unhandled exception in /auth/login
Traceback (most recent call last):
  File "src/api/auth.py", line 123, in login
    session = await get_session_store().create(user_id)
  File "src/auth/session.py", line 45, in create
    raise AttributeError("'NoneType' object has no attribute 'create'")
AttributeError: 'NoneType' object has no attribute 'create'
```

**Stack Trace**:
```
Full stack trace if different from error logs
```

### Screenshots/Videos

[Attach any visual evidence]

- Screenshot of error page: [link or attachment]
- Video of reproduction: [link]
- Network request/response: [HAR file or screenshot]

---

## Investigation

### Initial Analysis

**What do we know?**
- Error occurs in `src/auth/session.py:45`
- `get_session_store()` is returning `None`
- Only happens in production (works in staging)
- Started occurring after deployment at 2025-10-20 13:00

**What don't we know?**
- Why is `get_session_store()` returning `None`?
- When was the session store initialized?
- Are there any configuration differences between staging and production?

### Hypothesis

**Primary Hypothesis**:
`get_session_store()` returns `None` because the session store was not initialized properly in the production environment.

**Supporting Evidence**:
- Session store initialization happens in `app startup event`
- Production logs don't show startup event completion
- Staging logs show "Session store initialized successfully"

**Alternative Hypotheses**:
1. Race condition: Request arrives before initialization complete
2. Environment variable missing in production
3. Redis connection fails silently

### Investigation Steps

#### Step 1: Check Logs

**Command**:
```bash
# Check for initialization logs
grep -i "session.*init" production.log

# Check for errors during startup
grep -i "error\|exception" production.log | head -50

# Check for Redis connection
grep -i "redis" production.log
```

**Findings**:
```
[2025-10-20 13:00:15] INFO: Starting application...
[2025-10-20 13:00:16] INFO: Loading configuration...
[2025-10-20 13:00:17] ERROR: Failed to connect to Redis: Connection refused
[2025-10-20 13:00:17] WARNING: Session store not initialized, skipping...
[2025-10-20 13:00:18] INFO: Application started
```

**Analysis**: Redis connection failed, session store initialization skipped.

#### Step 2: Check Configuration

**Command**:
```bash
# Compare production vs staging config
diff <(kubectl get configmap app-config -n production -o yaml) \
     <(kubectl get configmap app-config -n staging -o yaml)
```

**Findings**:
```diff
  REDIS_HOST: redis-service
- REDIS_PORT: 6379
+ REDIS_PORT: 6380  # ← Different port in production!
```

**Analysis**: Production is configured to use port 6380, but Redis is running on 6379.

#### Step 3: Verify Services

**Command**:
```bash
# Check if Redis is running
kubectl get pods -n production | grep redis

# Check Redis service configuration
kubectl get svc redis-service -n production -o yaml
```

**Findings**:
```
redis-service:
  ports:
  - port: 6379  # Service exposes 6379
  - targetPort: 6379
```

**Analysis**: Redis service exposes port 6379, but config says 6380.

### Root Cause

**Root Cause**: Configuration mismatch

**Details**:
- Production ConfigMap has `REDIS_PORT=6380`
- Redis service actually runs on port 6379
- Connection fails during startup
- Session store initialization skips on connection failure
- Subsequent requests fail with `NoneType` error

**Why This Happened**:
- ConfigMap was manually edited in production
- Change was made to test something and not reverted
- No validation that Redis connection succeeds before marking app as "ready"

**Why Wasn't It Caught**:
- Staging has correct configuration (6379)
- Integration tests use in-memory session store (no Redis)
- Health check doesn't verify session store (only checks app is responding)

### Timeline

| Time | Event |
|------|-------|
| 2025-10-19 16:00 | Someone manually edited production ConfigMap |
| 2025-10-20 13:00 | New deployment rolled out |
| 2025-10-20 13:00 | App starts, Redis connection fails |
| 2025-10-20 13:01 | First user login fails |
| 2025-10-20 13:15 | Support tickets start coming in |
| 2025-10-20 13:30 | Incident declared |
| 2025-10-20 14:00 | Investigation started |
| 2025-10-20 14:30 | Root cause identified |

**Time to Detect**: 30 minutes
**Time to Identify**: 1 hour

---

## Fix

### Immediate Fix (Hot Patch)

**Action**: Revert ConfigMap to correct value

```bash
# Fix production ConfigMap
kubectl edit configmap app-config -n production
# Change REDIS_PORT from 6380 to 6379

# Rolling restart to pick up new config
kubectl rollout restart deployment app -n production

# Verify fix
kubectl logs -f deployment/app -n production | grep "Session store"
# Should see: "Session store initialized successfully"
```

**Status**: ✅ Applied at 2025-10-20 14:35
**Verification**: User logins working again

### Proper Fix

**Changes Required**:

1. **Add configuration validation**:
```python
# src/core/config.py

async def validate_config(settings: Settings):
    """Validate configuration on startup."""
    # Try connecting to Redis
    try:
        redis = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            socket_connect_timeout=5,
        )
        await redis.ping()
        logger.info("✓ Redis connection successful")
    except Exception as e:
        logger.error(f"✗ Redis connection failed: {e}")
        raise RuntimeError("Invalid Redis configuration")
```

2. **Improve health check**:
```python
# src/api/health.py

@router.get("/healthz")
async def health_check():
    """Comprehensive health check."""
    checks = {
        "app": "ok",
        "redis": await check_redis(),
        "session_store": await check_session_store(),
    }

    if any(v != "ok" for v in checks.values()):
        raise HTTPException(status_code=503, detail=checks)

    return checks
```

3. **Add integration test**:
```python
# tests/integration/test_config.py

async def test_production_config_valid():
    """Ensure production config is valid."""
    # Load production config
    prod_config = load_config("production")

    # Validate Redis connection
    redis = Redis(host=prod_config.redis_host, port=prod_config.redis_port)
    assert await redis.ping() is True
```

4. **Prevent manual ConfigMap edits**:
```yaml
# kustomization.yaml
configMapGenerator:
- name: app-config
  literals:
  - REDIS_HOST=redis-service
  - REDIS_PORT=6379  # Managed by Kustomize, not manual edits
```

**PR**: #[pr-number]
**Status**: [In Review | Merged | Deployed]

---

## Testing

### Verification Steps

**After Fix**:
1. ✅ User login works in production
2. ✅ Session creation succeeds
3. ✅ Health check shows all services healthy
4. ✅ No errors in logs related to session store

**Regression Test**:
```python
async def test_session_store_initialization_failure():
    """Test that app fails fast if session store init fails."""
    # Mock Redis connection failure
    with patch("redis.asyncio.Redis.ping", side_effect=ConnectionError):
        with pytest.raises(RuntimeError, match="Invalid Redis configuration"):
            await initialize_app()
```

**Manual Testing Checklist**:
- [ ] User login works
- [ ] Session persists across requests
- [ ] Session expires after timeout
- [ ] Health check reports Redis status
- [ ] App fails to start if Redis unavailable

---

## Prevention

### Immediate Actions

1. ✅ Revert configuration to correct value
2. ✅ Add alerting for session store initialization failures
3. ✅ Update runbook with configuration validation steps

### Short-term Actions (Next Sprint)

- [ ] Implement configuration validation on startup
- [ ] Improve health check to verify all dependencies
- [ ] Add integration test for production configuration
- [ ] Document Redis connection requirements

### Long-term Actions (Next Quarter)

- [ ] Move to GitOps - no manual ConfigMap edits
- [ ] Implement configuration drift detection
- [ ] Add synthetic monitoring for critical paths
- [ ] Improve observability (trace session store init)

### Lessons Learned

**What Went Well**:
- Error was logged clearly
- Investigation was systematic
- Fix was straightforward once root cause found

**What Could Be Better**:
- Detection took 30 minutes (should be instant)
- Health check didn't catch the issue
- Manual ConfigMap edits shouldn't be possible

**Process Improvements**:
1. **Fail Fast**: App should refuse to start if dependencies unavailable
2. **Validation**: Configuration should be validated on startup
3. **Monitoring**: Alert on initialization failures immediately
4. **GitOps**: Prevent manual configuration changes

---

## Related Issues

**Similar Issues**:
- #123 - Database connection failure not caught by health check
- #456 - Environment variable typo caused silent failure

**Prevented By This Fix**:
- Future Redis misconfigurations
- Other dependency initialization failures

---

## Metrics

**Impact**:
- Users affected: ~500 (10% of daily active users)
- Failed logins: ~1,200
- Support tickets: 15
- Revenue impact: $0 (no paid features affected)

**Resolution**:
- Time to detect: 30 minutes
- Time to fix: 1 hour 5 minutes (from detection to deployment)
- Total downtime: 1 hour 35 minutes

**Cost**:
- Engineering time: 3 hours (investigation + fix + review)
- Support time: 2 hours (handling tickets)
- Customer impact: Medium (inconvenience, no data loss)

---

## Appendix

### Relevant Code

**Session Store Initialization** (`src/auth/session.py:25-50`):
```python
_session_store: Optional[SessionStore] = None

def get_session_store() -> SessionStore:
    """Get the global session store instance."""
    global _session_store
    if _session_store is None:
        logger.warning("Session store not initialized!")
        # BUG: Returns None instead of raising exception
    return _session_store

async def initialize_session_store(settings: Settings):
    """Initialize the session store."""
    global _session_store
    try:
        redis = Redis(host=settings.redis_host, port=settings.redis_port)
        _session_store = RedisSessionStore(redis)
        logger.info("Session store initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize session store: {e}")
        # BUG: Silently continues instead of failing
```

### Configuration Files

**Production ConfigMap** (before fix):
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  REDIS_HOST: redis-service
  REDIS_PORT: "6380"  # ← Wrong port
```

**Production ConfigMap** (after fix):
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  REDIS_HOST: redis-service
  REDIS_PORT: "6379"  # ← Correct port
```

---

**Investigation Complete**: 2025-10-20 14:45
**Fix Applied**: 2025-10-20 14:35
**Verified**: 2025-10-20 14:40
**Status**: ✅ RESOLVED

---

## Template Usage Guide

### When to Use This Template

Use this template for:
- Production incidents requiring root cause analysis
- Complex bugs that need systematic investigation
- Issues affecting multiple users
- Bugs that need to be prevented in future

### How to Fill Out

1. **Start with Summary**: Capture initial report and impact
2. **Document Reproduction**: Write down exact steps while fresh
3. **Investigation**: Update as you learn more (don't wait until end)
4. **Root Cause**: Be specific about WHY, not just WHAT
5. **Fix**: Document both hotfix and proper fix
6. **Prevention**: Focus on systemic improvements

### Tips

- **Be detailed**: Future you will thank you
- **Include evidence**: Logs, screenshots, diffs
- **Timeline matters**: When did it start? When detected? When fixed?
- **Think prevention**: How do we avoid this class of bugs?
- **Share learnings**: Post-mortem with team

---

**Template Version**: 1.0
**Last Updated**: 2025-10-20
**Based On**: Post-mortem best practices
