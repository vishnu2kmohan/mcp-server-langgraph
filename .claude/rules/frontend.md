---
description: Frontend development rules for Agent Studio React application
paths:
  - "src/mcp_server_langgraph/studio/frontend/**"
globs:
  - "**/*.tsx"
  - "**/*.ts"
  - "**/*.css"
---

# Frontend Development Rules

## Technology Stack

| Category | Technology |
|----------|-----------|
| Framework | React 18 |
| State | Redux Toolkit + RTK Query |
| Styling | Tailwind CSS 4 + Radix UI |
| Animation | Motion.dev (physics) + tailwindcss-animate (CSS) |
| Testing | Vitest + React Testing Library + Playwright |
| Build | Vite 7 |

## Component Patterns

### Use CVA for Variants
```typescript
import { cva } from "class-variance-authority";

export const buttonVariants = cva("base-styles", {
  variants: {
    variant: { primary: "...", secondary: "..." },
    size: { sm: "...", md: "...", lg: "..." },
  },
  defaultVariants: { variant: "primary", size: "md" },
});
```

### Use Radix Color Scale (NOT Tailwind 50-950)
```tsx
// Correct
className="bg-neutral-2 text-neutral-11 border-neutral-6"

// Wrong
className="bg-gray-100 text-gray-900 border-gray-300"
```

### Radix Scale Step Conventions

When using semantic color tokens, use **step 3** for subtle backgrounds
(success, error, primary status), not step 2:

| Usage | Correct | Wrong |
|-------|---------|-------|
| Status background | `bg-success-3` | `bg-success-2` |
| Error background | `bg-error-3` | `bg-error-2` |
| Selected state | `bg-primary-3` | `bg-primary-2` |
| Border (status) | `border-success-9` | `border-success-7` |
| Text (on status bg) | `text-success-11` | `text-success-9` |

Step 2 is for very subtle hover states. Step 3 is the standard subtle background.

### WebSocket Type Guards
```typescript
function isAlertMessage(data: unknown): data is AlertMessage {
  // Validate structure before use
}
```

## Testing Rules

- Use `data-testid` for E2E selectors (pattern: `{scope}-{element}[-{modifier}]`)
- Mock WebSocket with `vi.mock()`
- Test accessibility with `jest-axe`
- Prefer `userEvent` for form/keyboard tests; use `fireEvent` for components
  with timers (`useDebouncedValue`) or `motion.button` elements (see tests.md Rule 6)

### Required Test File Structure (MANDATORY)

Every `.tsx` test file MUST include cleanup teardown. Every `.ts`/`.tsx` test
file MUST NOT have unused imports or variables (prefix with `_` if needed for
setup side-effects).

```typescript
// REQUIRED in every .tsx test file
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.restoreAllMocks();
});
```

**Before generating test code**, verify:
- No unused imports (remove or prefix with `_`)
- No unused variables (remove or prefix with `_`)
- `afterEach` block with `cleanup()` + `vi.clearAllMocks()` + `vi.restoreAllMocks()`
- Run through Prettier formatting mentally (consistent quotes, trailing commas)

### OOM/Hang Prevention (CRITICAL)

| Trap | Symptom | Fix |
|------|---------|-----|
| `vi.importActual("../../api")` | OOM >8GB in fork worker | Mock barrel directly: `vi.mock("../../api", () => ({...}))` |
| `vi.importActual("../../hooks")` | OOM >8GB (transitively loads api) | Mock only the hooks your component imports |
| RTK Query mock returns new refs | Infinite render → OOM | Hoist mock trigger in `vi.mock` factory body (see below) |
| `userEvent` + timer hooks + `RouterProvider` | Test hangs indefinitely | Use `fireEvent` + mock `useDebouncedValue` |
| `motion.button` without mock | `userEvent.click()` hangs (rAF) | Add `vi.mock("motion/react", ...)` with `filterMotionProps` |
| Test file >1,000 lines | OOM in sharded runs | Split into `.core.test.tsx`, `.features.test.tsx` |

**Never `vi.importActual` on heavy barrels** (`src/api/index.ts` = 5,132 lines,
`src/hooks/index.ts` = 107 re-exports). Read the component source to find which
named imports it uses, then mock only those.

**RTK Query mock stability**: When mocking RTK Query mutation/query hooks,
hoist the trigger function OUTSIDE the return object to prevent infinite
render loops. Each `useXxxMutation()` call must return the SAME function
reference (RTK Query does this via internal refs):
```typescript
vi.mock("../api", () => {
  const mockTrigger = vi.fn(() => ({
    unwrap: () => Promise.resolve({ /* mock data */ }),
  }));
  const mockReturn = [mockTrigger, { isLoading: false }] as const;
  return { useMyMutation: vi.fn(() => mockReturn) };
});
```

## Animation Choice

| Use Case | Library |
|----------|---------|
| Enter/exit, simple transitions | tailwindcss-animate |
| Physics, gestures, complex sequences | motion.dev |
| Radix UI components | tailwindcss-animate |

## Commands

```bash
npm test              # Run Vitest
npm run test:e2e      # Run Playwright
npm run typecheck     # TypeScript check
npm run lint          # ESLint
```

---

## Pre-Commit Validation (CRITICAL)

Before committing frontend changes, ALL must pass:

```bash
npm run lint && npm run typecheck && bash scripts/run-tests-sharded.sh --fast --parallel
```

| Common Blocker | Fix |
|----------------|-----|
| Unused imports | Remove or use the import |
| Missing types | Add explicit type annotations |
| Unhandled async | Add `await` or `.catch()` |
| Console statements | Remove `console.log` calls |
| Unused variables | Remove or prefix with `_` |

---

## Accessibility Requirements (WCAG AA)

### Focus Visible

```typescript
// CORRECT - Visible focus ring
"focus-visible:ring-2 focus-visible:ring-primary-9 focus-visible:ring-offset-2"

// WRONG - Removing outline without replacement
"outline-none"  // FORBIDDEN without focus-visible ring
```

### Touch Targets (24px minimum)

```typescript
// CORRECT - 24px minimum (AA required)
"min-h-6 min-w-6"        // 24x24 CSS px

// PREFERRED - 44px for mobile (AAA)
"min-h-11 min-w-11"      // 44x44 CSS px
```

---

## Design System Patterns (CRITICAL - Shift-Left from STYLE.md)

**Full Guide**: `docs-internal/frontend/STYLE.md`

### Button Semantic Variants (MANDATORY)

| Button Text | Required Variant | Reason |
|-------------|------------------|--------|
| Cancel, Close, Back, Dismiss | `secondary` | De-emphasized dismissal |
| Delete, Remove, Clear, Destroy | `danger` | Destructive actions |
| Confirm, Save, Submit, OK | `primary` | Affirmative actions |
| Toolbar/icon-only | `ghost` | Minimal weight |

```tsx
// CORRECT
<Button variant="secondary">Cancel</Button>
<Button variant="danger">Delete</Button>
<Button variant="primary">Save</Button>

// WRONG - Using primary for Cancel/Delete
<Button>Cancel</Button>
<Button>Delete</Button>
```

### Z-Index Tokens (MANDATORY)

Use semantic tokens, NOT raw values:

| Correct | Wrong | Purpose |
|---------|-------|---------|
| `z-dropdown` | `z-50` | Dropdown menus |
| `z-modal` | `z-60` | Modal dialogs |
| `z-toast` | `z-75` | Toast notifications |

### Import Patterns

```typescript
// Pages (src/pages/*.tsx) - Direct imports
import { Button } from "../components/UI/Button";

// Components (src/components/**/*.tsx) - Barrel imports
import { Button, Badge } from "@/components/UI";
```

---

## E2E Testing (Playwright)

### localStorage Key Convention

`storage.get(key)` auto-prefixes keys with `studio-` unless the key already starts with `studio-`. When setting localStorage directly in E2E fixtures, use the full key:

```typescript
// CORRECT - key already includes prefix
localStorage.setItem('studio-onboarding', 'true');
localStorage.setItem('studio-auth', JSON.stringify({ state: { tokens: {...} } }));

// WRONG - will be read as studio-studio-onboarding
localStorage.setItem('onboarding', 'true');
```

### Onboarding Dismissal

`StudioShellLayout` checks `storage.get<boolean>("studio-onboarding") !== true`.
The value must be `'true'` (JSON boolean string), NOT an object:

```typescript
// CORRECT
localStorage.setItem('studio-onboarding', 'true');

// WRONG - StudioShellLayout expects JSON boolean, not object
localStorage.setItem('studio-onboarding', JSON.stringify({ completed: true }));
```

After PKCE auth (cross-origin redirect), `addInitScript` may not persist. Set localStorage explicitly after auth succeeds and reload if needed.

### Feature Flag Mocking

Feature flags are loaded from `/api/v1/features`. E2E tests needing specific flags must mock the endpoint:

```typescript
await page.route("**/api/v1/features**", async (route) => {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ preferences_menu: true, kb_focus: true }),
  });
});
```

### Prop Threading Pattern

New props flowing through the chat component hierarchy must be added at every layer:

```
ConnectedConversationPanel (state + handlers)
  → ConversationPanel (interface + destructuring + pass-through)
    → ConnectedChatInputForm (interface + destructuring + pass-through)
      → ChatInput (interface + destructuring + render)
        → PreferencesMenu / other leaf components
```
