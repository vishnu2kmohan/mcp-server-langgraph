# Design System Exceptions Guide

This document explains when and how to bypass design system enforcement rules.

## ESLint Rules Enforced

The following rules enforce design system consistency:

| Rule | Severity | Purpose |
|------|----------|---------|
| `react/forbid-elements` | warn | Prefer `<Button>` over raw `<button>` |
| `no-restricted-imports` | error | Use barrel imports for UI components |
| `no-restricted-syntax` | error | Use semantic colors (error-*, success-*) |

## When Raw Elements Are Allowed

### 1. Canvas/ReactFlow Interactions

ReactFlow and canvas-based interactions require native DOM events and refs.
These are exempted in `eslint.config.js`.

```tsx
// canvas/NodeHandle.tsx - Exempted
<button
  onMouseDown={handleDragStart}
  ref={nodeRef}
  className="..."
/>
```

### 2. Third-Party Library Wrappers

When wrapping third-party components that require specific DOM structure:

```tsx
// eslint-disable-next-line react/forbid-elements -- Monaco Editor requires native input for keybindings
<input
  ref={hiddenInputRef}
  onKeyDown={handleMonacoKeydown}
/>
```

### 3. Performance-Critical Paths

Only when measured performance data shows significant overhead:

```tsx
// eslint-disable-next-line react/forbid-elements -- Measured 15ms render savings in virtualized list
<button onClick={onClick}>{children}</button>
```

**Requirements for performance exceptions:**
- Include benchmark data in the comment
- File an issue to revisit after optimization

### 4. UI Component Definitions

The `/components/UI/` directory is exempted - these define the primitives.

## How to Document Exceptions

Use ESLint disable comments with clear reasons:

```tsx
// Good - Clear reason
// eslint-disable-next-line react/forbid-elements -- Canvas drag handle needs native mousedown

// Bad - No reason
// eslint-disable-next-line react/forbid-elements

// Bad - Vague reason
// eslint-disable-next-line react/forbid-elements -- Needed here
```

## Exception Categories

### Automatic Exceptions (in eslint.config.js)

These directories are automatically exempted:

| Directory | Reason |
|-----------|--------|
| `components/UI/**` | Define design system primitives |
| `canvas/**` | Canvas interactions need native handlers |
| `Workflow/**` | ReactFlow integration |
| `*.test.tsx` | Tests may render raw elements |
| `*.stories.tsx` | Storybook may show examples |

### Manual Exceptions (eslint-disable)

For one-off cases, use inline disable comments:

```tsx
// Single line
// eslint-disable-next-line react/forbid-elements -- [REASON]
<button>...</button>

// Block
/* eslint-disable react/forbid-elements -- [REASON] */
<button>...</button>
<input>...</input>
/* eslint-enable react/forbid-elements */
```

## Color Exceptions

### Semantic Colors Required

Raw Tailwind colors are blocked:

| Blocked | Use Instead |
|---------|-------------|
| `red-*` | `error-*` |
| `green-*` | `success-*` |
| `blue-*` | `primary-*` |
| `yellow-*`, `amber-*` | `warning-*` |
| `cyan-*` | `info-*` |
| `purple-*` | `insight-*` |
| `orange-*` | `grafana-*` |

### Gray vs Neutral

`gray-*` is recommended to migrate to `neutral-*` but not blocked (4,000+ usages).

Use the migration script for bulk updates:

```bash
./scripts/migrate-gray-to-neutral.sh --dry-run src/components/UI
./scripts/migrate-gray-to-neutral.sh src/components/UI
```

## Import Exceptions

### Barrel Imports Required

Import from `@/components/UI` instead of direct files:

```tsx
// Good
import { Button, Badge, Card } from "@/components/UI";

// Blocked - Use barrel import
import { Button } from "@/components/UI/Button";
```

### cn() Required

Use `cn()` from `@/utils/cn` instead of clsx/classnames:

```tsx
// Good
import { cn } from "@/utils/cn";

// Blocked
import clsx from "clsx";
```

## Form Component Intentional Exceptions

The following form components are intentionally NOT using design system primitives due to specialized requirements:

### Toggle/Switch Exceptions

| File | Reason |
|------|--------|
| `layout/FeatureFlagToggle.tsx` | Specialized inline toggle with dynamic mode labels (Hybrid/Legacy) that change color based on state. The custom visual feedback and inline layout is integral to the feature flag debugging UX. |
| `components/UI/Toggle.tsx` | Defines the Toggle primitive itself |

### Input Exceptions

| File | Reason |
|------|--------|
| `components/Chat/ChatInputForm.tsx` | Hidden file inputs for attachment functionality. Uses visually-hidden pattern with custom dropzone integration. |
| `components/DevTools/TimelineBar.tsx` | Range input (scrubber) for media timeline control. Specialized slider behavior not suitable for Slider component. |

### Checkbox Exceptions

All raw `<input type="checkbox">` have been migrated to `<Checkbox>` as of January 2025.

### Form Component Migration Status (January 2025)

| Component | Files Migrated | Status |
|-----------|---------------|--------|
| Toggle | 17 toggles across 5 files | Complete |
| Checkbox | 2 checkboxes across 2 files | Complete |
| Input | Uses Input component | Complete |
| Select | Uses Select component | Complete |
| Textarea | Uses Textarea component | Complete |
| Slider | Uses Slider component | Complete |
| RadioGroup | Uses RadioGroup component | Complete |
| FileInput | Uses FileInput component | Complete |

**Key Files Migrated:**
- `components/Settings/SettingsPanel.tsx` - 13 toggles migrated
- `components/Agents/ThinkingBudgetCard.tsx` - 1 toggle migrated
- `components/Settings/AccessibilitySettings.tsx` - 4 toggles (via SettingToggle wrapper)
- `components/Export/ExportDialog.tsx` - 2 toggles (via OptionToggle wrapper)
- `generative/InteractiveForm.tsx` - 1 checkbox migrated
- `components/Chat/ExportButton.tsx` - 1 checkbox migrated

## Requesting New Exceptions

1. Check if the use case fits existing exception categories
2. If not, discuss with the team before adding to `eslint.config.js`
3. Document the rationale in this file

## Compliance Metrics

Track adoption with:

```bash
npm run check:design-system
```

Current metrics are reported in pre-push hooks.

## Related Documentation

- [Design System Documentation](./DESIGN_SYSTEM.md)
- [Color Utilities](../../src/mcp_server_langgraph/studio/frontend/src/utils/colors.ts)
- [Design Tokens](../../src/mcp_server_langgraph/studio/frontend/src/types/design-tokens.ts)
