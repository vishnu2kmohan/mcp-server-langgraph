# RBAC Gaps Analysis - LeftSidebar and Navigation

**Date:** 2025-12-19
**Phase:** 0 - Baseline Analysis
**Status:** Documentation only (no changes to legacy code)

---

## Executive Summary

The current LeftSidebar component claims to implement "RBAC filtering based on persona" (line 9 of component), but **no actual persona-based filtering is implemented**. All navigation items are visible to all users regardless of role.

---

## Current State

### LeftSidebar.tsx Analysis

**Location:** `src/components/Layout/LeftSidebar.tsx`

| Issue | Description | Impact |
|-------|-------------|--------|
| **No persona import** | Component does not import `selectPersona` | Cannot filter by role |
| **All groups visible** | GROUPS array rendered without filtering | Bob sees Admin links |
| **All items visible** | NAV_ITEMS rendered without filtering | Users can see dev-only items |
| **Misleading docstring** | Claims RBAC filtering exists | False documentation |

### Navigation Groups & Required Personas

| Group | Items | Should Be Visible To | Currently Visible To |
|-------|-------|---------------------|---------------------|
| **workspace** | Projects | all | all |
| **conversations** | Chat | all | all |
| **build** | Workflows | all (read), admin/dev (edit) | all |
| **connections** | MCP, Agents, Vectors | admin, developer | all |
| **insights** | Observability, Cost, Settings | all (Cost/Settings), admin/dev (Obs) | all |
| **admin** | Dashboard | admin | all |

### Route-Level Guards vs. UI Visibility

The router (`router/index.tsx`) correctly uses `PersonaGuard` to block unauthorized access:

```typescript
// Lines 128-145: MCP route is guarded
{
  path: "mcp",
  element: (
    <PersonaGuard allowedPersonas={["admin", "developer"]}>
      <Outlet />
    </PersonaGuard>
  ),
  ...
}

// Lines 220-246: Admin routes are guarded
{
  path: "admin",
  element: (
    <PersonaGuard allowedPersonas={["admin"]}>
      <Outlet />
    </PersonaGuard>
  ),
  ...
}
```

**However:** Users can still **see** and **click** nav items that lead to access-denied pages. This is poor UX - users should not see links to pages they cannot access.

---

## Identified RBAC Gaps

### Gap 1: LeftSidebar shows all navigation items

**File:** `src/components/Layout/LeftSidebar.tsx`
**Lines:** 110-200 (GROUPS and NAV_ITEMS definitions)

**Current behavior:**
```typescript
// Line 332-637: All groups rendered without persona check
{GROUPS.map((group) => {
  const items = itemsByGroup[group.id] || [];
  // No persona filtering here!
  ...
})}
```

**Expected behavior:**
```typescript
// Filter groups based on persona
const visibleGroups = GROUPS.filter(group => {
  if (group.id === 'admin') return persona === 'admin';
  if (group.id === 'connections') return ['admin', 'developer'].includes(persona);
  return true; // All other groups visible to all
});
```

### Gap 2: No NavItem-level permission checking

**Current:** All items in a group are rendered
**Expected:** Each item should have a `requiredPersonas` array

```typescript
interface NavItem {
  id: string;
  path: string;
  label: string;
  icon: ReactNode;
  group: NavGroup;
  requiredPersonas?: ('admin' | 'developer' | 'user')[]; // MISSING
}
```

### Gap 3: CommandPalette has filtering, LeftSidebar doesn't

**CommandPalette.tsx** (line 95) uses persona to filter commands:
```typescript
const personaFromSlice = useAppSelector(selectPersona);
```

But LeftSidebar does NOT import or use this selector.

---

## Components Using Persona Correctly

These components properly filter based on persona:

| Component | File | Usage |
|-----------|------|-------|
| PersonaGuard | `router/guards/PersonaGuard.tsx` | Route protection |
| PersonaRouter | `router/PersonaRouter.tsx` | Default route selection |
| CommandPalette | `components/Layout/CommandPalette.tsx` | Command filtering |
| StatusBar | `components/Layout/StatusBar.tsx` | Persona display |
| SettingsDocument | `components/Settings/SettingsDocument.tsx` | Persona selector (admin only) |

---

## Recommended Fixes (Phase 3)

### Fix 1: Add persona-based filtering to LeftSidebar

```typescript
// Import
import { selectPersona } from "../../store/slices/personaSlice";

// In component
const persona = useAppSelector(selectPersona);

// Define visibility rules
const GROUP_VISIBILITY: Record<NavGroup, ('admin' | 'developer' | 'user')[]> = {
  workspace: ['admin', 'developer', 'user'],
  conversations: ['admin', 'developer', 'user'],
  build: ['admin', 'developer', 'user'],
  connections: ['admin', 'developer'],
  insights: ['admin', 'developer', 'user'], // Filter items within
  admin: ['admin'],
};

// Filter groups
const visibleGroups = GROUPS.filter(group =>
  GROUP_VISIBILITY[group.id].includes(persona)
);
```

### Fix 2: Add requiredPersonas to NavItem

```typescript
const NAV_ITEMS: NavItem[] = [
  // WORKSPACE - all
  { id: "projects", ..., requiredPersonas: ['admin', 'developer', 'user'] },

  // CONNECTIONS - admin/developer only
  { id: "mcp", ..., requiredPersonas: ['admin', 'developer'] },
  { id: "agents", ..., requiredPersonas: ['admin', 'developer'] },
  { id: "vectors", ..., requiredPersonas: ['admin', 'developer'] },

  // INSIGHTS - mixed
  { id: "observability", ..., requiredPersonas: ['admin', 'developer'] },
  { id: "cost", ..., requiredPersonas: ['admin', 'developer', 'user'] },
  { id: "settings", ..., requiredPersonas: ['admin', 'developer', 'user'] },

  // ADMIN - admin only
  { id: "admin", ..., requiredPersonas: ['admin'] },
];
```

### Fix 3: Deny-by-default pattern

```typescript
// In StudioShell ActivityBar (Phase 3)
const useVisibleNavItems = () => {
  const persona = useAppSelector(selectPersona);

  return NAV_ITEMS.filter(item => {
    // DENY by default - must explicitly be allowed
    if (!item.requiredPersonas) return false;
    return item.requiredPersonas.includes(persona);
  });
};
```

---

## Impact on Studio Canvas Rebuild

### Phase 3 (Weeks 6-8): Migration

The new StudioShell `ActivityBar` component will implement proper RBAC from the start:

1. **Deny-by-default** - Items only shown if explicitly allowed
2. **Persona-aware groups** - Only show groups user can access
3. **OpenFGA integration ready** - Structure supports fine-grained permissions

### Phase 7 (Week 18+): Legacy Cleanup

When removing AppShell:
1. Document that legacy LeftSidebar had RBAC gaps
2. Verify StudioShell ActivityBar has proper filtering
3. Run E2E tests for each persona to verify correct visibility

---

## Testing Gaps

### Missing Tests

1. **LeftSidebar.test.tsx** - No tests for persona-based filtering
2. **Integration tests** - No tests verifying Bob can't see Admin links
3. **E2E tests** - No journey tests for persona-specific navigation

### Recommended Test Cases (Phase 3)

```typescript
describe('ActivityBar RBAC', () => {
  it('hides admin group for user persona', () => {
    // Bob should not see Admin links
  });

  it('hides connections group for user persona', () => {
    // Bob should not see MCP, Agents, Vectors
  });

  it('shows all groups for admin persona', () => {
    // Admin sees everything
  });

  it('shows connections but not admin for developer persona', () => {
    // Developer sees MCP but not Admin dashboard
  });
});
```

---

## Conclusion

The current LeftSidebar has a significant RBAC gap - all navigation items are visible to all users regardless of role. While routes are protected by PersonaGuard, the UI incorrectly shows links that lead to access-denied pages.

**Recommendation:** Fix this in the new StudioShell ActivityBar (Phase 3) rather than modifying legacy LeftSidebar. This aligns with the Strangler Fig pattern.
