# ADR-0100: Frontend AI-Native Integration Consolidation

| Status   | Accepted                                     |
|----------|----------------------------------------------|
| Date     | 2026-01-08                                   |
| Category | Frontend Architecture                        |
| Authors  | Claude Code                                  |

## Context

The Studio frontend accumulated several AI-powered components that needed consolidation and documentation:

1. **AIEmptyState**: Empty state component with AI suggestions needed expansion to cover all page contexts
2. **CommandPalette**: Static command list needed dynamic route-aware registration
3. **GenUI Widgets**: Widget artifact type needed integration into the chat flow
4. **Chat Input Gap**: Shell path missing model selector, reasoning effort, and URL fetch features

### Problems with Prior Approach

1. **AIEmptyState Gaps**: Only 8 contexts defined, missing coverage for new pages (artifacts, prompts, tools, resources, audit)
2. **Static Commands**: CommandPalette only supported static commands defined at initialization
3. **No Widget Support**: Artifact parser didn't handle GenUI widget JSON blocks
4. **Feature Parity Gap**: ChatDocument had features not available in shell's ConnectedConversationPanel

### Goals

- Expand AIEmptyState to cover all 13 page contexts
- Enable dynamic command registration per route
- Support widget artifact type for GenUI
- Wire Chat Input features through shell path

## Decision

Implement a 4-part consolidation following the AI-Native Integration Plan:

### Part 1: Chat Input Feature Gap Fix

**Problem**: Main shell path missing advanced features available in ChatDocument.

**Solution**: Extend `ConnectedChatInputForm` with new props:

```typescript
interface ConnectedChatInputFormProps {
  // ... existing props ...

  // Model selection (Sprint 1)
  showModelSelector?: boolean;
  selectedModel?: string;
  availableModels?: ModelOption[];
  onModelChange?: (modelId: string) => void;

  // Reasoning effort (Sprint 1)
  modelSupportsThinking?: boolean;
  reasoningEffort?: ReasoningEffortLevel;
  onReasoningEffortChange?: (level: ReasoningEffortLevel) => void;
  enableThinking?: boolean;
  onEnableThinkingChange?: (enabled: boolean) => void;

  // URL fetch (Sprint 1)
  enableUrlFetch?: boolean;
}
```

**Feature Flags**:
- `model_selector_in_shell`: Enable model selector
- `url_fetch_in_shell`: Enable #url fetch pattern

### Part 2: AIEmptyState Migration

**Problem**: Limited context coverage and no persona-aware registry.

**Solution**: Expand `EmptyStateContext` type and registry:

```typescript
export type EmptyStateContext =
  | "sessions" | "projects" | "workflows" | "traces"
  | "messages" | "files" | "artifacts" | "alerts" | "connections"
  | "prompts" | "tools" | "resources" | "audit";  // 13 total
```

**Registry Pattern**:
- `EmptyStateRegistry.ts` provides default configs per context
- Persona-specific overrides applied based on user's sub-persona
- `emptyType` prop distinguishes "empty" vs "no-matches" states
- `onAction` callback supports modal-based CTAs

### Part 3: CommandPaletteContext Enhancement

**Problem**: Static command list couldn't adapt to current route.

**Solution**: Create `CommandPaletteContext` with dynamic registration:

```typescript
interface CommandPaletteContextValue {
  commands: Command[];  // Merged static + dynamic
  registerCommands: (commands: Command[]) => void;
  unregisterCommands: (ids: string[]) => void;
}
```

**Route Hook**:
```typescript
// useRouteCommands.ts
function useRouteCommands() {
  const { registerCommands, unregisterCommands } = useCommandPalette();

  useEffect(() => {
    const commands = getCommandsForRoute(pathname);
    registerCommands(commands);
    return () => unregisterCommands(commands.map(c => c.id));
  }, [pathname]);
}
```

**Deduplication**: Dynamic commands override static commands with same ID.

### Part 4: GenUI Widget Integration

**Problem**: Widget artifacts from LLM responses not rendered.

**Solution**: Add `WidgetArtifact` type and parser support:

```typescript
interface WidgetArtifact extends BaseArtifact {
  type: "widget";
  widgetType: "chart" | "table" | "text";
  config: {
    id: string;
    title: string;
    data: WidgetChartData | WidgetTableData | WidgetTextData;
  };
}
```

**Parser**: Fenced code blocks with `widget` language parsed to WidgetArtifact.

**Renderer**: `ArtifactRenderer` delegates to `GenerativeWidget` component.

## Consequences

### Positive

1. **Complete Coverage**: AIEmptyState now covers all 13 page contexts
2. **Dynamic Commands**: Route-aware command palette improves discoverability
3. **GenUI Support**: Widget artifacts enable rich chart/table/text rendering
4. **Feature Parity**: Shell path now supports model selection and URL fetch
5. **Persona Awareness**: Empty states adapt to user's sub-persona

### Negative

1. **Complexity**: CommandPaletteContext adds provider to layout tree
2. **Testing**: AIEmptyState requires Redux Provider in tests (personaSlice, sessionSlice)
3. **Memory**: Full test suite requires sharding due to 8GB heap limit

### Risks

1. **Widget Parsing**: Invalid widget JSON falls back to code artifact
2. **Route Commands**: Must cleanup on unmount to prevent stale commands

## Implementation Files

| Component | Files |
|-----------|-------|
| Chat Input | `ConnectedChatInputForm.tsx`, `ConversationPanel.tsx` |
| AIEmptyState | `EmptyState.tsx`, `EmptyStateRegistry.ts`, `AIEmptyState.tsx` |
| CommandPalette | `CommandPaletteContext.tsx`, `useRouteCommands.ts`, `StudioShellLayout.tsx` |
| GenUI Widget | `artifacts.ts`, `artifactParser.ts`, `ArtifactRenderer.tsx` |

## Related ADRs

- **ADR-0084**: StudioOrchestrator - Unified AI Intelligence Pattern (backend)
- **ADR-0093**: Chat Input Component Unification
- **ADR-0092**: Hierarchical Capability Architecture

## References

- `docs-internal/frontend/DESIGN_SYSTEM.md` - AI-Native Components section
- `docs-internal/frontend/feature-flags-mapping.md` - Sprint 4 feature flags
- `.claude/plans/lucky-crafting-hummingbird.md` - Original implementation plan
