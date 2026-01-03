# DEPRECATED

> **This frontend has been deprecated in favor of StudioShell.**

**Archived**: 2026-01-02
**Migration Status**: In Progress

---

## Overview

The Playground frontend is deprecated. All functionality is being consolidated into:

- `@mcp-server-langgraph/studio-frontend` (StudioShell - primary app)
- `@mcp-server-langgraph/shared-frontend` (Design System - UI primitives)

**Do NOT add new features to this package.**

---

## Component Migration Status

### Chat Components

| Playground | Studio Equivalent | Status |
|------------|-------------------|--------|
| `ChatInput.tsx` | `ChatInputForm.tsx` | Covered |
| `ChatInterface.tsx` | `ChatDocument.tsx` | Covered |
| `ChatMessage.tsx` | `ChatMessage.tsx` | Covered |
| `ChatStream.tsx` | `useStreamingChat.ts` | Covered |

### Layout Components

| Playground | Studio Equivalent | Status |
|------------|-------------------|--------|
| `Header.tsx` | StudioShell layout | Covered |
| `Sidebar.tsx` | StudioShell layout | Covered |

### MCP Components

| Playground | Studio Equivalent | Status |
|------------|-------------------|--------|
| `ElicitationDialog.tsx` | `ElicitationDialog.tsx` | Covered |
| `SamplingDialog.tsx` | - | **Needs Migration** |
| `SchemaForm.tsx` | - | **Needs Migration** |
| `ServerManager.tsx` | `MCPServerCard.tsx` | Covered |

### Observability Components

| Playground | Studio Equivalent | Status |
|------------|-------------------|--------|
| `AlertPanel.tsx` | `AlertsPanel.tsx` | Covered |
| `LogPanel.tsx` | `LogsTab.tsx` | Covered |
| `MetricsPanel.tsx` | `MetricsTab.tsx` | Covered |
| `ObservabilityTabs.tsx` | `ObservabilityDocument.tsx` | Covered |
| `TracePanel.tsx` | `TracesTab.tsx` | Covered |
| `TraceWaterfall.tsx` | - | **Needs Evaluation** |

### Session Components

| Playground | Studio Equivalent | Status |
|------------|-------------------|--------|
| `CreateSessionModal.tsx` | Session creation in Studio | Covered |
| `SessionCard.tsx` | `SessionList.tsx` | Covered |
| `SessionList.tsx` | `SessionList.tsx` | Covered |

### Feedback Components

| Playground | Studio Equivalent | Status |
|------------|-------------------|--------|
| `NPSSurvey.tsx` | `SUSSurvey.tsx` | Different surveys - evaluate need |

---

## Hook Migration Status

### MCP Hooks

| Playground | Studio Equivalent | Status |
|------------|-------------------|--------|
| `useMCPConnection.ts` | `useMCPConnection.ts` | Covered |
| `useMCPElicitation.ts` | - | **Needs Migration** |
| `useMCPPrompts.ts` | - | **Needs Migration** |
| `useMCPResources.ts` | - | **Needs Migration** |
| `useMCPSampling.ts` | - | **Needs Migration** |
| `useMCPTools.ts` | - | **Needs Migration** |

### Other Hooks

| Playground | Studio Equivalent | Status |
|------------|-------------------|--------|
| `useAccessibility.ts` | `useAccessibility.ts` | Covered |
| `useDarkMode.ts` | `useTheme.ts` | Covered |
| `useSession.ts` | `useSessionSync.ts` | Covered |
| `useHeartMetrics.tsx` | `useHeartMetricsTracker.ts` | Covered |

---

## Migration Priority

### High Priority (Unique features needed in Studio)

1. **MCP Sampling** - `SamplingDialog.tsx` + `useMCPSampling.ts`
2. **MCP Schema Forms** - `SchemaForm.tsx`
3. **MCP Hooks** - `useMCPPrompts`, `useMCPResources`, `useMCPTools`

### Low Priority (Can defer or delete)

1. **TraceWaterfall** - Evaluate if Studio's TracesTab covers this
2. **NPSSurvey** - Studio has SUS survey; evaluate if NPS is still needed

---

## How to Migrate Features

1. Copy component/hook to Studio's equivalent directory
2. Update imports to use `@mcp-server-langgraph/shared-frontend` primitives
3. Ensure TypeScript types are aligned
4. Add tests in Studio
5. Delete from Playground after verification

---

## Build/CI Updates Required

After final deprecation:

- [ ] Remove Playground from root `package.json` workspaces
- [ ] Remove Playground build jobs from `.github/workflows/`
- [ ] Remove Playground Make targets from `Makefile`
- [ ] Update documentation links in `docs/`
- [ ] Archive or delete this directory

---

## Questions?

Contact the frontend team before making any changes to deprecated code.
