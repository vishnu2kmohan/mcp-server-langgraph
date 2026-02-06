---
purpose: Fixing Rollup circular dependency warnings with barrel exports
priority: medium
category: frontend
last-updated: 2026-02-05
---

# Rollup Circular Dependency Pattern

## Problem

When page components import from the `@/components/UI` barrel export (`index.ts`), Rollup can produce circular dependency warnings during build. This happens because:

1. Pages are code-split into separate chunks
2. The UI barrel re-exports many components
3. Some UI components may have transitive dependencies back to shared utilities

## Solution

**Use direct imports in page components** instead of barrel imports:

```typescript
// CORRECT: Direct imports in pages (avoid Rollup warnings)
// Direct imports to avoid Rollup circular dependency warnings
import { Button } from "../components/UI/Button";
import { Dialog } from "../components/UI/Dialog";
import { Skeleton } from "../components/UI/Skeleton";

// INCORRECT: Barrel imports in pages (may cause Rollup warnings)
import { Button, Dialog, Skeleton } from "../components/UI";
```

## Affected Files

Pages that use direct imports:
- `src/pages/AuditLogPage.tsx`
- `src/pages/ProjectsPage.tsx`
- `src/pages/WorkflowsListPage.tsx`
- `src/pages/WorkflowsPage.tsx`

## ESLint Configuration

The `no-restricted-imports` rule has exceptions for the `pages/` directory to allow direct UI component imports without triggering lint errors.

## When to Use

- **Pages**: Use direct imports with explanatory comment
- **Components**: Use barrel imports (`@/components/UI`) for cleaner imports
- **Hooks/Utils**: Use barrel imports

## Comment Format

Always include the explanatory comment before direct imports:

```typescript
// Direct imports to avoid Rollup circular dependency warnings
import { Button } from "../components/UI/Button";
```

This prevents future "fixes" that would reintroduce the circular dependency warnings.
