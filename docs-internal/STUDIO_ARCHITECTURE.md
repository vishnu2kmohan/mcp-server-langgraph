# Agent Studio Frontend Architecture

**Status**: Active
**Last Updated**: 2025-12-27
**Owner**: Platform Team

## Purpose

This document describes the architecture of the Agent Studio frontend, which consolidates the previous Builder and Playground UIs into a unified React application.

---

## Overview

The Agent Studio is a modern 3-panel React application built with:
- **React 18** with TypeScript
- **Redux Toolkit** + **RTK Query** for state management
- **React Router v7** with lazy code-splitting
- **Vite** for development and building
- **Tailwind CSS** for styling

---

## Directory Structure

```
studio/frontend/src/
├── ai/                      # AI components (command palette, suggestions, background agents)
├── analytics/               # HEART metrics, signal registry, goal definitions
├── api/                     # RTK Query API endpoints, contract validation, transforms
├── canvas/                  # Canvas workspace and artifact rendering
├── compliance/              # Compliance dashboards (GDPR, HIPAA, SOC2, FedRAMP)
├── components/              # React components organized by feature
│   ├── Admin/              # Admin dashboard, approval dialogs, alerts
│   ├── Agents/             # Agent configuration cards, LLM providers
│   ├── Analytics/          # Insights panels, HEART components
│   ├── Artifacts/          # Artifact rendering and export
│   ├── Chat/               # Chat UI components, messages, input
│   ├── Observability/      # Traces, logs, metrics visualization
│   └── UI/                 # Design system components
├── contexts/               # React contexts (FeatureFlags, Telemetry, etc.)
├── devtools/               # DevTools panel, telemetry viewer, time-travel debugging
├── hooks/                  # 40+ custom hooks (WebSockets, AI features, etc.)
├── layout/                 # Layout components (StudioShellLayout, ActivityBar, StatusBar)
├── pages/                  # Page components (lazy-loaded)
├── persona/                # Persona routing and guards
├── router/                 # React Router configuration and guards
├── services/               # Business logic services
├── store/                  # Redux store with 20+ slices
├── types/                  # TypeScript type definitions
└── utils/                  # Utility functions
```

---

## State Management

### Redux Toolkit + RTK Query

The frontend uses a unified Redux store with RTK Query for API caching.

**Store Configuration** (`src/store/index.ts`):

| Slice | Purpose | LOC |
|-------|---------|-----|
| `sessionSlice` | Chat session management | 882 |
| `canvasSlice` | Studio Canvas layout (panel sizes, focus mode) | - |
| `workspaceSlice` | JupyterLab-inspired layout with persistence | - |
| `authSlice` | Authentication state (JWT tokens) | - |
| `personaSlice` | User roles and RBAC | - |
| `uiSlice` | UI state (modals, sidebars, theme) | - |
| `projectSlice` | Project management | - |
| `workflowSlice` | Workflow builder state | - |
| `artifactSlice` | Code, charts, and media artifacts | - |
| `mcpSlice` | MCP (Model Context Protocol) state | - |
| `backgroundAgentSlice` | AI background agents | - |
| `aiContextSlice` | AI context and suggestions | - |
| `complianceSlice` | Compliance tracking | - |
| `alertSlice` | Alert management with sound integration | - |
| `observabilitySlice` | Metrics and tracing filters | - |
| `devToolsSlice` | DevTools panel state | - |
| `langGraphSlice` | LangGraph execution events | - |

**RTK Query API** (`src/api/index.ts`):
- 30+ endpoints with automatic caching and invalidation
- Endpoints for sessions, workflows, observability, admin, AI, compliance, MCP

**Typed Hooks** (`src/store/hooks.ts`):
```typescript
export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
```

---

## Component Architecture

### Shell Layout

`StudioShellLayout.tsx` - 3-panel resizable layout using `react-resizable-panels`:

```
┌─────────────────────────────────────────────────────────────┐
│                         Activity Bar (56px)                  │
├───────────┬──────────────────────────┬──────────────────────┤
│           │                          │                      │
│  Session  │   Conversation Panel     │   Canvas Workspace   │
│   Nav     │       (~40%)             │      (~40%)          │
│  (~20%)   │                          │                      │
│           │                          │                      │
├───────────┴──────────────────────────┴──────────────────────┤
│                        Status Bar                            │
├─────────────────────────────────────────────────────────────┤
│                   DevTools Panel (collapsible)               │
└─────────────────────────────────────────────────────────────┘
```

### Router Configuration

`src/router/index.tsx` - React Router v7 with lazy code-splitting:

```typescript
Routes:
├── /studio/*             # Main application (authenticated)
│   ├── /                 # Dashboard
│   ├── /sessions         # Chat sessions
│   ├── /workflows        # Workflow builder
│   ├── /agents           # Agent configuration
│   ├── /traces           # Observability traces
│   ├── /projects         # Project management
│   ├── /cost             # Cost dashboard
│   └── /admin/*          # Admin portal
└── /                     # Root redirect
```

**Guards:**
- `AuthGuard` - Requires authentication
- `PersonaGuard` - Role-based access control
- `PermissionGuard` - Feature-level permissions
- `StudioShellGuard` - Shell initialization

---

## API Integration Pattern

### Request Flow

```
Contract Validation (TypeScript)
    ↓
RTK Query Hooks (auto-generated with caching)
    ↓
Base Query with Reauth (JWT refresh on 401)
    ↓
Cursor Pagination (efficient large datasets)
    ↓
Transform Functions (API → frontend format)
```

### Example Usage

```typescript
// UI state in Redux
const { sessionNavCollapsed } = useAppSelector(selectCanvasState);
dispatch(toggleSessionNav());

// API data from RTK Query (auto-cached)
const { data: sessions } = useGetSessionsQuery({ limit: 20 });
```

---

## React Context System

| Context | Purpose |
|---------|---------|
| `FeatureFlagContext` | Feature gating from backend |
| `AIIntelligenceContext` | AI suggestions and insights |
| `PreferencesContext` | User preferences persistence |
| `TelemetryContext` | Analytics event tracking |
| `ChatLoaderContext` | Chat page data loading |

---

## Custom Hooks Library (40+ hooks)

### WebSocket Hooks
- `useNotificationWebSocket` - Real-time notifications
- `useAlertWebSocket` - Admin alerts
- `useAgentRequestWebSocket` - HITL approvals
- `useConnectionHealthWebSocket` - Connection status

### AI Hooks
- `useAIPersonaAnalysis` - AI persona recommendations
- `useAIRealTimeSuggestions` - Real-time chat suggestions
- `useAIIntelligenceConfig` - Intelligence panel configuration
- `useAINudges` - Contextual hints

### Feature Hooks
- `useOnboarding` - First-time user experience
- `useTheme` - Dark mode management
- `usePWAUpdate` - App update notifications
- `useAccessibility` - Accessibility preferences
- `usePersonaRouting` - Persona-based navigation

---

## Bundle Optimization

### Lazy Loading Strategy

```typescript
// Router-level splitting
const AdminDashboardPage = lazy(() => import('./pages/AdminDashboard'));

// Component-level splitting
const OnboardingWizard = lazy(() =>
  import("./components/Onboarding").then((m) => ({
    default: m.OnboardingWizard,
  })),
);
```

**Lazy-loaded components:**
- Modals (OnboardingWizard, GuidedTour, SUSSurvey)
- Heavy components (AICommandPalette, DevTools)
- All page components

---

## TypeScript Type System

| File | Purpose |
|------|---------|
| `src/types/api.ts` | API contract types (RTK Query) |
| `src/types/session.ts` | Session domain types |
| `src/types/workflow.ts` | Workflow domain types |
| `src/types/hitl.ts` | HITL (Human-in-the-Loop) types |
| `src/store/types.ts` | Redux RootState and AppDispatch |

---

## Testing Architecture

| Type | Location | Tool |
|------|----------|------|
| Unit tests | Colocated `.test.tsx` | Vitest |
| Slice tests | `store/*.test.ts` | Vitest |
| E2E tests | `tests/e2e/` | Playwright (50+ specs) |
| Contract tests | `tests/contract/` | API validation |
| Accessibility | Component tests | Jest Axe |

---

## Key Design Decisions

1. **Unified Redux Store** - All state in single tree, not multiple stores
2. **RTK Query for API** - Automatic caching, deduplication, real-time updates
3. **Canvas Layout** - Modern 3-panel resizable UI (inspired by Gemini/ChatGPT)
4. **Listener Middleware** - Cross-slice communication without circular dependencies
5. **Lazy Code-Splitting** - Aggressive splitting for smaller initial bundle
6. **Feature Flags** - Backend-driven feature gating via React Context
7. **WebSocket Hooks** - Custom hooks for real-time features
8. **Persona-Based Routing** - Role-based access control at route level

---

## Related Documentation

- [Feature Flag Catalog](./FEATURE_FLAG_CATALOG.md) - UI feature flags
- [WebSocket Standardization](./WEBSOCKET_STANDARDIZATION.md) - ADR-0068
- [ADR-0047](../docs/architecture/adr-0047-visual-workflow-builder.mdx) - Visual Workflow Builder
