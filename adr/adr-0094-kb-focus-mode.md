# ADR-0094: Knowledge Base Focus Mode

| Status | Accepted |
|--------|----------|
| Date | 2026-01-06 |
| Authors | Claude Opus 4.5 |
| Deciders | Backend Architecture, Frontend UX |
| Consulted | LLM Integration, Product |
| Informed | All Contributors |

## Context and Problem Statement

The system uses `DynamicContextLoader` to perform semantic search against a Qdrant vector store, injecting relevant context into LLM prompts. However, users had no control over this context retrieval behavior:

1. **All-or-Nothing**: Context augmentation was always on or always off based on feature flags
2. **No User Control**: Users couldn't disable context injection for simple queries or enable web-only search
3. **Perplexity-Style UX**: Modern AI assistants (Perplexity, ChatGPT with browsing) let users toggle between knowledge sources

### Problem Statement

How do we give users granular control over context retrieval strategy, similar to Perplexity's "Focus" feature, while maintaining backward compatibility and clean API design?

## Decision Drivers

1. **User Agency**: Users should control when/how context is injected
2. **Perplexity Parity**: Match UX patterns users expect from modern AI products
3. **Backend Integration**: Support focus modes in the streaming endpoint and DynamicContextLoader
4. **Feature Flag Gating**: `enable_kb_focus` flag allows gradual rollout
5. **Type Safety**: Use Literal types for validated mode values
6. **Fail-Soft**: If KB is unavailable, gracefully degrade without breaking chat

## Decision

Implement KB Focus Mode with four modes: `"all"`, `"kb_only"`, `"web_only"`, `"none"`.

### Focus Modes

| Mode | KB Search | Web Search | Use Case |
|------|-----------|------------|----------|
| `"all"` (default) | Yes | Yes* | Full context augmentation |
| `"kb_only"` | Yes | No | Use only internal knowledge base |
| `"web_only"` | No | Yes* | Skip KB, use external sources only |
| `"none"` | No | No | Raw LLM response, no augmentation |

*Note: Web search is not yet implemented; `web_only` mode returns empty context pending future implementation.

### Implementation

#### 1. Backend: ChatCompletionRequest (`chat.py`)

Added `kb_focus` field to the Pydantic model:

```python
# Knowledge Base focus mode (Perplexity-style context retrieval control)
kb_focus: Literal["all", "kb_only", "web_only", "none"] = Field(
    default="all",
    description="Knowledge Base focus mode controlling context retrieval strategy. "
    "'all' = use both KB and web search (default), "
    "'kb_only' = only use KB/vector store for context, "
    "'web_only' = only use web search for context, "
    "'none' = disable context augmentation.",
)
```

The streaming endpoint passes `kb_focus` to the service:

```python
kb_focus=request.kb_focus,
```

#### 2. Backend: DynamicContextLoader (`dynamic_context_loader.py`)

Added `KBFocusMode` type alias and `focus_mode` parameter to convenience function:

```python
# Type alias for KB focus mode
KBFocusMode = Literal["all", "kb_only", "web_only", "none"]

async def search_and_load_context(
    query: str,
    loader: DynamicContextLoader | None = None,
    top_k: int = 3,
    max_tokens: int = 2000,
    focus_mode: KBFocusMode = "all",
) -> list[LoadedContext]:
    # Handle focus modes that skip KB search
    if focus_mode == "none":
        return []  # No context augmentation
    if focus_mode == "web_only":
        return []  # Skip KB (web not yet implemented)

    # For "all" and "kb_only" modes, perform KB semantic search
    if loader is None:
        loader = DynamicContextLoader()
    references = await loader.semantic_search(query, top_k=top_k)
    loaded = await loader.load_batch(references, max_tokens=max_tokens)
    return loaded
```

#### 3. Frontend: KnowledgeBaseFocus Component

New component with segment control for focus mode selection:

```tsx
<KnowledgeBaseFocus
  value={focusMode}
  onChange={setFocusMode}
  kbStatus={kbStatusForUI}  // Shows status indicator
  disabled={!isKBReady}
/>
```

Visual states:
- **All**: Globe + Database icon (both sources)
- **KB Only**: Database icon (internal knowledge)
- **Web Only**: Globe icon (external sources)
- **None**: Slash-through icon (no augmentation)

#### 4. Frontend: StatusBar KB Indicator

StatusBar shows KB status when `kb_focus` feature flag is enabled:

```tsx
kbStatus={kbFocusEnabled ? kbStatus : undefined}
kbStatusMessage={kbFocusEnabled ? kbStatusMessage : undefined}
kbContextStats={kbFocusEnabled ? kbContextStats : undefined}
```

Status colors:
- **Green (ready)**: KB connected and operational
- **Yellow (misconfigured)**: Configuration needed (shows guidance)
- **Gray (unavailable)**: Cannot connect to Qdrant

### Feature Flag

```python
# FeatureFlags class
enable_kb_focus: bool = Field(
    default=True,
    description="Enable KB Focus Mode UI controls"
)
```

- **Default**: `True` (enabled by default - production-ready feature)
- **Environment**: `FF_ENABLE_KB_FOCUS=false` to disable

### Test Coverage

Created 18 unit tests covering:

1. **ChatCompletionRequest tests** (`test_chat_kb_focus.py`):
   - Model has `kb_focus` field
   - Default value is `"all"`
   - Accepts valid Literal values
   - Rejects invalid values with ValidationError
   - Streaming endpoint passes `kb_focus` to service
   - Feature flag exists and defaults to True

2. **DynamicContextLoader tests** (`test_dynamic_context_loader_kb_focus.py`):
   - `search_and_load_context` accepts `focus_mode` parameter
   - `"none"` returns empty list without calling search
   - `"web_only"` returns empty list (KB search skipped)
   - `"kb_only"` performs semantic search
   - `"all"` performs semantic search
   - Default is `"all"` (backward compatible)

## Consequences

### Positive

1. **User Control**: Users can now tune context retrieval per-query
2. **Perplexity Parity**: Matches expected UX from modern AI products
3. **Backward Compatible**: Default `"all"` preserves existing behavior
4. **Type Safe**: Literal types prevent invalid mode values
5. **Fail-Soft**: Unknown modes default to safe behavior

### Negative

1. **Web Search Not Implemented**: `"web_only"` mode currently returns empty context
2. **Additional Complexity**: More states to manage in frontend and backend

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Users confused by empty context in web_only mode | Show tooltip explaining web search coming soon |
| KB misconfigured shows poor UX | StatusBar shows clear guidance message |
| Performance impact of checking focus mode | Mode check is O(1) string comparison |

## Related ADRs

- **ADR-0091**: API Response Transformation Strategy (type safety patterns)
- **ADR-0089**: Prompt Architecture Centralization (context injection patterns)
- **ADR-0092**: Hierarchical Capability Architecture (feature flag patterns)

## Future Work

1. **Web Search Integration**: Implement actual web search for `"web_only"` and `"all"` modes
2. **Focus Mode Persistence**: Remember user's preferred focus mode per session
3. **Context Preview**: Show what context will be injected before sending
4. **Per-Source Attribution**: Show which context came from KB vs web
