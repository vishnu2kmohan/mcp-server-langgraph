# Frontend Component Style Guide

This guide documents the patterns and conventions for creating UI components in the Agent Studio frontend.

## Quick Reference

| Pattern | Usage |
|---------|-------|
| CVA | All components with variants |
| cn() | `import { cn } from "../../utils/cn"` |
| Barrel import | `import { Button, Badge } from "@/components/UI"` |
| Type exports | `NonNullable<VariantProps<typeof variants>["prop"]>` |

---

## CVA (Class Variance Authority)

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
          "bg-brand-primary text-white",
          "hover:bg-primary-600",
          "dark:bg-primary-600 dark:hover:bg-primary-500",
        ],
        secondary: [
          "bg-neutral-100 dark:bg-neutral-800 text-neutral-900",
          "hover:bg-neutral-200",
          "dark:text-neutral-100",
        ],
      },
      size: {
        sm: "px-2 py-1 text-xs",
        md: "px-3 py-1.5 text-sm",
        lg: "px-4 py-2 text-base",
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

## Naming Conventions

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

### Props Interface

```typescript
// Pattern: {ComponentName}Props
// Extends HTMLAttributes + VariantProps
export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}
```

---

## Import Patterns

### Always Use

```typescript
// cn() utility - ALWAYS import from utils
import { cn } from "../../utils/cn";

// CVA imports
import { cva, type VariantProps } from "class-variance-authority";

// Barrel imports for UI components
import { Button, Badge, Card } from "@/components/UI";
```

### Never Use

```typescript
// NEVER define local cn()
function cn(...classes) { ... }  // DON'T

// NEVER import clsx/classnames
import clsx from "clsx";  // DON'T

// NEVER import individual UI files
import { Button } from "@/components/UI/Button";  // DON'T
```

---

## Color Usage

### Semantic Colors (Required)

| Semantic | Raw (Blocked) | Usage |
|----------|---------------|-------|
| `error-*` | `red-*` | Errors, destructive |
| `success-*` | `green-*` | Success, positive |
| `warning-*` | `yellow-*`, `amber-*` | Cautions |
| `primary-*` | `blue-*` | Primary actions |
| `info-*` | `cyan-*` | Informational |
| `insight-*` | `purple-*` | AI features |
| `neutral-*` | `gray-*` | General UI |

### Examples

```typescript
// GOOD - Semantic colors
"bg-error-500 text-white"
"text-success-700 dark:text-success-300"
"border-primary-500"

// BAD - Raw colors (blocked by ESLint)
"bg-red-500 text-white"
"text-green-700"
```

---

## Dark Mode

Always include dark mode variants for visibility-critical styles:

```typescript
// Pattern: light-mode dark:dark-mode
const variants = cva("base-styles", {
  variants: {
    status: {
      success: [
        "bg-success-100 text-success-700",           // Light
        "dark:bg-success-900/50 dark:text-success-300",  // Dark
      ],
    },
  },
});
```

---

## Component Categories

### Primitive Components (CVA Required)

Simple, single-purpose components that form the design system foundation:

- Button, Badge, Card, Dialog
- Input, Select, Textarea, Checkbox
- Toggle, Slider, RadioGroup
- Skeleton, Tooltip, StatusBadge

### Composite Components (Use Primitives)

Complex components that compose primitives:

- ContextMenu (uses Button)
- ConfirmDialog (uses Dialog + Button)
- SearchInput (uses Input)
- Pagination (uses Button)

Composite components may not need CVA if they primarily delegate to primitives.

---

## File Structure

```
src/components/UI/
├── Button.tsx           # Component implementation
├── Button.test.tsx      # Unit tests
├── Button.stories.tsx   # Storybook stories
└── index.ts             # Barrel export
```

### Barrel Export Pattern

```typescript
// src/components/UI/index.ts
export { Button, buttonVariants, type ButtonProps } from "./Button";
export { Badge, badgeVariants, type BadgeProps } from "./Badge";
// ... etc
```

---

## Testing Requirements

Every CVA component should test:

1. **Default variant rendering**
2. **All variant options**
3. **All size options**
4. **className merging**
5. **CVA export availability**

```typescript
describe("Button", () => {
  it("renders with default props", () => {
    render(<Button>Click</Button>);
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("applies variant classes", () => {
    render(<Button variant="danger">Delete</Button>);
    expect(screen.getByRole("button").className).toContain("bg-error");
  });

  it("exports buttonVariants for composition", async () => {
    const { buttonVariants } = await import("./Button");
    expect(typeof buttonVariants).toBe("function");
  });
});
```

---

## Storybook Requirements

Every UI component should have a story file:

```typescript
// Button.stories.tsx
import type { Meta, StoryObj } from "@storybook/react";
import { Button } from "./Button";

const meta: Meta<typeof Button> = {
  title: "Design System/Button",
  component: Button,
  tags: ["autodocs"],
  argTypes: {
    variant: {
      control: "select",
      options: ["primary", "secondary", "danger", "ghost"],
    },
    size: {
      control: "select",
      options: ["sm", "md", "lg"],
    },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Primary: Story = {
  args: { variant: "primary", children: "Primary Button" },
};

export const AllVariants: Story = {
  render: () => (
    <div className="flex gap-4">
      <Button variant="primary">Primary</Button>
      <Button variant="secondary">Secondary</Button>
      <Button variant="danger">Danger</Button>
    </div>
  ),
};
```

---

## Common Patterns

### forwardRef for Native Elements

```typescript
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant, size, className, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  )
);
Button.displayName = "Button";
```

### Compound Variants

```typescript
const alertVariants = cva("...", {
  variants: {
    variant: { info: "...", error: "..." },
    hasIcon: { true: "pl-12", false: "pl-4" },
  },
  compoundVariants: [
    {
      variant: "error",
      hasIcon: true,
      className: "border-l-4 border-error-500",
    },
  ],
});
```

### Dynamic Color (Score/Level Based)

For components where color depends on a runtime value:

```typescript
// Define static variants for size
export const indicatorVariants = cva("inline-flex items-center", {
  variants: {
    size: { sm: "text-xs", md: "text-sm", lg: "text-base" },
  },
});

// Use dynamic color helper
export function Indicator({ score, size }: Props) {
  return (
    <span className={cn(
      indicatorVariants({ size }),
      getColorByScore(score),  // Dynamic
    )}>
      {score}
    </span>
  );
}
```

---

## Checklist for New Components

- [ ] Uses CVA for all variants
- [ ] Imports cn() from utils/cn
- [ ] Exports variant function (`buttonVariants`)
- [ ] Exports type definitions
- [ ] Extends appropriate HTMLAttributes
- [ ] Includes dark mode variants
- [ ] Uses semantic colors only
- [ ] Has unit tests
- [ ] Has Storybook story
- [ ] Added to barrel export (index.ts)

---

## Related Documentation

- [Design System Exceptions](./DESIGN_SYSTEM_EXCEPTIONS.md)
- [Design Tokens](../../src/mcp_server_langgraph/studio/frontend/src/types/design-tokens.ts)
- [Color Utilities](../../src/mcp_server_langgraph/studio/frontend/src/utils/colors.ts)
- [Tailwind Config](../../src/mcp_server_langgraph/studio/frontend/tailwind.config.ts)
