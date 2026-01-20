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

## ARIA Pattern Exceptions (January 2026)

Raw `<button>` elements are **required** for certain ARIA patterns where native button semantics are necessary for proper accessibility:

### Listbox/Combobox Options

| File | Pattern | Reason |
|------|---------|--------|
| `components/Chat/HeaderModelSelector.tsx` | `role="option"` | ARIA listbox pattern requires native button for keyboard navigation |
| `components/Chat/ToolSelector.tsx` | `role="option"` | ARIA listbox pattern requires native button for keyboard navigation |

### Menu Items

| File | Pattern | Reason |
|------|---------|--------|
| `components/Chat/AttachmentMenu.tsx` | `role="menuitem"` | ARIA menu pattern requires native button for menu semantics |

### Icon-Only Close Buttons (Chips)

| File | Pattern | Reason |
|------|---------|--------|
| `components/Chat/AttachmentPreviews.tsx` | Chip close buttons | Minimal footprint icon buttons within chips |

### Canvas Interactions

| File | Pattern | Reason |
|------|---------|--------|
| `canvas/ArtifactTab.tsx` | Drag handle, close button | Specialized drag-and-drop interactions with @dnd-kit |
| `canvas/SuggestionsFooterBar.tsx` | Collapsible header, action buttons | Collapsible panel pattern |
| `canvas/ArtifactInteractionWrapper.tsx` | Popout button | Overlay interaction pattern |

### ESLint Disable Pattern

All ARIA pattern exceptions must include the reason in the ESLint disable comment:

```tsx
// eslint-disable-next-line react/forbid-elements -- ARIA listbox pattern requires native button
<button role="option" aria-selected={isSelected} onClick={handleSelect}>
  {option.label}
</button>
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

## Inline Style Exceptions (January 2026)

The following inline styles are **intentionally retained** and should not be migrated to Tailwind classes. All other inline styles should use CSS custom properties via design system utilities.

### Error Boundary Resilience (10 occurrences)

**File**: `components/ErrorBoundary/AIErrorBoundary.tsx`

Error boundaries use inline styles to ensure visual recovery even if CSS loading fails:

```tsx
// Inline styles are intentional for crash resilience
style={{
  padding: '16px',
  background: 'linear-gradient(135deg, #dc2626, #991b1b)',
  fontFamily: 'system-ui, sans-serif',
}}
```

**Rationale**: When CSS fails to load (network issues, corruption), error boundaries must still render readable UI.

### User-Selected Theme Values (3 occurrences)

**File**: `components/Settings/ThemeSettings.tsx`

Dynamic color swatches display user-selected theme colors:

```tsx
style={{ backgroundColor: primaryColor }}
style={{ fontFamily: font.fontFamily }}
```

**Rationale**: These display user-customized values that cannot be predetermined in CSS.

### Story/Demo Files (15 occurrences)

**Files**:
- `stories/ThemeSwitcher.stories.tsx`
- `stories/DataVizPalettes.stories.tsx`
- `stories/DesignTokenValidation.stories.tsx`
- `stories/Spacing.stories.tsx`

**Rationale**: Storybook demos showcase CSS variable values directly for documentation.

### Third-Party Library Constraints (3 occurrences)

**Files**:
- `components/Artifacts/SandpackExecutor.tsx` - Sandpack CSS isolation
- `components/Onboarding/GuidedTour.tsx` - Shepherd.js positioning

**Rationale**: Third-party libraries require specific inline style patterns for their APIs.

### Dynamic Positioning (Complex Calculations)

**Files with complex position calculations**:
| File | Pattern | Reason |
|------|---------|--------|
| `layout/StudioShellLayout.tsx` | Panel positions | Multi-panel resize requires runtime calculation |
| `components/DevTools/TimelineBar.tsx` | Timeline markers, cursor position | Dynamic positioning based on data |
| `components/Cost/BudgetForecastChart.tsx` | Chart elements | Data-driven positioning |
| `components/Chat/InteractiveMermaidDiagram.tsx` | Diagram pan/zoom | Transform-based pan/zoom |
| `canvas/VersionTimeline.tsx` | Timeline markers | Data-driven positioning |

**Rationale**: These require dynamic positioning calculations that cannot be expressed as static CSS classes.

### Chart & Visualization Components

**Files**:
| File | Pattern | Reason |
|------|---------|--------|
| `components/Artifacts/VegaLiteArtifact.tsx` | Container sizing | Dynamic chart dimensions |
| `components/Artifacts/ChartArtifact.tsx` | Bar heights | Dynamic data-driven heights |
| `components/Artifacts/HTMLArtifact.tsx` | Iframe sizing | Expand/collapse states |
| `components/Artifacts/InteractiveSVGArtifact.tsx` | SVG transforms | Pan/zoom transforms |
| `components/Analytics/HEARTComponents.tsx` | Score-based colors | Dynamic color based on score |

**Rationale**: Visualization libraries and interactive charts require dynamic styling based on data.

### Migrated Patterns (Use Instead of Inline Styles)

The following patterns have design system utilities and should NOT use inline styles:

| Pattern | Inline Style | Use Instead |
|---------|--------------|-------------|
| Animation delay | `style={{ animationDelay: "150ms" }}` | `className="animation-delay-150"` |
| Progress width | `style={{ width: \`${percent}%\` }}` | `className="progress-bar-fill" style={{ "--progress": \`${percent}%\` }}` |
| Dynamic height | `style={{ height: \`${height}%\` }}` | `className="dynamic-height" style={{ "--height": \`${height}%\` }}` |
| Grid columns | `style={{ gridTemplateColumns: \`repeat(${n}, ...)\` }}` | `className="grid-dynamic-cols" style={{ "--cols": n }}` |
| Tree indent | `style={{ paddingLeft: \`${depth * 16}px\` }}` | `className={getIndentClass(depth)}` or `className="tree-indent"` |
| Standard tree indent | `paddingLeft` with depth × 16 | Use `getIndentClass()` from `@/utils/indent` |
| Non-standard tree indent | `paddingLeft` with offset (e.g., +8px) | `className="tree-indent" style={{ "--indent": value }}` |

### Audit Commands

Run the inline style audit:

```bash
# Count remaining inline styles
grep -r "style={{" src/ --include="*.tsx" | wc -l

# Find inline styles excluding CSS custom properties
grep -r "style={{" src/ --include="*.tsx" | grep -v '"-\-'
```

## Keycloak Theme Alignment (January 2026)

The Keycloak login theme (`docker/keycloak/themes/agent-studio/`) is styled to match the React Studio frontend design system. Since Keycloak uses PatternFly CSS, the theme overrides PatternFly defaults with CSS `!important` rules.

### Theme Location

```
docker/keycloak/themes/agent-studio/
├── login/
│   ├── resources/css/login.css    # Main login styling
│   ├── resources/img/             # Logos and icons
│   └── theme.properties           # Theme configuration
├── account/                       # Account management theme
└── theme.properties               # Parent theme reference
```

### Design System Alignment

Both pages now use **identical** Radix color tokens and a **minimal/borderless design**:

| Element | Keycloak CSS | React Design System | Radix Token |
|---------|--------------|---------------------|-------------|
| Background start | `#111113` | `neutral-1` | `slate-1` dark |
| Background end | `#18191b` | `neutral-2` | `slate-2` dark |
| Card background | `#18191b` | `bg-neutral-2` | `slate-2` dark |
| Card border | None (borderless) | None (borderless) | - |
| Primary button | `#6e56cf` | `bg-primary-9` | `violet-9` |
| Primary hover | `#7c66dc` | `hover:bg-primary-10` | `violet-10` |
| Focus ring | `rgba(110, 86, 207, 0.5)` | `ring-primary-a3` | `violet-a3` |
| Input background | `#212225` (opacity) | `bg-neutral-3` | `slate-3` dark |
| Text primary | `#edeef0` | `text-neutral-12` | `slate-12` dark |
| Text secondary | `#b0b4ba` | `text-neutral-11` | `slate-11` dark |
| Text muted | `#777b84` | `text-neutral-10` | `slate-10` dark |
| Links | `#baa7ff` | `text-primary-11` | `violet-11` dark |
| Border radius | `1rem` (card), `0.5rem` (inputs) | `rounded-2xl`, `rounded-lg` | 16px, 8px |
| IdP button bg | `#212225` | `bg-neutral-3` | `slate-3` dark |
| IdP button hover | `#272a2d` | `hover:bg-neutral-4` | `slate-4` dark |

**Design Philosophy**: Login pages use a flat, minimal design with shadows for depth instead of borders. This aligns with modern login page trends (GitHub, Google, Vercel). All buttons (including IdP/SSO buttons) are borderless.

### Typography Alignment (January 2026)

Both login pages use **identical** typography from the design system:

| Element | Size | Weight | Tailwind | Keycloak CSS Variable |
|---------|------|--------|----------|----------------------|
| Title | 24px (1.5rem) | 700 (bold) | `text-2xl font-bold` | `--kc-font-size-2xl`, `--kc-font-weight-bold` |
| Subtitle | 14px (0.875rem) | 400 (normal) | `text-sm` | `--kc-font-size-sm`, `--kc-font-weight-normal` |
| Labels | 14px (0.875rem) | 500 (medium) | `text-sm font-medium` | `--kc-font-size-sm`, `--kc-font-weight-medium` |
| Inputs | 16px (1rem) | 400 (normal) | `text-base` | `--kc-font-size-base` |
| Primary button | 16px (1rem) | 600 (semibold) | `font-semibold` | `--kc-font-size-base`, `--kc-font-weight-semibold` |
| IdP buttons | 14px (0.875rem) | 500 (medium) | `text-sm font-medium` | `--kc-font-size-sm`, `--kc-font-weight-medium` |
| Footer | 12px (0.75rem) | 400 (normal) | `text-xs` | `--kc-font-size-xs` |

**Font Family**: Both pages use Inter as the primary font:
```css
/* React (tailwind.config.ts) */
fontFamily.sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif']

/* Keycloak (login.css) */
--kc-font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
```

### Password Field Styling

The password field uses PatternFly's input-group pattern. Custom CSS ensures:

1. **Rounded focus ring**: Applied directly on the inner input with rounded corners
2. **No vertical separator**: PatternFly's `::after` border is disabled via CSS custom properties
3. **Compact toggle**: Reduced padding on the visibility toggle button (0.75rem)
4. **Consistent hit target**: Minimum 40px touch target for accessibility

```css
/* Focus ring on input itself - matches username field */
.pf-v5-c-input-group input:focus {
  box-shadow: 0 0 0 2px var(--kc-focus-ring) !important;
}

/* Remove PatternFly's vertical separator */
.pf-v5-c-button.pf-m-control::after {
  display: none !important;
}
```

### Eye Icon Behavior

PatternFly uses **action-based** icons for the password visibility toggle:
- **Eye open** = Clicking will reveal the password
- **Eye slashed** = Clicking will hide the password

This is consistent with many login page implementations (GitHub, Google, etc.) and provides clear visual feedback about what action the button performs when clicked.

**Note**: While "state-based" icons (showing current state) are preferred by some UX researchers, the action-based approach is widely adopted and PatternFly's implementation handles the icon swapping internally. Attempting to override this with CSS transforms can cause visual inconsistencies.

### Maintenance Notes

When updating Keycloak or PatternFly versions:
1. Test the login page styling after upgrade
2. Check if PatternFly CSS class names changed (pf-c-* → pf-v5-c-*)
3. Verify focus ring behavior on input-group fields
4. Confirm no vertical separators appear in input-groups

## Related Documentation

- [Design System Documentation](./DESIGN_SYSTEM.md)
- [Design System Changelog](./DESIGN_SYSTEM_CHANGELOG.md)
- [Color Utilities](../../src/mcp_server_langgraph/studio/frontend/src/utils/colors.ts)
- [Design Tokens](../../src/mcp_server_langgraph/studio/frontend/src/types/design-tokens.ts)
- [Indent Utility](../../src/mcp_server_langgraph/studio/frontend/src/utils/indent.ts)
- [Keycloak Login CSS](../../docker/keycloak/themes/agent-studio/login/resources/css/login.css)
