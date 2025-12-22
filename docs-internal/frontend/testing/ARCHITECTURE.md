# Frontend Component Architecture

This document describes the component architecture patterns used in the Studio Frontend.

## Table of Contents

- [Layer Overview](#layer-overview)
- [Connected vs Presentational Components](#connected-vs-presentational-components)
- [Canvas Architecture](#canvas-architecture)
- [State Management](#state-management)

---

## Layer Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Pages                                 │
│  (Route components: ChatPage, MCPPage, AdminDashboardPage)  │
├─────────────────────────────────────────────────────────────┤
│                    Connected Components                      │
│  (Redux-connected: ConnectedCanvasPanel, HybridShellLayout) │
├─────────────────────────────────────────────────────────────┤
│                  Presentational Components                   │
│  (Pure UI: CanvasWorkspace, CanvasArtifact, CanvasTabs)     │
├─────────────────────────────────────────────────────────────┤
│                         Hooks                                │
│  (Business logic: useAISuggestionsFetch, useSaveArtifact)   │
├─────────────────────────────────────────────────────────────┤
│                      Redux Store                             │
│  (State: canvasSlice, sessionSlice, aiContextSlice)         │
└─────────────────────────────────────────────────────────────┘
```

---

## Connected vs Presentational Components

### Connected Components

Located in: `src/canvas/`, `src/layout/`

Responsibilities:
- Connect to Redux store
- Fetch data from React Router loaders
- Handle side effects (API calls, telemetry)
- Pass data down to presentational components

Example:
```typescript
// ConnectedCanvasPanel.tsx
export function ConnectedCanvasPanel({ className }: Props) {
  const dispatch = useAppDispatch();
  const loaderData = useRouteLoaderData("chat-session");

  // Handles save, suggestions, telemetry
  const handleSave = useCallback(async (id, content) => {
    await fetch(`/api/v1/artifacts/${id}`, { ... });
    revalidator.revalidate();
  }, []);

  return (
    <CanvasWorkspace
      artifacts={loaderData.artifacts}
      onSave={handleSave}
    />
  );
}
```

### Presentational Components

Located in: `src/canvas/`, `src/components/`

Responsibilities:
- Render UI based on props
- Emit events via callbacks
- No direct Redux or API access
- Highly testable

Example:
```typescript
// CanvasWorkspace.tsx
export function CanvasWorkspace({
  artifacts,
  onSave,
  onArtifactSelect,
}: Props) {
  // Only UI logic, no side effects
  return (
    <PanelGroup>
      {artifacts.map(artifact => (
        <ArtifactTab key={artifact.id} onClick={() => onArtifactSelect(artifact)} />
      ))}
    </PanelGroup>
  );
}
```

---

## Canvas Architecture

```
ConnectedCanvasPanel (Redux + Router integration)
└── CanvasWorkspace (Layout + Panel management)
    ├── ArtifactTabBar (Artifact switching)
    ├── CanvasTabs (Code/Preview/Data tabs)
    ├── CanvasArtifact (Content rendering)
    ├── ArtifactActions (Export/Share buttons)
    └── AIEditOverlay (AI inline editing - Phase 4)
```

---

## State Management

### Redux Slices

| Slice | Purpose |
|-------|---------|
| `canvasSlice` | Selected artifact, panel sizes |
| `sessionSlice` | Current session, messages |
| `aiContextSlice` | AI suggestions, context |
| `workspaceSlice` | Layout preferences |

### React Router Loaders

Data fetching happens in loaders, not components:

```typescript
// router/loaders/canvasLoaders.ts
export const chatLoader = async ({ params }) => {
  const [session, messages, artifacts] = await Promise.all([
    api.getSession(params.sessionId),
    api.getMessages(params.sessionId),
    api.getArtifacts(params.sessionId),
  ]);
  return { session, messages, artifacts };
};
```

---

## Related Documentation

- [Testing Patterns](./TESTING_PATTERNS.md)
- [Router Integration](./ROUTER.md)
