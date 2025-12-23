# Feature Flags Mapping - Studio Canvas

**Date:** 2025-12-19
**Phase:** 0 - Baseline Analysis

---

## Existing Feature Flags

### Currently Defined in TypeScript (api.ts:149-161)

| Flag Name (Backend) | TypeScript Property | Used In |
|---------------------|---------------------|---------|
| `enable_workflows_feature` | `enable_workflows_feature` | - |
| `enable_sessions_feature` | `enable_sessions_feature` | - |
| `enable_cost_dashboard` | `enable_cost_dashboard` | - |
| `enable_cost_dashboard_users` | `enable_cost_dashboard_users` | - |
| `enable_observability_ui` | `enable_observability_ui` | - |
| `enable_code_export` | `enable_code_export` | - |
| `enable_ai_suggestions` | `enable_ai_suggestions` | - |
| `enable_mcp_websocket` | `enable_mcp_websocket` | - |
| `enable_interactive_artifacts` | `enable_interactive_artifacts` | - |

### Currently Used in Frontend (isEnabled calls)

| Flag Name (Frontend) | Used In | Purpose |
|---------------------|---------|---------|
| `url_content_fetch` | App.tsx | Enable URL content fetching in chat |
| `slash_commands` | App.tsx | Enable slash commands in chat input |
| `style_presets` | App.tsx | Enable style presets in chat |
| `onboarding_wizard` | App.tsx | Show onboarding for new users |
| `guided_tour` | App.tsx | Show guided tour after onboarding |
| `sus_survey` | App.tsx | Show SUS (usability) survey |
| `interactive_artifacts` | ChatPage.tsx, ChatDocument.tsx | Enable Sandpack for code artifacts |
| `ai_suggestions` | ChatDocument.tsx | Enable AI follow-up suggestions |
| `session_export` | ChatHeader.tsx | Enable session export button |

---

## Naming Convention Mismatch

**Issue:** Backend uses `enable_` prefix (snake_case), frontend uses plain names (snake_case).

| Backend (api.ts) | Frontend (isEnabled) |
|------------------|---------------------|
| `enable_ai_suggestions` | `ai_suggestions` |
| `enable_interactive_artifacts` | `interactive_artifacts` |

**Recommendation:** Standardize on frontend names (no `enable_` prefix) and map in API layer if needed.

---

## Canvas Feature Flags

These flags control the Studio Canvas feature rollout:

### Phase 1-2 Flags

| Flag Name | Purpose | Default | Gate |
|-----------|---------|---------|------|
| ~~`canvas_hybrid_shell`~~ | ~~Enable StudioShellLayout at /studio~~ | N/A | **REMOVED** - StudioShell is now the default at `/studio` |
| `canvas_editable` | Enable artifact editing in Canvas | `false` | Edit buttons |

### Phase 3-4 Flags

| Flag Name | Purpose | Default | Gate |
|-----------|---------|---------|------|
| `canvas_agents` | Enable background agent panel | `false` | Agent UI |
| `canvas_ai_palette` | Enable AI command palette fallback | `false` | Cmd+K NL |

### Phase 5 Flags

| Flag Name | Purpose | Default | Gate |
|-----------|---------|---------|------|
| `canvas_compliance` | Enable compliance dashboards | `false` | Compliance nav |
| `canvas_help` | Enable in-app help pane | `false` | Help button |

### Phase 6+ Flags (AI UX Features)

| Flag Name | Purpose | Default | Gate |
|-----------|---------|---------|------|
| `batch_composite_analysis` | Enable CrossInsightsPanel with batch AI analysis | `false` | CrossInsightsPanel visibility |
| `insights_session_dismissal` | Session-only dismissal (no localStorage persistence) | `false` | CrossInsightsPanel state management |

**`insights_session_dismissal` Details:**
- When `false` (default): Dismissed state persists to localStorage, survives page refresh
- When `true`: Dismissed state is session-only, resets on page refresh
- Use case: Allows operators to force users to see insights on each session
- Keyboard shortcut: Cmd+I (Mac) / Ctrl+I (Windows/Linux) toggles visibility

### Granular Intelligence Feature Flags (Sprint 1-4)

These flags control specific AI Intelligence capabilities in the StudioShell UI:

| Flag Name (Backend) | Frontend Property | Purpose | Default | Task Categories |
|---------------------|-------------------|---------|---------|-----------------|
| `enable_studio_ai` | Global enabled | Master toggle for all Studio AI | `false` | All 8 categories |
| `enable_session_intelligence` | `sessionIntelligence` | Session summarize/group/similarity | `false` | session |
| `enable_conversation_intelligence` | `conversationIntelligence` | Intent detection/context optimization/goal tracking | `false` | conversation |
| `enable_canvas_intelligence` | `canvasIntelligence` | Code analysis/artifact suggestions/diff explanation | `false` | canvas |
| `enable_trace_intelligence` | `traceIntelligence` | Trace summarization/cost projection/anomaly detection | `false` | trace |
| `enable_diagram_intelligence` | `diagramIntelligence` | Diagram analysis/diagram-to-code generation | `false` | diagram |
| `enable_hitl_ai` | `hitlIntelligence` | HITL risk assessment (beyond basic HITL approvals) | `false` | hitl |
| `enable_genui` | `genuiComponents` | Generative UI - dynamic component rendering | `false` | command |

**Granular Flag Behavior:**
- Each granular flag can be enabled independently
- Falls back to `enable_studio_ai` master flag when granular flag is not set
- Mapped in `useAIIntelligenceConfig.ts` hook
- Exposed via `get_ui_features_for_role()` backend method

**Frontend Mapping (useAIIntelligenceConfig.ts):**
```typescript
// Helper to check granular flag with fallback to master flag
const isIntelligenceEnabled = (granularFlag: string): boolean =>
  isEnabled(granularFlag) || isEnabled("enable_studio_ai");

features: {
  sessionIntelligence: isIntelligenceEnabled("enable_session_intelligence"),
  conversationIntelligence: isIntelligenceEnabled("enable_conversation_intelligence"),
  canvasIntelligence: isIntelligenceEnabled("enable_canvas_intelligence"),
  traceIntelligence: isIntelligenceEnabled("enable_trace_intelligence"),
  diagramIntelligence: isIntelligenceEnabled("enable_diagram_intelligence"),
  hitlIntelligence: isEnabled("enable_hitl_ai"),
  genuiComponents: isEnabled("enable_genui"),
}
```

---

## Implementation in FeatureFlags Interface

Add to `src/types/api.ts`:

```typescript
export interface FeatureFlags {
  // ... existing flags ...

  // Canvas Features (StudioShell is now default at /studio)
  /** Enable editable artifacts in Canvas panel */
  canvas_editable?: boolean;
  /** Enable background agent panel */
  canvas_agents?: boolean;
  /** Enable AI fallback in command palette */
  canvas_ai_palette?: boolean;
  /** Enable compliance dashboards */
  canvas_compliance?: boolean;
  /** Enable in-app help pane */
  canvas_help?: boolean;

  // Allow any string key for flexibility
  [key: string]: boolean | undefined;
}
```

---

## Usage Pattern

### Route-Level Structure (router/index.tsx)

StudioShellLayout is now the default at `/studio`:

```typescript
// In router - StudioShell is the default shell
{
  path: "studio",
  element: (
    <AuthGuard>
      <StudioShellLayout />
    </AuthGuard>
  ),
  children: [
    { index: true, element: <Navigate to="chat" replace /> },
    // ... all studio routes
  ],
}
```

### Component-Level Gating

```typescript
// In StudioShellLayout
const enableEditable = useFeatureFlag('canvas_editable');

return (
  <CanvasPanel editable={enableEditable}>
    {/* ... */}
  </CanvasPanel>
);
```

---

## Rollback Strategy

StudioShellLayout is now the default at `/studio`. Feature flags control individual canvas features:

```typescript
// Feature-level rollback (no shell-level rollback needed):
// 1. Set canvas_editable = false to disable artifact editing
// 2. Set canvas_agents = false to disable agent panel
// 3. Set canvas_compliance = false to disable compliance dashboards
// 4. No code deployment required for feature rollbacks

// Route-level feature gates
const ROUTE_FLAGS = {
  '/studio/compliance': 'canvas_compliance',
  '/studio/help': 'canvas_help',
};
```

---

## Backend Coordination Needed

**Action Item:** Confirm with backend team that these flag names will be added to:

1. Feature flag service/config
2. `/api/v1/features` endpoint response
3. Any environment-specific overrides

**Naming Convention:**
- All Canvas flags use `canvas_` prefix
- No `enable_` prefix (frontend convention)
- snake_case throughout

---

## MSW Mocking (Development)

For development before backend implements:

```typescript
// src/mocks/handlers.ts
http.get('/api/v1/features', () => {
  return HttpResponse.json({
    // Existing flags
    url_content_fetch: true,
    slash_commands: true,
    // Canvas feature flags (StudioShell is now default)
    canvas_editable: true,
    canvas_agents: true,
    canvas_ai_palette: true,
    canvas_compliance: true,
    canvas_help: true,
  });
}),
```

---

## Status

**COMPLETED:** StudioShellLayout is now the default UI at `/studio`.

- ~~Phase 1: Add `canvas_hybrid_shell` flag~~ - **REMOVED** (StudioShell is default)
- ✅ Phase 2: `canvas_editable` controls artifact editing
- ✅ Phase 3-4: `canvas_agents`, `canvas_ai_palette` control agent features
- ✅ Phase 5: `canvas_compliance`, `canvas_help` control advanced features
- ✅ Phase 6+: `batch_composite_analysis`, `insights_session_dismissal` control AI UX features

**Granular Intelligence Flags (Sprint 1-4):**
- ✅ Sprint 1: Frontend feature flag integration (`useAIIntelligenceConfig.ts`)
- ✅ Sprint 1: AIIntelligenceContext extended with new feature types
- ✅ Sprint 1: All 7 granular flags mapped with fallback to master flag
- 🔄 Sprint 2: Session Intelligence implementation (in progress)
