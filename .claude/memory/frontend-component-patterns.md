---
purpose: Quick reference for UI component patterns with CVA, Radix, and Tailwind
priority: high
category: frontend
last-updated: 2026-02-05
---

# Frontend Component Patterns

Quick reference for UI component development patterns.

## CVA Component Template

```typescript
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../../utils/cn";

export const componentVariants = cva("base-styles", {
  variants: {
    variant: { primary: "...", secondary: "..." },
    size: { sm: "...", md: "...", lg: "...", icon: "p-2 h-9 w-9" },
  },
  defaultVariants: { variant: "primary", size: "md" },
});

export type ComponentVariant = NonNullable<VariantProps<typeof componentVariants>["variant"]>;

export interface ComponentProps
  extends HTMLAttributes<HTMLElement>,
    VariantProps<typeof componentVariants> {}

export function Component({ variant, size, className, ...props }: ComponentProps) {
  return <div className={cn(componentVariants({ variant, size }), className)} {...props} />;
}
```

## Critical Rules

1. **ALWAYS** import cn from utils/cn: `import { cn } from "../../utils/cn";`
2. **NEVER** define local cn() function
3. **ALWAYS** use semantic colors: `error-*`, `success-*`, `primary-*`, `neutral-*`
4. **NEVER** use raw colors: `red-*`, `green-*`, `blue-*`, `gray-*`
5. **ALWAYS** use barrel imports: `import { Button } from "@/components/UI"`
6. **ALWAYS** export variant function for composition

## CVA Component Count

Current: 19/31 components use CVA (61%)

**With CVA:**
Badge, Button, Card, Checkbox, ConfidenceIndicator, Dialog, ErrorState,
FileInput, Input, RadioGroup, RiskBadge, Select, Skeleton, Slider,
StatusBadge, Textarea, TierUsageBar, Toggle, Tooltip

**Without CVA (Composite/Simple):**
BulkActionBar, ConfirmDialog, ContextMenu, CursorPagination, FilterChips,
InlineEdit, OfflineBanner, Pagination, SearchInput, SortDropdown,
StatusFilter, UpgradePrompt

## Naming Conventions

| Element | Pattern | Example |
|---------|---------|---------|
| Variant function | `{component}Variants` | `buttonVariants` |
| Type export | `{Component}{Prop}` | `ButtonVariant`, `ButtonSize` |
| Props interface | `{Component}Props` | `ButtonProps` |

## Button Sizes

| Size | Usage | Example |
|------|-------|---------|
| `sm` | Compact buttons | `<Button size="sm">` |
| `md` | Default buttons | `<Button>` |
| `lg` | Prominent buttons | `<Button size="lg">` |
| `icon` | Icon-only buttons | `<Button size="icon" variant="ghost"><Icon /></Button>` |

## Dark Mode Pattern

```typescript
status: {
  success: [
    "bg-success-100 text-success-700",           // Light
    "dark:bg-success-900/50 dark:text-success-300",  // Dark
  ],
},
```

## Dynamic Color Pattern

For score/level-based coloring:

```typescript
// Static variants in CVA
const variants = cva("base", { variants: { size: { sm: "...", md: "..." } } });

// Dynamic color via helper
<span className={cn(variants({ size }), getDynamicColor(value))} />
```

## Full Guide

See `docs-internal/frontend/STYLE.md` for complete documentation.
