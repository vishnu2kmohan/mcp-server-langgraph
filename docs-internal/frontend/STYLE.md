# Frontend Component Style Guide

This guide documents the patterns and conventions for creating UI components in the Agent Studio frontend.

**Last Updated**: 2026-01-18
**Design System Version**: 2.0 (Radix Colors 1-12 Scale)

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [CVA (Class Variance Authority)](#cva-class-variance-authority)
3. [Naming Conventions](#naming-conventions)
   - 3.1 [Button Variant Guidelines](#button-variant-guidelines)
   - 3.2 [Form Field Sizing Guidelines](#form-field-sizing-guidelines)
4. [Design System Foundation](#design-system-foundation)
   - 4.1 [Color System (Radix 1-12 Scale)](#color-system-radix-1-12-scale)
   - 4.2 [Dark Mode Architecture](#dark-mode-architecture)
   - 4.3 [Borders & Separators](#borders--separators)
   - 4.4 [Shadows & Elevation](#shadows--elevation)
   - 4.5 [Border Radius & Corners](#border-radius--corners)
   - 4.6 [Spacing & Sizing Tokens](#spacing--sizing-tokens)
5. [Accessibility Requirements](#accessibility-requirements)
   - 5.1 [WCAG 2.2 Compliance Overview](#wcag-22-compliance-overview)
   - 5.2 [Color Contrast Requirements](#color-contrast-requirements)
   - 5.3 [Target Size Requirements](#target-size-requirements)
   - 5.4 [Focus & Keyboard Navigation](#focus--keyboard-navigation)
   - 5.5 [Non-Color Cues](#non-color-cues)
6. [Motion.dev Animation Patterns](#motiondev-animation-patterns)
7. [Typography & Content](#typography--content)
8. [Responsive Design Patterns](#responsive-design-patterns)
9. [Interactive Component Patterns](#interactive-component-patterns)
10. [Feedback & State Patterns](#feedback--state-patterns)
11. [Micro-interactions & Polish](#micro-interactions--polish)
12. [Dynamic Styling Patterns](#dynamic-styling-patterns)
13. [Tooling & Validation](#tooling--validation)
14. [Related Documentation](#related-documentation)

---

## 1. Quick Reference

| Pattern | Usage |
|---------|-------|
| CVA | All components with variants |
| cn() | `import { cn } from "../../utils/cn"` |
| Barrel import | `import { Button, Badge } from "@/components/UI"` (components) |
| Direct import | `import { Button } from "../components/UI/Button"` (pages) |
| Type exports | `NonNullable<VariantProps<typeof variants>["prop"]>` |
| Color scale | Radix 1-12 (NOT Tailwind 50-950) |
| Touch targets | 24px minimum (AA), 44px recommended (AAA) |
| Focus rings | `focus-visible:ring-2 focus-visible:ring-primary-9` |

### Import Pattern: Pages vs Components

**Pages** (`src/pages/*.tsx`) should use **direct imports** to avoid Rollup circular dependency warnings:

```typescript
// ✅ CORRECT for pages - direct imports
// Direct imports to avoid Rollup circular dependency warnings
// (page chunks end up separate from UI barrel)
import { Button } from "../components/UI/Button";
import { Input } from "../components/UI/Input";
import { Select } from "../components/UI/Select";
import { SkeletonList } from "../components/UI/Skeleton";

// ❌ WRONG for pages - barrel imports cause circular dependency warnings
import { Button, Input, Select } from "../components/UI";
```

**Components** (`src/components/**/*.tsx`) should use **barrel imports** for convenience:

```typescript
// ✅ CORRECT for components - barrel imports
import { Button, Badge, Dialog } from "@/components/UI";
```

**Why?** When Vite/Rollup bundles the application, page chunks and the UI barrel
can end up in different chunks. If pages import from the barrel, this creates
circular dependencies between chunks, which Rollup warns about and can lead to
broken execution order in some edge cases.

**ESLint Override**: Pages have `no-restricted-imports` disabled to allow direct imports.

---

## 2. CVA (Class Variance Authority)

All UI components with variants MUST use CVA for type-safe styling.

### Installation

```bash
npm install class-variance-authority
```

### Component Template

```typescript
/**
 * ComponentName Component
 *
 * Brief description of what this component does.
 * Uses CVA for type-safe variant management.
 */

import { cva, type VariantProps } from "class-variance-authority";
import { type HTMLAttributes } from "react";
import { cn } from "../../utils/cn";

// =============================================================================
// Variants
// =============================================================================

/**
 * ComponentName variant styles using CVA
 * Exported for use in compound components or style composition
 */
export const componentNameVariants = cva(
  // Base styles (always applied)
  "inline-flex items-center font-medium",
  {
    variants: {
      variant: {
        primary: [
          "bg-primary-9 text-white",
          "hover:bg-primary-10",
          "focus-visible:ring-2 focus-visible:ring-primary-7 focus-visible:ring-offset-2",
        ],
        secondary: [
          "bg-neutral-3 text-neutral-12",
          "hover:bg-neutral-4",
          "focus-visible:ring-2 focus-visible:ring-neutral-7 focus-visible:ring-offset-2",
        ],
      },
      size: {
        sm: "px-2 py-1 text-xs min-h-6",  // 24px - WCAG AA minimum
        md: "px-3 py-1.5 text-sm min-h-8", // 32px - Internal standard
        lg: "px-4 py-2 text-base min-h-11", // 44px - WCAG AAA / Touch
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  }
);

// =============================================================================
// Types
// =============================================================================

export type ComponentNameVariant = NonNullable<
  VariantProps<typeof componentNameVariants>["variant"]
>;
export type ComponentNameSize = NonNullable<
  VariantProps<typeof componentNameVariants>["size"]
>;

export interface ComponentNameProps
  extends HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof componentNameVariants> {
  /** Component-specific props */
  customProp?: string;
}

// =============================================================================
// Component
// =============================================================================

export function ComponentName({
  variant,
  size,
  customProp,
  className,
  children,
  ...props
}: ComponentNameProps) {
  return (
    <div
      className={cn(componentNameVariants({ variant, size }), className)}
      {...props}
    >
      {children}
    </div>
  );
}
```

---

## 3. Naming Conventions

### Variant Functions

```typescript
// Pattern: {componentName}Variants
export const buttonVariants = cva(...)
export const badgeVariants = cva(...)
export const statusBadgeVariants = cva(...)
```

### Type Exports

```typescript
// Pattern: {ComponentName}{VariantName}
export type ButtonVariant = "primary" | "secondary" | "danger";
export type ButtonSize = "sm" | "md" | "lg";
export type StatusBadgeStatus = "success" | "warning" | "error";
```

### Button Variant Guidelines

Always use semantic variants based on the button's action:

| Button Text | Required Variant | Reason |
|-------------|------------------|--------|
| Cancel, Close, Back, Dismiss, No, Never mind | `secondary` | De-emphasized dismissal actions |
| Delete, Remove, Clear, Destroy, Discard, Reset | `danger` | Destructive actions require visual warning |
| Confirm, Approve, Accept, Save, Submit, OK, Yes | `primary` | Affirmative/confirmation actions |
| Toolbar/icon-only buttons | `ghost` | Minimal visual weight for density |

**Enforcement**: Pre-commit hooks detect violations.
Fix script: `scripts/design-system.py --fix --category=variants`

```tsx
// CORRECT - Semantic variants
<Button variant="secondary">Cancel</Button>
<Button variant="danger">Delete</Button>
<Button variant="primary">Save</Button>
<Button variant="ghost" size="icon" aria-label="Settings"><Settings /></Button>

// WRONG - Using default primary for Cancel/Delete
<Button>Cancel</Button>  // Should be variant="secondary"
<Button>Delete</Button>  // Should be variant="danger"

// WRONG - className color overrides
<Button className="bg-error-9">Delete</Button>  // Use variant="danger"
```

**Accessibility**: Icon-only buttons (`size="icon"`) MUST have `aria-label` for screen readers.

### Form Field Sizing Guidelines

All form fields (Input, Select, Textarea) use a consistent `size` prop with three sizes:

| Size | Text | Padding | Usage |
|------|------|---------|-------|
| `sm` | text-xs (12px) | Compact | Dense UIs, inline forms, filters |
| `md` | text-sm (14px) | Standard | **Default** - most forms |
| `lg` | text-base (16px) | Spacious | Touch-optimized, hero forms |

**CRITICAL**: Never override field sizing via `className`. Use the `size` prop instead.

```tsx
// ✅ CORRECT - Use size prop for consistent sizing
<Input size="sm" placeholder="Search..." />
<Input size="md" placeholder="Email address" />  {/* Default */}
<Input size="lg" placeholder="Enter your message" />

<Select size="sm" options={options} />
<Textarea size="lg" rows={4} />

// ❌ WRONG - className overrides break consistency
<Input className="py-1 text-xs" />     // Use size="sm"
<Input className="px-6 py-3" />        // Use size="lg"
<Input className="h-10" />             // Use size prop
<Input className="text-base" />        // Use size="lg"

// ❌ WRONG - Arbitrary sizing values
<input className="py-[10px] px-[14px]" />  // Use Input component with size prop
```

**Why This Matters**:
1. **Visual consistency** - All fields align properly in forms
2. **Maintainability** - Change sizing in one place (component definition)
3. **Accessibility** - Size tokens ensure proper touch targets
4. **Audit compliance** - Pre-commit hooks detect className sizing overrides

**Enforcement**: Pre-commit hooks detect violations.
Audit command: `python3 scripts/design-system.py check --all`

**Sizing Override Detection Patterns**:
- `input-padding-override` - Input with `py-*`, `px-*`, `p-*` in className
- `input-text-size-override` - Input with `text-xs/sm/base/lg` in className
- `input-height-override` - Input with `h-*` in className
- `select-padding-override`, `select-text-size-override`, `select-height-override`
- `textarea-padding-override`, `textarea-text-size-override`, `textarea-height-override`
- `raw-input-arbitrary-sizing` - Raw `<input>` with `py-[...]`, `h-[...]`

### Props Interface

```typescript
// Pattern: {ComponentName}Props
// Extends HTMLAttributes + VariantProps
export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}
```

---

## 4. Design System Foundation

### 4.1 Color System (Radix 1-12 Scale)

Agent Studio uses [Radix Colors](https://www.radix-ui.com/colors) with a 1-12 step scale.
This is the **canonical scale for all code**. Legacy Tailwind 50-950 references are
deprecated and should be migrated.

#### Radix Step Usage Guide

| Radix Step | Purpose | Example |
|------------|---------|---------|
| 1-2 | App/component backgrounds | `bg-neutral-1`, `bg-primary-2` |
| 3-5 | Interactive backgrounds | `hover:bg-neutral-4`, `active:bg-neutral-5` |
| 6-8 | Borders and separators | `border-neutral-6`, `divide-neutral-7` |
| 9-10 | Solid colors (buttons, badges) | `bg-primary-9`, `hover:bg-primary-10` |
| 11-12 | Text (secondary to primary) | `text-neutral-11`, `text-primary-12` |

**Reference**: See `src/design-system/radix-colors.ts` for:
- `RADIX_STEP_USAGE` - Canonical step usage guide
- `TAILWIND_TO_RADIX_MAP` - Legacy migration mapping
- `THEME_COLOR_MAPPINGS` - Semantic color to Radix mapping

#### Semantic Color Tokens

Raw Tailwind colors are blocked by ESLint. Use semantic colors instead:

| Semantic | Raw (Blocked) | Usage |
|----------|---------------|-------|
| `error-*` | `red-*`, `rose-*` | Errors, destructive actions |
| `success-*` | `green-*`, `emerald-*`, `lime-*` | Success, positive states |
| `warning-*` | `yellow-*`, `amber-*` | Cautions, warnings |
| `primary-*` | `blue-*`, `indigo-*`, `sky-*` | Primary actions, links |
| `info-*` | `cyan-*`, `teal-*` | Informational content |
| `insight-*` | `violet-*`, `purple-*` | AI features, thinking |
| `neutral-*` | `gray-*`, `slate-*`, `zinc-*`, `stone-*` | General UI, borders |
| `grafana-*` | `orange-*` | Observability integration |

#### Migration from Tailwind 50-950 to Radix 1-12

| Tailwind Shade | Radix Step | Purpose |
|----------------|------------|---------|
| `*-50` | `*-1` or `*-2` | Subtle backgrounds |
| `*-100` | `*-2` or `*-3` | UI backgrounds |
| `*-200` | `*-4` | Hovered backgrounds |
| `*-300` | `*-5` | Active/selected |
| `*-400` | `*-7` | Borders |
| `*-500` | `*-9` | Solid colors (buttons) |
| `*-600` | `*-10` | Solid hover |
| `*-700` | `*-11` | Low contrast text |
| `*-800` | `*-11` | Secondary text |
| `*-900` | `*-12` | High contrast text |
| `*-900/30` | `*-4` | Dark mode subtle bg |

#### Color Migration Scripts

```bash
# Python script - comprehensive migration with dry-run support
python3 scripts/design-system.py --audit --category=color  # Preview
python3 scripts/design-system.py --fix --category=color    # Apply

# Legacy migration (deprecated - use unified fixer)
python3 scripts/migrate-raw-colors.py --dry-run
```

#### Exceptions (Categorical Colors)

Some files legitimately use raw Tailwind colors for categorical purposes (not semantic status):

- **NodePalette.tsx**: Node type colors (start=green, end=red, llm=blue, tool=purple)
- **TraceCanvas.tsx, TraceNode.tsx**: Trace visualization
- **ChartArtifact.tsx, InteractiveChart.tsx**: Chart/visualization colors
- **ConnectionTemplateSelector.tsx**: Template category colors
- **tokens.ts, colors.ts**: Define the raw-to-semantic mappings

These files have ESLint overrides and should NOT be migrated to semantic colors.

### 4.2 Dark Mode Architecture

Agent Studio uses **class-based dark mode** via Tailwind's `darkMode: 'class'` configuration.

#### Why Class-Based (Not Media Query)

| Approach | Detection | Control |
|----------|-----------|---------|
| **Class-based** (ours) | `.dark` class on `<html>` | App controls theme |
| **Media query** | `@media (prefers-color-scheme: dark)` | System controls theme |

Benefits:
1. Users can override system preference in the app
2. Theme persists in localStorage
3. Prevents flash of wrong theme on load

#### Radix Colors Integration (v3.0.0+)

As of Radix Colors v3.0.0, the `-dark.css` files use `.dark, .dark-theme` class selectors:

```css
/* index.css - Import BOTH light and dark */
@import "@radix-ui/colors/violet.css";      /* Light mode */
@import "@radix-ui/colors/teal.css";
@import "@radix-ui/colors/slate.css";

@import "@radix-ui/colors/violet-dark.css"; /* Dark mode (.dark class) */
@import "@radix-ui/colors/teal-dark.css";
@import "@radix-ui/colors/slate-dark.css";
```

#### Surface Background Patterns

Use Radix semantic colors (1-12 scale) - they auto-switch for dark mode:

```typescript
// ✅ PREFERRED - Radix semantic colors (auto-switch)
"bg-neutral-1"                           // App backgrounds (step 1-2)
"bg-neutral-2"                           // Card backgrounds
"bg-neutral-3"                           // Interactive backgrounds

// ❌ DEPRECATED - Redundant with Radix v3.0.0+
"bg-white dark:bg-neutral-900"           // ESLint will flag this
"bg-neutral-50 dark:bg-neutral-800"      // ESLint will flag this
```

#### Text Contrast Patterns

| Pattern | Contrast on neutral-1 | Status |
|---------|----------------------|--------|
| `text-neutral-12` | 15.8:1+ | ✅ Primary text (WCAG AAA) |
| `text-neutral-11` | 8.5:1+ | ✅ Secondary text (WCAG AAA) |
| `text-neutral-10` | 4.5:1+ | ✅ Tertiary text (WCAG AA) |
| `text-neutral-9` | 3.0:1+ | ⚠️ Low contrast (UI only) |

### 4.3 Borders & Separators

Borders use the Radix neutral scale (steps 6-8) with CSS variable tokens.

#### Border Color Scale

| Token | Radix Step | Usage | WCAG Notes |
|-------|------------|-------|------------|
| `border-neutral-6` | 6 | Subtle borders (cards, inputs) | 3:1 vs bg required |
| `border-neutral-7` | 7 | Default borders | ✅ 3:1 on neutral-1/2 |
| `border-neutral-8` | 8 | Emphasized borders (focus, active) | ✅ 4.5:1+ on neutral-1 |

```typescript
// ✅ CORRECT - Semantic border colors
"border border-neutral-7"           // Default card/container border
"border-2 border-neutral-8"         // Emphasized border
"divide-y divide-neutral-6"         // Subtle dividers

// ✅ CORRECT - Status borders
"border-l-4 border-error-9"         // Error indicator
"border-l-4 border-success-9"       // Success indicator
"border-2 border-primary-9"         // Focus/selected state

// ❌ WRONG - Raw color values
"border-gray-200"                   // Use border-neutral-6
"border-slate-300"                  // Use border-neutral-7
```

#### Border Width Tokens

| Class | Width | Usage |
|-------|-------|-------|
| `border` | 1px | Default borders |
| `border-2` | 2px | Emphasized, focus states |
| `border-4` | 4px | Status indicators (left/top edge) |
| `border-0` | 0px | Remove borders |

#### Divider Patterns

```typescript
// Horizontal divider
<hr className="border-t border-neutral-6" />

// Vertical divider (flex context)
<div className="w-px h-6 bg-neutral-6" />

// List dividers
<ul className="divide-y divide-neutral-6">
  {items.map(item => <li key={item.id}>{item.name}</li>)}
</ul>
```

### 4.4 Shadows & Elevation

Shadows create visual hierarchy through elevation. All shadows use CSS variables.

#### Shadow Token Scale

| Token | CSS Variable | Usage |
|-------|--------------|-------|
| `shadow-none` | `--shadow-none` | Remove shadow |
| `shadow-sm` | `--shadow-sm` | Subtle lift (hover states) |
| `shadow` / `shadow-md` | `--shadow-md` | Default cards, dropdowns |
| `shadow-lg` | `--shadow-lg` | Popovers, tooltips |
| `shadow-xl` | `--shadow-xl` | Modals, dialogs |
| `shadow-2xl` | `--shadow-2xl` | Maximum elevation |
| `shadow-inner` | `--shadow-inner` | Inset (pressed states) |

#### Semantic Shadow Aliases

| Token | Purpose | Equivalent |
|-------|---------|------------|
| `shadow-soft` | Subtle elevation (cards) | ~shadow-sm |
| `shadow-elevated` | Floating elements (dropdowns) | ~shadow-lg |
| `shadow-modal` | Full-page overlays | ~shadow-2xl |

```typescript
// ✅ CORRECT - Semantic shadows
<Card className="shadow-soft" />           // Cards, panels
<Dropdown className="shadow-elevated" />   // Floating menus
<Dialog className="shadow-modal" />        // Modals

// ✅ CORRECT - Interactive shadow transitions
<Card className="shadow-soft hover:shadow-md transition-shadow duration-fast" />
```

#### Dark Mode Shadow Adjustments

In dark mode, shadows are less visible. Consider:

```typescript
// Option 1: Increase shadow intensity
"shadow-md dark:shadow-lg"

// Option 2: Add subtle border for definition
"shadow-soft dark:shadow-none dark:border dark:border-neutral-7"

// Option 3: Use colored glow (sparingly)
"dark:shadow-[0_0_15px_rgba(139,92,246,0.15)]"  // Primary glow
```

#### Elevation Hierarchy

| Level | Z-Index | Shadow | Components |
|-------|---------|--------|------------|
| 0 | Base | none | Page background |
| 1 | 0 | shadow-soft | Cards, panels |
| 2 | dropdown | shadow-elevated | Dropdowns, popovers |
| 3 | modal | shadow-modal | Modals, dialogs |
| 4 | toast | shadow-xl | Toasts, notifications |
| 5 | system-alert | shadow-2xl | System alerts |

#### Z-Index Token Scale

Agent Studio uses semantic z-index tokens to ensure consistent layering.
**Always use semantic tokens (not raw z-10, z-20, etc.)** for maintainability.

| Token | CSS Variable | Value | Usage |
|-------|--------------|-------|-------|
| `z-tooltip` | `--z-tooltip` | 10 | Tooltips, hover cards |
| `z-dropdown` | `--z-dropdown` | 50 | Dropdown menus, speed selectors, popovers |
| `z-panel` | `--z-panel` | 50 | Floating panels, sidebars |
| `z-command-palette` | `--z-command-palette` | 55 | Command palette overlay |
| `z-modal` | `--z-modal` | 60 | Modal dialogs |
| `z-notification` | `--z-notification` | 65 | In-app notifications |
| `z-system-alert` | `--z-system-alert` | 70 | Critical system alerts |
| `z-toast` | `--z-toast` | 75 | Toast notifications (highest priority) |

```typescript
// ✅ CORRECT - Semantic z-index tokens
<div className="absolute z-dropdown ...">
  <DropdownMenu />
</div>

<Dialog className="fixed z-modal ...">
  <DialogContent />
</Dialog>

// ❌ WRONG - Raw z-index values (blocked by ESLint)
<div className="absolute z-10 ...">  // Use z-tooltip or z-dropdown
<div className="absolute z-50 ...">  // Use z-dropdown or z-panel
```

**Common Mistake**: Using `z-10` for dropdowns. This causes occlusion when
dropdowns overlap with other fixed elements. Always use `z-dropdown` (50)
for menus that must appear above content.

**DevTools Note**: Dropdowns inside DevTools panels (like speed selectors,
filter menus) should use `z-dropdown` to ensure they appear above the tab bar.

### 4.5 Border Radius & Corners

Border radius creates visual softness and component identity.

#### Radius Token Scale

| Token | CSS Variable | Pixels | Usage |
|-------|--------------|--------|-------|
| `rounded-none` | `--radius-none` | 0px | Sharp corners (tables, code) |
| `rounded-sm` | `--radius-sm` | 2px | Subtle rounding |
| `rounded` | `--radius-DEFAULT` | 4px | Default (buttons, inputs) |
| `rounded-md` | `--radius-md` | 6px | Medium elements |
| `rounded-lg` | `--radius-lg` | 8px | Cards, dialogs |
| `rounded-xl` | `--radius-xl` | 12px | Large cards, panels |
| `rounded-2xl` | `--radius-2xl` | 16px | Hero cards |
| `rounded-3xl` | `--radius-3xl` | 24px | Feature cards |
| `rounded-full` | `--radius-full` | 9999px | Pills, avatars |

#### Component-Specific Radius Guidelines

| Component | Recommended | Reason |
|-----------|-------------|--------|
| Button | `rounded` or `rounded-md` | Standard interactive feel |
| Input | `rounded` or `rounded-md` | Match buttons for forms |
| Card | `rounded-lg` or `rounded-xl` | Container prominence |
| Dialog/Modal | `rounded-xl` or `rounded-2xl` | Overlay distinction |
| Badge/Chip | `rounded-full` | Pill shape |
| Avatar | `rounded-full` | Circular |
| Tooltip | `rounded-md` | Compact, informational |
| Code block | `rounded-md` or `rounded-lg` | Technical content |

#### Nested Radius Calculation

When elements are nested, inner radius should be smaller:

```
Inner radius = Outer radius - Padding

Example: Card with rounded-lg (8px) and p-4 (16px) padding
→ Inner element should use rounded-md (6px) or rounded (4px)
```

```typescript
// ✅ CORRECT - Nested radius hierarchy
<Card className="rounded-xl p-4">      {/* 12px radius, 16px padding */}
  <div className="rounded-lg p-3">      {/* 8px radius, 12px padding */}
    <Button className="rounded-md">     {/* 6px radius */}
      Action
    </Button>
  </div>
</Card>

// ❌ WRONG - Same radius at all levels
<Card className="rounded-lg">
  <div className="rounded-lg">
    <Button className="rounded-lg">Misaligned</Button>
  </div>
</Card>
```

### 4.6 Spacing & Sizing Tokens

The design system uses Tailwind's spacing scale (4px base unit).

#### Valid Token Reference

Use Tailwind's standard spacing scale. Avoid arbitrary values.

```typescript
// ✅ CORRECT - Standard Tailwind spacing
"p-4"        // 16px
"m-2"        // 8px
"gap-3"      // 12px
"w-64"       // 256px
"h-10"       // 40px

// ❌ WRONG - Arbitrary values without justification
"p-[20px]"   // Use p-5 (20px)
"m-[15px]"   // Use m-4 (16px) or m-3.5 (14px)
"h-[42px]"   // Use h-10 (40px) or h-11 (44px)
```

#### Semantic Size Tokens

| Token | Value | Usage |
|-------|-------|-------|
| `max-h-modal` | `90vh` | Modal max height |
| `max-h-panel` | `80vh` | Panel max height |
| `max-h-drawer` | `70vh` | Drawer max height |
| `min-h-touch` | `44px` | WCAG AAA touch target |
| `min-h-input-rich` | `100px` | Multiline input |
| `w-dialog-sm` | `300px` | Small dialog |
| `w-dialog-md` | `500px` | Medium dialog |
| `w-dialog-lg` | `600px` | Large dialog |
| `w-dialog-xl` | `800px` | Wide dialog (tables, code) |
| `max-w-message` | `70%` | Chat message bubble |

```typescript
// ✅ Use semantic tokens
<Dialog className="max-h-modal w-dialog-md">

// ❌ Avoid arbitrary values
<Dialog className="max-h-[90vh] w-[500px]">
```

#### Legitimate Arbitrary Values

The following arbitrary sizing patterns are **intentionally exempted**:

| Category | Example | Justification |
|----------|---------|---------------|
| Viewport-relative | `max-h-[90vh]` | Responsive layouts |
| Percentage | `max-w-[70%]` | Proportional sizing |
| Calc-based | `h-[calc(100vh-48px)]` | Dynamic layouts |
| WCAG touch targets | `min-h-[44px]` | Accessibility requirement |
| Workflow nodes | `min-w-[180px]` | Visual consistency |
| Table columns | `min-w-[100px]` | Data alignment |
| Truncation | `max-w-[120px]` | Text overflow |

---

## 5. Accessibility Requirements

### 5.1 WCAG 2.2 Compliance Overview

**Principle**: WCAG AA is mandatory; WCAG AAA is aspirational but not blocking.

| Criterion | Level | Requirement | Description |
|-----------|-------|-------------|-------------|
| **1.4.1 Use of Color** | A | **REQUIRED** | Color cannot be only indicator |
| **1.4.3 Contrast (Minimum)** | AA | **REQUIRED** | 4.5:1 for normal text |
| **1.4.10 Reflow** | AA | **REQUIRED** | No horizontal scroll at 320px |
| **1.4.11 Non-text Contrast** | AA | **REQUIRED** | 3:1 for UI components |
| **2.2.2 Pause, Stop, Hide** | A | **REQUIRED** | User controls for auto-play |
| **2.4.7 Focus Visible** | AA | **REQUIRED** | Visible focus indicator |
| **2.4.11 Focus Not Obscured** | AA | **REQUIRED** | Focus not hidden by content |
| **2.5.8 Target Size (Minimum)** | AA | **REQUIRED** | 24×24 CSS px minimum |
| **2.3.3 Animation from Interactions** | AAA | RECOMMENDED | reduced-motion support |
| **2.4.13 Focus Appearance** | AAA | OPTIONAL | 3:1 focus indicator contrast |

**Practical Application:**
- All AA requirements are blocking for merge
- AAA requirements are tracked but not blocking
- Use `// TODO: AAA enhancement` comments for deferred AAA work

### 5.2 Color Contrast Requirements

#### Text Contrast by Radix Step

| Usage | Radix Step | Contrast vs neutral-1 | WCAG Status |
|-------|------------|----------------------|-------------|
| Primary text | 12 | 15.8:1+ | ✅ AAA |
| Secondary text | 11 | 8.5:1+ | ✅ AAA |
| Tertiary text | 10 | 4.5:1+ | ✅ AA |
| Disabled/placeholder | 9 | 3.0:1+ | ⚠️ UI only |

#### Primary Color Usage

**IMPORTANT**: `primary-9` (#3b82f6) achieves ~3.7:1 contrast on white background.

| Usage | Correct | Notes |
|-------|---------|-------|
| Solid button backgrounds | `bg-primary-9` with white text | ✅ 4.5:1+ |
| Text on light backgrounds | `text-primary-11` or `text-primary-12` | ✅ 4.5:1+ |
| Text on dark backgrounds | `text-primary-9` | ✅ Works in dark mode |

```typescript
// ✅ CORRECT - White text on solid background
<Button className="bg-primary-9 text-white">Submit</Button>

// ✅ CORRECT - High-contrast text on light bg
<a className="text-primary-11 hover:text-primary-12">Link</a>

// ❌ WRONG - primary-9 text on light bg (fails AA for normal text)
<span className="text-primary-9">Important</span>  // Use text-primary-11
```

### 5.3 Target Size Requirements

WCAG 2.5.8 specifies minimum sizes for interactive elements.

| Size | WCAG Level | Requirement | Use Case |
|------|------------|-------------|----------|
| 24×24 CSS px | **AA (minimum)** | **REQUIRED** | All interactive elements |
| 32×32 CSS px | Internal standard | RECOMMENDED | Desktop pointer targets |
| 44×44 CSS px | AAA | OPTIONAL | Mobile touch, enhanced accessibility |

**Compliance Strategy:**
- **REQUIRED**: All interactive elements must meet 24×24 minimum (AA)
- **RECOMMENDED**: Use 32×32 for desktop, 44×44 for mobile where practical
- **OPTIONAL**: 44×44 (AAA) is aspirational, not blocking

```typescript
// WCAG 2.5.8 minimum (Level AA) - REQUIRED
"min-h-6 min-w-6"        // 24×24 CSS px - absolute minimum

// Internal standard (exceeds AA) - RECOMMENDED
"min-h-8 min-w-8"        // 32×32 CSS px - desktop pointer

// WCAG AAA / Mobile best practice - OPTIONAL
"min-h-11 min-w-11"      // 44×44 CSS px - touch targets
"min-h-touch min-w-touch" // 44px semantic token
```

### 5.4 Focus & Keyboard Navigation

All interactive elements MUST have visible focus indicators (WCAG 2.4.7 AA).

#### Focus Visible Requirements

```typescript
// ✅ REQUIRED - Visible focus ring (meets 2.4.7 AA)
"focus-visible:ring-2 focus-visible:ring-primary-9 focus-visible:ring-offset-2"

// ✅ High contrast focus for dark mode
"dark:focus-visible:ring-primary-9 dark:focus-visible:ring-offset-neutral-1"

// ❌ FORBIDDEN - Removing focus outline without replacement
"outline-none"  // Only allowed if focus-visible ring is present
"focus:outline-none"  // MUST pair with focus-visible styles
```

#### Focus Ring Standard Pattern

```typescript
// Standard focus ring (use in all interactive components)
const focusRing = cn(
  "focus-visible:outline-none",
  "focus-visible:ring-2",
  "focus-visible:ring-primary-9",
  "focus-visible:ring-offset-2",
  "dark:focus-visible:ring-offset-neutral-1"
);
```

#### Keyboard Patterns by Component

| Component | Required Keys | ARIA |
|-----------|--------------|------|
| Button | Enter, Space | `role="button"` if not `<button>` |
| Accordion | Enter, Space, Arrow (optional) | `aria-expanded`, `aria-controls` |
| Dialog | Escape to close, Tab trap | `role="dialog"`, `aria-modal` |
| Menu | Arrows, Enter, Escape | `aria-haspopup`, `aria-expanded` |
| Tabs | Arrows, Enter/Space | `role="tablist"`, `aria-selected` |
| Checkbox | Space | `aria-checked` |
| Switch/Toggle | Space, Enter | `aria-checked`, `role="switch"` |

### 5.5 Non-Color Cues

Status, errors, and scores MUST include non-color indicators (WCAG 1.4.1).

#### Status Indicators

```typescript
// ✅ CORRECT - Color + icon + text
<Badge variant="success">
  <CheckCircle className="h-4 w-4 mr-1" aria-hidden="true" />
  Active
</Badge>

// ❌ WRONG - Color only
<Badge className="bg-success-9">Active</Badge>
```

#### Score/Level-Based Colors

```typescript
// ✅ CORRECT - Color + numeric label
<div className={getScoreColor(score)}>
  <span className="sr-only">Score:</span>
  {score}%
  <span className="sr-only">{getScoreLabel(score)}</span>
</div>

// ❌ WRONG - Color only indicates severity
<div className={getScoreColor(score)} />
```

#### Charts and Visualizations

For data visualization, combine color with:
- Pattern fills (diagonal, dots, crosshatch)
- Shape differentiation (circle, square, triangle)
- Direct labels on data points

See `radix-colors.ts` for `NODE_TYPE_STYLES` with pattern overlays.

---

## 6. Motion.dev Animation Patterns

All complex animations use [Motion.dev](https://motion.dev/) (`motion/react`) for
declarative, physics-based animations.

**Accessibility Note**: Motion.dev provides the `useReducedMotion()` hook and
`MotionConfig` component to detect user preferences, but **accessibility support
must be implemented by developers** using these primitives.

### Core Imports

```typescript
// Standard animation imports
import { motion, AnimatePresence, useReducedMotion } from "motion/react";

// Pre-built variants from design system
import {
  shimmerVariants,
  accordionVariants,
  cardHoverVariants,
  listContainerVariants,
  listItemVariants,
} from "../../../design-system/micro-interactions";
```

### Available Animation Variants

| Variant | Purpose | Usage |
|---------|---------|-------|
| `shimmerVariants` | Loading skeleton shimmer | Loading states, skeletons |
| `accordionVariants` | Expand/collapse content | Tree views, details panels |
| `cardHoverVariants` | Card hover lift effect | Clickable cards, items |
| `listContainerVariants` | Staggered list container | Parent of staggered children |
| `listItemVariants` | Individual list item animation | Children in staggered lists |
| `dropdownVariants` | Dropdown menu animation | Menus, filter dropdowns |

### Reduced Motion Support

Agent Studio implements reduced motion as a best practice (exceeds WCAG AA).

| WCAG Criterion | Level | Requirement | Our Implementation |
|----------------|-------|-------------|-------------------|
| 2.2.2 Pause, Stop, Hide | A | **REQUIRED** | Auto-play disabled; user controls |
| 2.3.3 Animation from Interactions | AAA | RECOMMENDED | `prefers-reduced-motion` support |

**Practical Guidance:**
- Essential animations (loading indicators, transitions under 300ms) are exempt
- Decorative animations (shimmer, parallax) should respect reduced motion
- If `useReducedMotion()` adds significant complexity, skip and document

```typescript
function AnimatedComponent() {
  const prefersReducedMotion = useReducedMotion();

  return (
    <motion.div
      // Pass undefined when reduced motion is preferred
      variants={prefersReducedMotion ? undefined : cardHoverVariants}
      initial="rest"
      whileHover="hover"
    >
      Content
    </motion.div>
  );
}
```

### Pattern: Loading Skeleton with Accessibility

```typescript
function LoadingSkeleton() {
  const prefersReducedMotion = useReducedMotion();

  return (
    <div
      aria-busy="true"
      aria-label="Loading content"
      data-testid="loading-skeleton"
    >
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          aria-hidden="true"  // Decorative shimmer
          className={cn(
            "h-10 bg-neutral-3 rounded",
            // Disable shimmer animation when reduced motion preferred
            !prefersReducedMotion && "animate-shimmer bg-gradient-to-r from-neutral-3 via-neutral-2 to-neutral-3"
          )}
        />
      ))}
    </div>
  );
}
```

### Pattern: Accordion with ARIA

```typescript
function AccordionItem({ isExpanded, title, children }: Props) {
  const prefersReducedMotion = useReducedMotion();
  const contentId = useId();

  return (
    <div>
      <button
        aria-expanded={isExpanded}
        aria-controls={contentId}
        onClick={onToggle}
      >
        {title}
      </button>
      <AnimatePresence initial={false}>
        {isExpanded && (
          <motion.div
            id={contentId}
            role="region"
            variants={prefersReducedMotion ? undefined : accordionVariants}
            initial="collapsed"
            animate="expanded"
            exit="collapsed"
            className="overflow-hidden"
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
```

### Testing Animation Integration

```typescript
// Mock motion/react for tests
const mockMotionDiv = vi.fn();

vi.mock("motion/react", () => ({
  motion: {
    div: (props: Record<string, unknown>) => {
      const { variants, initial, animate, whileHover, exit, ...rest } = props;
      // Track calls for assertions
      mockMotionDiv(props);
      return <div data-motion-variants={variants ? "true" : "false"} {...rest} />;
    },
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useReducedMotion: vi.fn(() => false),
}));

beforeEach(() => {
  mockMotionDiv.mockClear();
});

// Test reduced motion compliance
it("should respect reduced motion preference", async () => {
  const { useReducedMotion } = await import("motion/react");
  vi.mocked(useReducedMotion).mockReturnValue(true);

  render(<AnimatedComponent />);

  // Verify variants are undefined when reduced motion is preferred
  const motionCalls = mockMotionDiv.mock.calls;
  const hasUndefinedVariants = motionCalls.some(
    (call) => call[0]?.variants === undefined
  );
  expect(hasUndefinedVariants).toBe(true);
});
```

### Animation Checklist

- [ ] Import variants from `design-system/micro-interactions`
- [ ] Use `useReducedMotion()` hook
- [ ] Pass `undefined` variants when reduced motion is preferred
- [ ] Include `data-testid` for loading/animated states
- [ ] Wrap exit animations in `<AnimatePresence>`
- [ ] Use `overflow-hidden` for accordion animations
- [ ] Add `aria-busy` for loading states
- [ ] Test reduced motion compliance

---

## 7. Typography & Content

Typography establishes visual hierarchy and readability.

### Font Scale

| Class | Size | Line Height | Usage |
|-------|------|-------------|-------|
| `text-xs` | 12px | 16px | Captions, metadata |
| `text-sm` | 14px | 20px | Secondary text, form labels |
| `text-base` | 16px | 24px | Body text (default) |
| `text-lg` | 18px | 28px | Emphasized body |
| `text-xl` | 20px | 28px | Card titles |
| `text-2xl` | 24px | 32px | Section headings |
| `text-3xl` | 30px | 36px | Page headings |
| `text-4xl` | 36px | 40px | Hero headings |

### Font Weight Guidelines

| Weight | Class | Usage |
|--------|-------|-------|
| 400 | `font-normal` | Body text, descriptions |
| 500 | `font-medium` | Labels, navigation, emphasis |
| 600 | `font-semibold` | Headings, buttons, important UI |
| 700 | `font-bold` | Strong emphasis (use sparingly) |

### Reading Width Optimization

Optimal reading width is 45-75 characters per line:

```typescript
// ✅ CORRECT - Constrained reading width
<article className="max-w-prose">  {/* ~65ch */}
  <p>Long-form content...</p>
</article>

// Chat messages
<div className="max-w-message">  {/* 70% of container */}
  {message.content}
</div>

// ❌ WRONG - Full-width text
<p className="w-full">Difficult to read at wide viewports...</p>
```

### Text Truncation Patterns

```typescript
// Single-line truncation
<span className="truncate max-w-[200px]">Long text here</span>

// Multi-line clamp (2 lines)
<p className="line-clamp-2">Multi-line text that may overflow...</p>

// Multi-line clamp (3 lines)
<p className="line-clamp-3">Even longer content...</p>

// Always provide full text via title or tooltip
<span className="truncate" title={fullText}>{fullText}</span>
```

### Code Typography

```typescript
// Inline code
<code className="px-1.5 py-0.5 bg-neutral-3 rounded text-sm font-mono">
  variable
</code>

// Code blocks
<pre className="p-4 bg-neutral-2 rounded-lg overflow-x-auto">
  <code className="text-sm font-mono">{codeContent}</code>
</pre>
```

---

## 8. Responsive Design Patterns

Agent Studio is mobile-first with progressive enhancement.

### Breakpoint Strategy

| Breakpoint | Prefix | Min Width | Target Devices |
|------------|--------|-----------|----------------|
| Default | - | 0px | Mobile phones |
| sm | `sm:` | 640px | Large phones, small tablets |
| md | `md:` | 768px | Tablets |
| lg | `lg:` | 1024px | Laptops, small desktops |
| xl | `xl:` | 1280px | Desktops |
| 2xl | `2xl:` | 1536px | Large desktops |

### Mobile-First Approach

Always start with mobile styles, then add larger breakpoint overrides:

```typescript
// ✅ CORRECT - Mobile-first
<div className="flex flex-col md:flex-row gap-4">
  <Sidebar className="w-full md:w-64" />
  <Main className="flex-1" />
</div>

// ❌ WRONG - Desktop-first (harder to maintain)
<div className="flex flex-row md:flex-col">...</div>
```

### Touch vs Pointer Optimization

```typescript
// Larger touch targets on touch devices
<Button className="min-h-10 @pointer-coarse:min-h-12">
  Touch-friendly
</Button>

// Hover effects only on pointer devices
<Card className="@hover:hover:shadow-lg">
  Hover-aware
</Card>
```

### Reflow at 320px (WCAG 1.4.10)

Content must reflow at 320px without horizontal scrolling:

```typescript
// ✅ CORRECT - Responsive with constraints
<Dialog className="w-full max-w-dialog-lg">
  <DialogContent className="p-4 sm:p-6">
    Content reflows naturally
  </DialogContent>
</Dialog>

// ❌ WRONG - Fixed width breaks reflow
<Dialog className="min-w-[700px]">
  Breaks on mobile
</Dialog>
```

### Stack-to-Row Patterns

```typescript
// Horizontal on desktop, stacked on mobile
<div className="flex flex-col sm:flex-row gap-4">
  <div className="flex-1">Left/Top</div>
  <div className="flex-1">Right/Bottom</div>
</div>

// Grid that collapses
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
  {items.map(item => <Card key={item.id} />)}
</div>
```

---

## 9. Interactive Component Patterns

### Accordion Pattern

```typescript
<div>
  <button
    aria-expanded={isExpanded}
    aria-controls="accordion-content"
    className="flex items-center justify-between w-full p-4"
  >
    <span>Section Title</span>
    <ChevronDown className={cn(
      "transition-transform",
      isExpanded && "rotate-180"
    )} />
  </button>
  <div
    id="accordion-content"
    role="region"
    hidden={!isExpanded}
  >
    Content
  </div>
</div>
```

### Dialog/Modal Pattern

```typescript
<Dialog>
  <DialogTrigger asChild>
    <Button>Open Dialog</Button>
  </DialogTrigger>
  <DialogContent className="w-full max-w-dialog-lg">
    <DialogHeader>
      <DialogTitle>Dialog Title</DialogTitle>
      <DialogDescription>Description text</DialogDescription>
    </DialogHeader>
    <div className="p-4 sm:p-6">
      {/* Content */}
    </div>
    <DialogFooter>
      <Button variant="secondary">Cancel</Button>
      <Button variant="primary">Confirm</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

### Hover Cards with Touch Fallback

```typescript
function HoverCard({ children, content }: Props) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => setIsOpen(false)}
      onFocus={() => setIsOpen(true)}
      onBlur={() => setIsOpen(false)}
    >
      <button
        aria-expanded={isOpen}
        onClick={() => setIsOpen(!isOpen)} // Touch fallback
      >
        {children}
      </button>
      {isOpen && (
        <div role="tooltip">
          {content}
        </div>
      )}
    </div>
  );
}
```

---

## 10. Feedback & State Patterns

Provide clear feedback for all user actions and system states.

### Loading States

#### Skeleton Loading (Preferred)

```typescript
function SkeletonCard() {
  const prefersReducedMotion = useReducedMotion();

  return (
    <div aria-busy="true" aria-label="Loading content">
      <div
        aria-hidden="true"
        className={cn(
          "h-4 w-3/4 rounded bg-neutral-3",
          !prefersReducedMotion && "animate-shimmer"
        )}
      />
    </div>
  );
}
```

**Timing Guidelines:**
- Show skeleton immediately for slow operations
- Keep skeleton for minimum 300ms to avoid flash
- Auto-disable shimmer animation after 5s (prevents battery drain)

#### Progress Indicators

| Type | Use When | Accessibility |
|------|----------|---------------|
| Determinate bar | Progress is known (uploads, multi-step) | `role="progressbar"` with `aria-valuenow` |
| Indeterminate bar | Duration unknown but finite | `role="progressbar"` without valuenow |
| Spinner | Brief wait (<3s expected) | `role="status"` with `aria-live` |

```typescript
// Accessible Progress Bar
<div
  role="progressbar"
  aria-valuenow={percentage}
  aria-valuemin={0}
  aria-valuemax={100}
  aria-label={label}
  className="h-2 bg-neutral-3 rounded-full overflow-hidden"
>
  <div
    className={cn(
      "progress-bar-fill bg-success-9 rounded-full",
      "motion-safe:transition-all motion-safe:duration-normal",
      "motion-reduce:transition-none"
    )}
    style={{ '--progress': `${percentage}%` } as React.CSSProperties}
  />
</div>
```

### Empty States

Empty states should be actionable and helpful:

```typescript
function EmptyState({ icon, title, description, action }: Props) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <div className="mb-4 text-neutral-9" aria-hidden="true">
        {icon}
      </div>
      <h3 className="text-lg font-semibold text-neutral-12">{title}</h3>
      <p className="mt-1 text-sm text-neutral-11 max-w-md">{description}</p>
      {action && (
        <Button className="mt-4" variant="primary">
          {action.label}
        </Button>
      )}
    </div>
  );
}
```

### Error States

#### Inline Validation

```typescript
// Field-level error
<div className="space-y-1">
  <Input
    aria-invalid={!!error}
    aria-describedby={error ? "email-error" : undefined}
    className={error ? "border-error-9 focus:ring-error-9" : ""}
  />
  {error && (
    <p id="email-error" className="text-sm text-error-11 flex items-center gap-1">
      <AlertCircle className="h-4 w-4" aria-hidden="true" />
      {error}
    </p>
  )}
</div>
```

#### Form Error Summary

```typescript
// Error summary at top of form
<div role="alert" className="p-4 bg-error-2 border border-error-6 rounded-lg">
  <h2 className="font-semibold text-error-11 flex items-center gap-2">
    <AlertCircle className="h-5 w-5" />
    Please fix {errors.length} error{errors.length > 1 ? 's' : ''}
  </h2>
  <ul className="mt-2 list-disc list-inside text-sm text-error-11">
    {errors.map(e => <li key={e.field}>{e.message}</li>)}
  </ul>
</div>
```

### Success Feedback

```typescript
// Toast notification
<Toast variant="success">
  <CheckCircle className="h-5 w-5" aria-hidden="true" />
  <span>Changes saved successfully</span>
</Toast>

// Inline confirmation (replaces button temporarily)
<Button
  onClick={handleSave}
  className={saved ? "bg-success-9" : "bg-primary-9"}
  disabled={saved}
>
  {saved ? (
    <>
      <Check className="h-4 w-4 mr-1" /> Saved
    </>
  ) : (
    "Save"
  )}
</Button>
```

---

## 11. Micro-interactions & Polish

Subtle animations and transitions that enhance usability.

### Hover/Focus Feedback

All interactive elements should respond to hover/focus:

```typescript
// Button hover
"transition-colors duration-fast hover:bg-primary-10"

// Card hover with lift
"transition-all duration-fast hover:shadow-md hover:-translate-y-0.5"

// Link underline animation
"underline-offset-2 hover:underline"

// Icon button
"transition-colors duration-fast hover:bg-neutral-4 rounded-md p-2"
```

### Button Press States

```typescript
// Active/pressed state
"active:scale-[0.98] active:bg-primary-10"

// Or with Motion.dev
<motion.button
  whileTap={{ scale: 0.98 }}
  className="..."
>
  Click me
</motion.button>
```

### Input Focus Transitions

```typescript
// Input focus
"transition-all duration-fast focus-visible:ring-2 focus-visible:ring-primary-9 focus-visible:border-primary-9"

// Textarea expansion on focus
"transition-all duration-normal focus:min-h-[120px]"
```

### List Item Interactions

```typescript
<li
  className={cn(
    "px-4 py-2 cursor-pointer transition-colors duration-fast",
    "hover:bg-neutral-3 active:bg-neutral-4",
    selected && "bg-primary-3 hover:bg-primary-4"
  )}
>
  {item.name}
</li>
```

### Transition Timing Guidelines

| Interaction | Duration | Easing |
|-------------|----------|--------|
| Hover state | 100-150ms | ease-out |
| Focus ring | 100ms | ease-out |
| Button press | 100ms | ease-out |
| Dropdown open | 150-200ms | ease-out |
| Modal open | 200-300ms | spring |
| Page transition | 200-300ms | ease-in-out |
| Toast appear | 200ms | spring |

**Rule of thumb**: Faster for direct manipulation (buttons), slower for layout changes (modals).

---

## 12. Dynamic Styling Patterns

### Progress Bar Pattern

For progress bars with dynamic width, use CSS custom properties:

```css
/* src/index.css */
.progress-bar-fill {
  width: var(--progress, 0%);
  @apply h-full transition-all duration-normal ease-out;
}

.progress-bar-primary { @apply progress-bar-fill bg-primary-9; }
.progress-bar-success { @apply progress-bar-fill bg-success-9; }
.progress-bar-warning { @apply progress-bar-fill bg-warning-9; }
.progress-bar-error   { @apply progress-bar-fill bg-error-9; }
```

```typescript
// ✅ CORRECT - CSS custom property for dynamic width
<div
  className="progress-bar-fill bg-success-9 rounded-full"
  style={{ '--progress': `${percentage}%` } as React.CSSProperties}
/>

// ❌ WRONG - Inline style for width
<div
  className="h-full bg-success-9 rounded-full"
  style={{ width: `${percentage}%` }}
/>
```

### Tree Indentation Pattern

For tree views, use the `getIndentClass()` utility:

```typescript
import { getIndentClass } from "@/utils/indent";

// Returns: 'pl-0', 'pl-4', 'pl-8', etc. for depths 0-6
getIndentClass(0);  // → 'pl-0'
getIndentClass(1);  // → 'pl-4'
getIndentClass(2);  // → 'pl-8'
getIndentClass(3);  // → 'pl-12'
```

```typescript
// ✅ CORRECT - Using getIndentClass utility
<div className={cn("flex items-center", getIndentClass(depth))}>
  {children}
</div>

// ❌ WRONG - Inline style for padding
<div style={{ paddingLeft: `${depth * 16}px` }}>
  {children}
</div>
```

---

## 13. Tooling & Validation

### ESLint Integration

The project's ESLint config includes design system rules:

| Rule | Severity | Description |
|------|----------|-------------|
| `no-restricted-syntax` | error | Blocks raw Tailwind colors |
| `no-restricted-syntax` | warn | Flags legacy neutral-XXX (50-950) |

### Design System Audit

```bash
# Full audit
npm run audit:design-system

# Strict mode (fails on errors)
npm run audit:design-system:strict

# Show fix suggestions
npm run audit:design-system -- --fix

# JSON output for CI
npm run audit:design-system -- --json
```

### Unified Design System Fixer

```bash
# Audit all categories
python scripts/design-system.py --audit

# Audit specific category
python scripts/design-system.py --audit --category=color
python scripts/design-system.py --audit --category=a11y
python scripts/design-system.py --audit --category=variants

# Apply fixes (dry-run first)
python scripts/design-system.py --fix --dry-run --all
python scripts/design-system.py --fix --all

# Fix specific path
python scripts/design-system.py --fix --path=pages/
```

### Pre-commit Hook Integration

Design system violations are caught by pre-commit hooks:

```bash
# Hook: check-design-system-violations (in pre-commit stage)
# Scans for: legacy neutrals, raw Tailwind colors, non-token z-index
```

### CI Pipeline Integration

```yaml
# .github/workflows/ci.yaml
- name: Design System Audit
  run: npm run audit:design-system -- --strict
```

### IDE Integration

#### VS Code Extensions

```json
{
  "recommendations": [
    "dbaeumer.vscode-eslint",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode"
  ]
}
```

#### Tailwind CSS IntelliSense

Configure for CVA and cn() pattern recognition:

```json
{
  "tailwindCSS.experimental.classRegex": [
    ["cva\\(([^)]*)\\)", "[\"'`]([^\"'`]*).*?[\"'`]"],
    ["cn\\(([^)]*)\\)", "[\"'`]([^\"'`]*).*?[\"'`]"]
  ]
}
```

### Deprecation Tracking

Maintain a deprecation log in `reports/DEPRECATION_TRACKING.md`:

```markdown
# Deprecation Log

| Hook/Component | Deprecated | Replacement | Remove By |
|----------------|------------|-------------|-----------|
| useAutoSessionTitle | v1.8 | useSessionAutoName | v2.0 |
| neutral-50..950 | v1.9 | neutral-1..12 | v2.0 |
```

---

## 14. Related Documentation

- [Design System Changelog](./DESIGN_SYSTEM_CHANGELOG.md)
- [Design System Exceptions](./DESIGN_SYSTEM_EXCEPTIONS.md)
- [Accessibility Implementation](./ACCESSIBILITY_IMPLEMENTATION.md)
- [Design Tokens](../../src/mcp_server_langgraph/studio/frontend/src/types/design-tokens.ts)
- [Radix Colors](../../src/mcp_server_langgraph/studio/frontend/src/design-system/radix-colors.ts)
- [Animation Tokens](../../src/mcp_server_langgraph/studio/frontend/src/design-system/animation-tokens.ts)
- [Color Utilities](../../src/mcp_server_langgraph/studio/frontend/src/utils/colors.ts)
- [Tailwind Config](../../src/mcp_server_langgraph/studio/frontend/tailwind.config.ts)
- [ESLint Config (color rules)](../../src/mcp_server_langgraph/studio/frontend/eslint.config.js)
- [Storybook Token Validation](../../src/mcp_server_langgraph/studio/frontend/src/stories/DesignTokenValidation.stories.tsx)

---

## Appendix A: Component Checklist

For new components:

- [ ] Uses CVA for all variants
- [ ] Imports cn() from utils/cn
- [ ] Exports variant function (`buttonVariants`)
- [ ] Exports type definitions
- [ ] Extends appropriate HTMLAttributes
- [ ] Uses Radix 1-12 color scale (not Tailwind 50-950)
- [ ] Includes dark mode support (auto via Radix)
- [ ] Has visible focus ring (focus-visible:ring-2)
- [ ] Meets 24px minimum touch target (WCAG 2.5.8 AA)
- [ ] Uses semantic Button variants
- [ ] Has unit tests
- [ ] Has Storybook story
- [ ] Added to barrel export (index.ts)

---

## Appendix B: Test ID Conventions

All components MUST use `data-testid` attributes for testability.

### Naming Pattern

```typescript
// Pattern: {scope}-{element}[-{modifier}]
data-testid="chat-input-form"
data-testid="model-selector-button"
data-testid="send-button-loading"
```

### Rules

| Rule | Example | Bad Example |
|------|---------|-------------|
| Use kebab-case | `file-upload-button` | `fileUploadButton` |
| Scope to component | `chat-input-form` | `form` |
| Use semantic names | `send-button` | `button-1` |
| State suffix for variants | `send-button-loading` | `loading-send-button` |

### Dynamic IDs

```typescript
// Pattern: {scope}-{element}-{id}
data-testid={`file-card-${file.id}`}
data-testid={`model-option-${model.id}`}
```

---

## Appendix C: Feature Flag Conventions

### API/Backend Feature Flags

Backend flags use short names (no prefix):

```python
# Pattern: {feature_name}
workflow_from_chat: bool = True
ai_suggestions: bool = True
```

### Frontend Feature Flags

Frontend flags use the `enable` prefix:

```typescript
// Pattern: enable{FeatureName}
interface Props {
  enableAI?: boolean;
  enableHITL?: boolean;
}
```

### Flag Lifecycle

| Stage | Duration | Action |
|-------|----------|--------|
| alpha | Sprint 1-2 | Hidden behind flag, dev only |
| beta | Sprint 3-4 | Flag defaults to `false`, opt-in |
| ga | Sprint 5+ | Flag defaults to `true`, opt-out |
| removed | After 2 sprints at GA | Flag removed, feature always on |

---

## Appendix D: Unit Selection (rem vs px)

### When to Use rem (Scalable)

| Category | Examples | Rationale |
|----------|----------|-----------|
| Typography | `text-sm`, `text-lg` | Respects user font size |
| Spacing | `p-4`, `m-2`, `gap-3` | Scales with text |
| Layout widths | `max-w-prose`, `w-64` | Maintains readability |
| Border radius | `rounded-lg` | Visual proportion |

### When to Use px (Fixed)

| Category | Examples | Rationale |
|----------|----------|-----------|
| WCAG touch targets | `min-h-[44px]` | WCAG specifies exact pixels |
| Icon containers | `w-6 h-6` | Fixed visual consistency |
| Border widths | `border`, `border-2` | Exact lines |
| Shadow offsets | Box shadows | Visual precision |

```typescript
// Touch target with scalable padding
<button
  className={cn(
    "min-h-[44px] min-w-[44px]",  // Fixed accessibility
    "p-3",                         // Scalable padding
    "text-sm",                     // Scalable text
  )}
>
  <Icon className="w-5 h-5" />
</button>
```
