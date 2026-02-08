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

### WebSocket Type Guards
```typescript
function isAlertMessage(data: unknown): data is AlertMessage {
  // Validate structure before use
}
```

## Testing Rules

- Use `data-testid` for E2E selectors
- Mock WebSocket with `vi.mock()`
- Use `userEvent` over `fireEvent`
- Test accessibility with `jest-axe`

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

### Test ID Conventions

```tsx
// Pattern: {scope}-{element}[-{modifier}]
data-testid="chat-input-form"
data-testid="model-selector-button"
data-testid={`file-card-${file.id}`}  // Dynamic

// WRONG
data-testid="button-1"      // Not semantic
data-testid="fileUploadBtn" // Not kebab-case
```

### Import Patterns

```typescript
// Pages (src/pages/*.tsx) - Direct imports
import { Button } from "../components/UI/Button";

// Components (src/components/**/*.tsx) - Barrel imports
import { Button, Badge } from "@/components/UI";
```
