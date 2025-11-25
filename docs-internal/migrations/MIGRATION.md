# Migration Guide: v2.7 → v2.8

This guide helps you upgrade from v2.7.x to v2.8.0, which includes operational hardening improvements and breaking changes to observability initialization.

## Overview of Changes

v2.8.0 introduces significant improvements to operational ergonomics:

- ✅ **Fixed**: Circular import between config, secrets, and telemetry
- ✅ **Fixed**: Observability settings not being honored due to import-time race conditions
- ✅ **Improved**: Package can now be used as a library without filesystem operations
- ✅ **Improved**: Container-friendly (works in read-only filesystems)
- ✅ **Improved**: Multi-provider fallback with proper credential validation
- ✅ **Improved**: Developer experience with mock data when OpenFGA is disabled

⚠️ **Breaking**: Observability requires explicit initialization in entry points

---

## Quick Migration Checklist

- [ ] Update all entry points to call `init_observability(settings)` before using logger/tracer
- [ ] Update `.env` with API keys for all fallback providers (if using multi-provider fallback)
- [ ] Set `ENABLE_FILE_LOGGING=true` if you need file-based log rotation (now opt-in)
- [ ] Review test fixtures - `conftest.py` updated automatically
- [ ] Remove any custom observability initialization workarounds
- [ ] Test in development environment
- [ ] Deploy to staging and verify observability works
- [ ] Deploy to production

---

## Step 1: Update Entry Points

### Main Application Entry Point

**File**: `src/mcp_server_langgraph/mcp/server_stdio.py` (or your custom entry point)

**Before (v2.7.0):**
```python
import asyncio
from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer
from mcp_server_langgraph.observability.telemetry import logger  # Auto-initialized

async def main():
    logger.info("Starting server")  # Just worked
    server = MCPAgentServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
```

**After (v2.8.0):**
```python
import asyncio

async def main():
    # STEP 1: Initialize observability FIRST
    from mcp_server_langgraph.observability.telemetry import init_observability
    from mcp_server_langgraph.core.config import settings

    init_observability(
        settings=settings,
        enable_file_logging=True  # Set to True if you need file-based logging
    )

    # STEP 2: Now safe to import and use logger
    from mcp_server_langgraph.observability.telemetry import logger
    from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

    logger.info("Starting server")
    server = MCPAgentServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
```

### FastAPI/Starlette Applications

**File**: `main.py` or app startup

**Before:**
```python
from fastapi import FastAPI
from mcp_server_langgraph.observability.telemetry import logger

app = FastAPI()

@app.on_event("startup")
async def startup():
    logger.info("API server starting")
```

**After:**
```python
from fastapi import FastAPI

app = FastAPI()

@app.on_event("startup")
async def startup():
    # Initialize observability first
    from mcp_server_langgraph.observability.telemetry import init_observability
    from mcp_server_langgraph.core.config import settings

    init_observability(settings=settings, enable_file_logging=True)

    # Now safe to use logger
    from mcp_server_langgraph.observability.telemetry import logger
    logger.info("API server starting")
```

### Custom Scripts

**Before:**
```python
#!/usr/bin/env python
from mcp_server_langgraph.observability.telemetry import logger
from mcp_server_langgraph.core.config import settings

# Do work
logger.info(f"Processing {settings.model_name}")
```

**After:**
```python
#!/usr/bin/env python
from mcp_server_langgraph.observability.telemetry import init_observability
from mcp_server_langgraph.core.config import settings

# Initialize first
init_observability(settings=settings, enable_file_logging=False)

# Now use logger
from mcp_server_langgraph.observability.telemetry import logger
logger.info(f"Processing {settings.model_name}")
```

---

## Step 2: Update Environment Configuration

### File Logging (Now Opt-In)

File-based log rotation is now **opt-in** to support read-only containers and serverless environments.

**Option 1: Environment Variable**
```bash
# .env
ENABLE_FILE_LOGGING=true  # Enable file rotation
```

**Option 2: Code**
```python
init_observability(settings=settings, enable_file_logging=True)
```

**Option 3: Settings Class**
```python
from mcp_server_langgraph.core.config import Settings

settings = Settings(enable_file_logging=True)
init_observability(settings=settings)
```

**Default Behavior (v2.8.0):**
- Console logging: ✅ Always enabled
- File logging: ❌ Disabled by default (opt-in)

**Previous Behavior (v2.7.0):**
- Console logging: ✅ Always enabled
- File logging: ✅ Always enabled (even in containers)

### Multi-Provider Fallback

If you use multiple providers in your fallback chain, you must now configure API keys for **all** providers.

**Example Fallback Configuration:**
```python
# config.py or .env
llm_provider="google"
fallback_models=["claude-haiku-4-5", "claude-sonnet-4-5", "gpt-4o"]
```

**Required Environment Variables:**
```bash
# .env
GOOGLE_API_KEY=your-google-key          # Primary provider
ANTHROPIC_API_KEY=your-anthropic-key    # For claude-* fallbacks
OPENAI_API_KEY=your-openai-key          # For gpt-* fallbacks
```

**Startup Validation:**
v2.8.0 warns you at startup if fallback models are missing credentials:

```
WARNING: Fallback models configured without required credentials.
  - Model 'claude-haiku-4-5' (provider: anthropic) requires 'ANTHROPIC_API_KEY'
  - Model 'gpt-4o' (provider: openai) requires 'OPENAI_API_KEY'
```

---

## Step 3: Update Tests

### Pytest Configuration (Already Updated)

The `tests/conftest.py` file has been updated with a `pytest_configure()` hook that automatically initializes observability for all tests.

**What Changed:**
```python
# tests/conftest.py
def pytest_configure(config):
    """Initialize observability system for tests."""
    from mcp_server_langgraph.observability.telemetry import init_observability
    from mcp_server_langgraph.core.config import Settings

    test_settings = Settings(
        log_format="text",
        enable_file_logging=False,  # No file logging in tests
        langsmith_tracing=False,
        observability_backend="opentelemetry"
    )
    init_observability(settings=test_settings)
```

**Action Required:**
- ✅ None - `conftest.py` is already updated
- ✅ Your existing tests should continue to work

### Custom Test Fixtures

If you have custom test fixtures that initialize observability, update them:

**Before:**
```python
@pytest.fixture
def custom_logger():
    from mcp_server_langgraph.observability.telemetry import logger
    return logger  # Auto-initialized
```

**After:**
```python
@pytest.fixture
def custom_logger():
    from mcp_server_langgraph.observability.telemetry import init_observability, logger, is_initialized

    # Initialize if not already done
    if not is_initialized():
        init_observability(enable_file_logging=False)

    return logger
```

---

## Step 4: Update Docker/Kubernetes Deployments

### Docker

No changes required to Dockerfiles, but you may want to enable file logging for production containers with persistent volumes.

**Option 1: Environment Variable**
```dockerfile
# Dockerfile
ENV ENABLE_FILE_LOGGING=true
```

**Option 2: docker-compose.yml**
```yaml
services:
  mcp-server:
    environment:
      - ENABLE_FILE_LOGGING=true
    volumes:
      - ./logs:/app/logs  # Mount volume for logs
```

### Kubernetes

Update ConfigMaps or Secrets:

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-server-config
data:
  ENABLE_FILE_LOGGING: "true"
  # Multi-provider fallback credentials
  GOOGLE_API_KEY: "..."
  ANTHROPIC_API_KEY: "..."
  OPENAI_API_KEY: "..."
```

**For Read-Only Root Filesystem:**
```yaml
# deployment.yaml
spec:
  template:
    spec:
      securityContext:
        readOnlyRootFilesystem: true
      containers:
      - name: mcp-server
        env:
        - name: ENABLE_FILE_LOGGING
          value: "false"  # Disable file logging for read-only FS
        volumeMounts:
        - name: tmp
          mountPath: /tmp  # Writable tmp for temporary files
      volumes:
      - name: tmp
        emptyDir: {}
```

---

## Step 5: Verify Migration

### Development Environment

1. **Test Import Without Init:**
   ```python
   python -c "from mcp_server_langgraph.observability import telemetry; print('Import successful')"
   # Should succeed without creating logs/ directory
   ```

2. **Test Lazy Init:**
   ```python
   from mcp_server_langgraph.observability.telemetry import logger
   try:
       logger.info("Test")
   except RuntimeError as e:
       print(f"Expected error: {e}")
   # Should raise: RuntimeError: Observability not initialized
   ```

3. **Test Full Initialization:**
   ```python
   from mcp_server_langgraph.observability.telemetry import init_observability
   from mcp_server_langgraph.core.config import Settings

   settings = Settings(enable_file_logging=False)
   init_observability(settings=settings)

   from mcp_server_langgraph.observability.telemetry import logger
   logger.info("Success!")
   # Should work without errors
   ```

4. **Test Multi-Provider Fallback:**
   ```bash
   # Set up environment
   export GOOGLE_API_KEY=your-key
   export ANTHROPIC_API_KEY=your-key
   export OPENAI_API_KEY=your-key

   # Start server - should not show credential warnings
   python -m mcp_server_langgraph.mcp.server_stdio
   ```

### Staging Environment

1. Deploy updated code
2. Check logs for observability initialization message
3. Verify no "Observability not initialized" errors
4. Test fallback behavior (if applicable)
5. Monitor metrics and traces

### Production Environment

1. **Canary Deployment**: Deploy to 1-2 nodes first
2. **Monitor**: Check logs, metrics, traces for 15-30 minutes
3. **Verify**: No RuntimeError exceptions
4. **Rollout**: Gradually deploy to all nodes
5. **Rollback Plan**: Keep v2.7.0 deployment ready

---

## Troubleshooting

### Error: "RuntimeError: Observability not initialized"

**Cause**: Using logger/tracer before calling `init_observability()`

**Solution:**
```python
# Add this at the top of your entry point
from mcp_server_langgraph.observability.telemetry import init_observability
from mcp_server_langgraph.core.config import settings

init_observability(settings=settings)
```

### Error: "ModuleNotFoundError: No module named 'mcp_server_langgraph.observability'"

**Cause**: Import order issue or circular import

**Solution:**
1. Initialize observability BEFORE importing other modules
2. Use lazy imports inside functions if needed

### Warning: "Fallback models configured without required credentials"

**Cause**: Missing API keys for fallback providers

**Solution:**
```bash
# .env - Add missing credentials
ANTHROPIC_API_KEY=your-key  # If using claude-* fallbacks
OPENAI_API_KEY=your-key     # If using gpt-* fallbacks
```

### No File Logs Created

**Cause**: File logging is now opt-in by default

**Solution:**
```bash
# .env
ENABLE_FILE_LOGGING=true
```
Or:
```python
init_observability(settings=settings, enable_file_logging=True)
```

### Tests Failing with "Observability not initialized"

**Cause**: Custom test fixtures not using updated initialization

**Solution:** Check that `tests/conftest.py` has the `pytest_configure()` hook (already added in v2.8.0)

---

## Rollback Instructions

If you encounter critical issues, you can rollback to v2.7.0:

```bash
# pip
pip install mcp-server-langgraph==2.7.0

# uv
uv pip install mcp-server-langgraph==2.7.0

# poetry
poetry add mcp-server-langgraph@2.7.0

# Kubernetes
kubectl set image deployment/mcp-server mcp-server=mcp-server-langgraph:2.7.0
```

After rollback:
1. Remove `init_observability()` calls
2. Revert `.env` changes
3. File logging will be enabled by default again

---

## Support

- **Issues**: https://github.com/your-org/mcp-server-langgraph/issues
- **Documentation**: [BREAKING_CHANGES.md](./BREAKING_CHANGES.md)
- **ADR**: [ADR-0026: Lazy Observability Initialization](../adr/adr-0026-lazy-observability-initialization.md)

---

**Migration completed?** ✅

Run the validation suite to confirm:
```bash
make test-all
make validate-all
```
