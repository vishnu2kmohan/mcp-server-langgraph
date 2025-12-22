# Feature Flags Mapping - Hybrid Canvas

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

## Proposed Canvas Feature Flags

Per the plan, these flags control the Hybrid Canvas rollout:

### Phase 1-2 Flags

| Flag Name | Purpose | Default | Gate |
|-----------|---------|---------|------|
| `canvas_hybrid_shell` | Enable HybridShellLayout at /studio/v2 | `false` | Route access |
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

---

## Implementation in FeatureFlags Interface

Add to `src/types/api.ts`:

```typescript
export interface FeatureFlags {
  // ... existing flags ...

  // Canvas Hybrid Shell (Phase 0+)
  /** Enable Hybrid Canvas shell at /studio/v2 */
  canvas_hybrid_shell?: boolean;
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

### Route-Level Gating (App.tsx or router)

```typescript
const { isEnabled } = useFeatureFlags();

// In router
{
  path: "studio/v2",
  element: isEnabled('canvas_hybrid_shell') ? (
    <AuthGuard>
      <HybridShellLayout />
    </AuthGuard>
  ) : (
    <Navigate to="/studio" replace />
  ),
}
```

### Component-Level Gating

```typescript
// In HybridShellLayout
const enableEditable = useFeatureFlag('canvas_editable');

return (
  <CanvasPanel editable={enableEditable}>
    {/* ... */}
  </CanvasPanel>
);
```

---

## Rollback Strategy

Per the plan, feature flags enable instant rollback:

```typescript
// If issues detected:
// 1. Set canvas_hybrid_shell = false in backend
// 2. Users immediately fall back to /studio (legacy AppShell)
// 3. No code deployment required

// Route-level kill switch
const ROUTE_FLAGS = {
  '/studio/v2/chat': 'canvas_chat_enabled',
  '/studio/v2/workflows': 'canvas_workflows_enabled',
  '/studio/v2/compliance': 'canvas_compliance_enabled',
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
    // Canvas flags (enable for development)
    canvas_hybrid_shell: true,
    canvas_editable: false,
    canvas_agents: false,
  });
}),
```

---

## Next Steps

1. **Phase 0:** Document complete (this file)
2. **Phase 1:** Add `canvas_hybrid_shell` to FeatureFlags interface
3. **Phase 1:** Add MSW mock for development
4. **Phase 1:** Add route-level gating in router/index.tsx
5. **Coordinate:** Sync flag names with backend team
