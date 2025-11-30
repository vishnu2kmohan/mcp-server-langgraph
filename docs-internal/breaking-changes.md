# Breaking Changes

This document tracks breaking changes across versions of mcp-server-langgraph.

## v2.8.0 (Pending Release)

### **BREAKING: Observability Requires Explicit Initialization**

**Impact:** High - affects all entry points and library usage

**What Changed:**
- Observability (telemetry, logging, tracing) is no longer initialized automatically at module import time
- Entry points MUST explicitly call `init_observability(settings)` before using observability features
- File-based log rotation is now **opt-in** via `enable_file_logging=True`

**Why:**
This change fixes critical operational issues:
1. **Circular Import Fix**: Resolves `config → secrets.manager → telemetry → config` circular dependency
2. **Library Reusability**: Package can now be imported without triggering filesystem writes or requiring configuration
3. **Container-Friendly**: Works in read-only containers, serverless environments, and ephemeral pods
4. **Configuration Respect**: `settings.log_format` and `langsmith_tracing` are now properly honored (previously fell back to defaults due to import-time race condition)

**Migration Required:**

**Before (v2.7.0 and earlier):**
```python
# main.py
from mcp_server_langgraph.observability.telemetry import logger, tracer

# Observability was auto-initialized on import
logger.info("Server starting")  # Just worked

def main():
    server = MCPAgentServer()
    await server.run()
```

**After (v2.8.0+):**
```python
# main.py
async def main():
    # Initialize observability FIRST (before using logger/tracer)
    from mcp_server_langgraph.observability.telemetry import init_observability
    from mcp_server_langgraph.core.config import settings

    init_observability(
        settings=settings,
        enable_file_logging=True  # Opt-in for file-based logging
    )

    # NOW safe to use logger/tracer
    from mcp_server_langgraph.observability.telemetry import logger
    logger.info("Server starting")

    server = MCPAgentServer()
    await server.run()
```

**For Tests:**
```python
# conftest.py (already updated)
def pytest_configure(config):
    from mcp_server_langgraph.observability.telemetry import init_observability
    from mcp_server_langgraph.core.config import Settings

    test_settings = Settings(
        log_format="text",
        enable_file_logging=False,  # No file logging in tests
        langsmith_tracing=False
    )
    init_observability(settings=test_settings)
```

**Error if Not Initialized:**
```python
# This will raise RuntimeError if you forget to initialize
from mcp_server_langgraph.observability.telemetry import logger
logger.info("Hello")  # RuntimeError: Observability not initialized
```

**Files Modified:**
- `src/mcp_server_langgraph/observability/telemetry.py` (+168, -21)
- `src/mcp_server_langgraph/secrets/manager.py` (+50, -3) - now works before observability init
- `src/mcp_server_langgraph/mcp/server_stdio.py` (+10) - adds `init_observability()` call
- `tests/conftest.py` (+13) - adds `pytest_configure()` hook

**Settings Added:**
- `enable_file_logging: bool = False` - Opt-in file-based log rotation

**References:**
- Issue: #ultrathink-issue-1 (Decouple observability bootstrapping from import time)
- ADR-0026: Lazy Observability Initialization
- Migration Guide: See `MIGRATION.md`

---

### **NEW: Multi-Provider Fallback Credential Support**

**Impact:** Medium - affects deployments using LLM fallback models

**What Changed:**
- LLMFactory now provisions credentials for **all** fallback providers, not just the primary provider
- Startup validation warns if fallback models are configured without required API keys
- `_get_provider_from_model(model_name)` extracts provider from model name (e.g., "gpt-4o" → "openai")

**Why:**
The default fallback configuration `fallback_models = ["claude-haiku-4-5", "claude-sonnet-4-5", "gpt-4o"]` with `llm_provider="google"` previously failed at runtime because:
- Primary provider (Google) credentials were set
- Fallback providers (Anthropic, OpenAI) credentials were NOT set
- Result: Fallback attempt → authentication failure

**Migration Required:**

**Before (v2.7.0 and earlier):**
```bash
# .env
GOOGLE_API_KEY=your-google-key
# Fallback to gpt-4o would FAIL (no OPENAI_API_KEY)
```

**After (v2.8.0+):**
```bash
# .env - Provide keys for ALL providers used in fallbacks
GOOGLE_API_KEY=your-google-key
ANTHROPIC_API_KEY=your-anthropic-key  # For claude-* fallbacks
OPENAI_API_KEY=your-openai-key        # For gpt-* fallbacks
```

**Validation at Startup:**
```
WARNING: Fallback models configured without required credentials.
         These fallbacks will fail at runtime if the primary provider fails.
  - Model 'claude-haiku-4-5' (provider: anthropic) requires 'ANTHROPIC_API_KEY' environment variable
  - Model 'gpt-4o' (provider: openai) requires 'OPENAI_API_KEY' environment variable
```

**Files Modified:**
- `src/mcp_server_langgraph/llm/factory.py` (+91, -12)
- `src/mcp_server_langgraph/core/config.py` (+44) - adds `_validate_fallback_credentials()`

**References:**
- Issue: #ultrathink-issue-3 (Revisit multi-provider fallback defaults)

---

### **NEW: Mock Resources for Development Mode (OpenFGA Disabled)**

**Impact:** Low - improves developer experience

**What Changed:**
- `AuthMiddleware.list_accessible_resources()` now returns mock sample data when OpenFGA is not configured
- Only enabled in `environment="development"` with `enable_mock_authorization=True` (default)
- Provides 4 sample conversations, 3 tools, 3 users out-of-box

**Why:**
Previously, `conversation_search` returned "no conversations" without OpenFGA, making the tool unusable for local development and demos.

**Migration:**
No migration required - this is a non-breaking enhancement. To disable:

```python
# .env
ENABLE_MOCK_AUTHORIZATION=false  # Disable mock data
```

**Mock Data Provided:**
- Tools: `tool:agent_chat`, `tool:conversation_get`, `tool:conversation_search`
- Conversations: `conversation:demo_thread_1`, `conversation:demo_thread_2`, `conversation:demo_thread_3`, `conversation:sample_conversation`
- Users: `user:alice`, `user:bob`, `user:charlie`

**Files Modified:**
- `src/mcp_server_langgraph/auth/middleware.py` (+39) - adds `_get_mock_resources()`
- `src/mcp_server_langgraph/core/config.py` (+3) - adds `enable_mock_authorization` setting

**References:**
- Issue: #ultrathink-issue-4 (Improve developer-mode behavior when OpenFGA is disabled)

---

## How to Upgrade

See [MIGRATION.md](./migrations/MIGRATION.md) for detailed upgrade instructions.

## Support

- **GitHub Issues**: Report issues at https://github.com/your-org/mcp-server-langgraph/issues
- **Documentation**: https://docs.yoursite.com
- **Migration Guide**: [MIGRATION.md](./migrations/MIGRATION.md)
