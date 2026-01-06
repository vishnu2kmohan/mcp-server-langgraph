# Design System Architecture

This document describes the design system architecture for MCP Server LangGraph frontends.

## Overview

The design system is centralized in `@mcp-server-langgraph/shared-frontend`, which serves as the **Single Source of Truth (SSOT)** for:

- Design tokens (colors, typography, spacing)
- UI primitives (Button, Card, Badge, Input)
- Common hooks (accessibility, metrics, i18n)
- Tailwind CSS preset

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    shared-frontend                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Primitives │  │    Hooks    │  │    Design Tokens    │  │
│  │  Button     │  │  useWebVitals│  │  colors, typography│  │
│  │  Card       │  │  useHeartMetrics│  │  Tailwind preset │  │
│  │  Badge      │  │  useDarkMode│  │                     │  │
│  │  Input      │  │  useAccessibility│ │                  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐                           │
│  │    i18n     │  │   Utils     │                           │
│  │  react-i18next│ │   cn()     │                           │
│  │  translations│  │   CVA      │                           │
│  └─────────────┘  └─────────────┘                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Studio Frontend                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │               Studio-Specific Hooks                  │    │
│  │  usePermission, usePersonaTheme, useHeartMetricsTracker│ │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │               Redux Store Integration                 │    │
│  │  personaSlice, sessionSlice, RTK Query               │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Package Structure

### shared-frontend

```
src/
├── components/
│   ├── primitives/        # CVA-based UI components
│   │   ├── Button.tsx     # Primary interaction component
│   │   ├── Card.tsx       # Container component
│   │   ├── Badge.tsx      # Status indicator
│   │   └── Input.tsx      # Form input
│   └── A11yDevTools.tsx   # Dev-only accessibility checker
├── hooks/
│   ├── useAccessibility.ts  # Focus trap, announcements
│   ├── useDarkMode.ts       # Theme switching
│   ├── useHeartMetrics.tsx  # HEART framework metrics
│   ├── useWebVitals.tsx     # Core Web Vitals collection
│   └── useFTUXAnalytics.ts  # First-time user experience
├── i18n/
│   └── index.ts           # react-i18next configuration
├── styles/
│   └── design-tokens.ts   # Color/typography definitions
├── utils/
│   └── cn.ts              # Tailwind class merging
├── tailwind-preset.ts     # ESM Tailwind preset
└── tailwind-preset.cjs    # CommonJS Tailwind preset
```

### studio-frontend

```
src/
├── components/
│   └── Common/
│       └── KeyboardShortcutOverlay.tsx  # Keyboard shortcuts overlay
├── hooks/
│   ├── usePermission.ts           # Permission-based UI
│   ├── usePersonaTheme.ts         # Persona theming
│   ├── useHeartMetricsTracker.ts  # Enhanced metrics with persona
│   ├── useFocusTrap.ts            # Modal focus management (WCAG 2.1)
│   └── useKeyboardShortcuts.ts    # Global keyboard shortcut handler
├── layout/
│   ├── StudioShellLayout.tsx      # Main shell container
│   ├── ActivityBar.tsx            # RBAC-filtered navigation with collapsible groups
│   ├── SessionNav.tsx             # Session navigation panel
│   ├── TopBar.tsx                 # Header with section title
│   ├── ResponsiveLayout.tsx       # Breakpoint detection
│   ├── MobileDrawer.tsx           # Mobile navigation drawer
│   └── HamburgerMenu.tsx          # Mobile menu trigger
├── store/
│   └── slices/
│       ├── personaSlice.ts        # Persona state management
│       └── canvasSlice.ts         # Panel sizes, collapse states, hasCustomLayout
└── persona/
    └── PersonaVariants.ts         # Persona configuration + default presets
```

## Design Tokens

### Colors

```typescript
// Primary scale (blue)
primary: { 50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950 }

// Status colors
success: { 50-950 }  // Green
warning: { 50-950 }  // Amber
error: { 50-950 }    // Red

// Persona accents
admin: red
security-admin: orange
auditor: yellow
alice-builder: blue
alice-analyst: purple
alice-devops: cyan
compliance-officer: teal
bob: green
```

### Typography

```typescript
fontFamily: {
  sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
  mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
}
```

## Component Variants (CVA)

All primitives use [class-variance-authority](https://cva.style/) for type-safe variants.

### Button Variants

| Variant | Use Case |
|---------|----------|
| `primary` | Primary actions (Save, Submit) |
| `secondary` | Secondary actions (Cancel) |
| `ghost` | Tertiary actions (View More) |
| `destructive` | Dangerous actions (Delete) |

### Sizes

| Size | Height | Use Case |
|------|--------|----------|
| `sm` | 32px (h-8) | Compact UI, toolbars |
| `md` | 40px (h-10) | Standard buttons |
| `lg` | 48px (h-12) | Hero sections |

## Tailwind Integration

### Using the Preset

```typescript
// tailwind.config.ts
import sharedPreset from '@mcp-server-langgraph/shared-frontend/tailwind-preset';

export default {
  presets: [sharedPreset],
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      // Local overrides...
    },
  },
};
```

### ESLint Enforcement

An ESLint rule prevents importing local design tokens:

```javascript
// eslint.config.js
'no-restricted-imports': [
  'error',
  {
    patterns: [{
      group: ['**/styles/design-tokens'],
      message: 'Use @mcp-server-langgraph/shared-frontend instead',
    }],
  },
],
```

## Internationalization (i18n)

### Stage 1 (Current)

- **Languages:** English only
- **Namespaces:** `common` only
- **Bundled translations:** Fast initial load

### Stage 2 (Future)

- Additional namespaces: `studio`, `errors`
- Additional languages based on user needs
- Lazy-loaded translations

### Translation Keys

```
nav.*        - Navigation labels
actions.*    - Button/action labels
status.*     - Status messages
errors.*     - Error messages
a11y.*       - Accessibility labels
persona.*    - Persona display names
```

## Accessibility

All components comply with **WCAG 2.1 AA**:

- Focus-visible styles (`:focus-visible` with ring)
- ARIA attributes for interactive elements
- Keyboard navigation support
- Screen reader announcements

### Layout Accessibility Features

| Feature | Component | WCAG Criterion |
|---------|-----------|----------------|
| Skip-to-content link | `StudioShellLayout` | 2.4.1 Bypass Blocks |
| Focus trap in modals | `useFocusTrap` hook | 2.1.2 No Keyboard Trap |
| Keyboard shortcuts | `useKeyboardShortcuts` | 2.1.1 Keyboard |
| Collapsible groups | `ActivityBar` | 4.1.2 Name, Role, Value |

### Keyboard Shortcuts

Press `?` or `Shift+?` to display the shortcuts overlay.

| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd+K` | Open command palette |
| `Ctrl/Cmd+/` | Toggle canvas panel |
| `Ctrl/Cmd+Shift+I` | Toggle DevTools |
| `Ctrl/Cmd+Shift+F` | Toggle focus mode |
| `?` | Show shortcuts overlay |

See [KEYBOARD_SHORTCUTS.md](./KEYBOARD_SHORTCUTS.md) for complete reference.

### Testing

- **Unit tests:** jest-axe for component-level a11y
- **E2E tests:** @axe-core/playwright for page-level a11y
- **Dev tools:** A11yDevTools for real-time violations
- **Dedicated suite:** `StudioShellLayout.accessibility.test.tsx`

See [ACCESSIBILITY_IMPLEMENTATION.md](./ACCESSIBILITY_IMPLEMENTATION.md) for full compliance details.

## Metrics Collection

### Web Vitals

Collects Core Web Vitals with persona context:

- **LCP** - Largest Contentful Paint (loading)
- **CLS** - Cumulative Layout Shift (stability)
- **INP** - Interaction to Next Paint (interactivity)
- **FCP** - First Contentful Paint (perceived load)
- **TTFB** - Time to First Byte (server response)

### HEART Metrics

Full HEART framework implementation:

- **Happiness** - NPS scores, satisfaction ratings
- **Engagement** - Session duration, feature usage
- **Adoption** - Onboarding completion, feature discovery
- **Retention** - Return visits, active days
- **Task Success** - Completion rates, error rates

All metrics include persona context for per-persona analysis.

## Permission-Based UI

Studio includes hooks for conditional rendering based on user permissions.

### Pattern

```tsx
function ProtectedComponent() {
  const { allowed, reason } = usePermission('resource:action');

  if (!allowed) {
    return <DisabledState reason={reason} />;
  }

  return <FeatureComponent />;
}
```

### Admin Bypass

The `admin` persona has full access to all permissions and routes.

### Route Protection

```tsx
const { allowed } = useRoutePermission('/studio/admin');
if (!allowed) redirect('/studio/chat');
```

## Migration Notes

### From Local Tokens

Replace local token imports:

```diff
- import { colors } from '../styles/design-tokens';
+ import { colors } from '@mcp-server-langgraph/shared-frontend/styles';
```

### From Custom Buttons

Replace custom button implementations:

```diff
- <button className="bg-blue-500 px-4 py-2 rounded">Save</button>
+ import { Button } from '@mcp-server-langgraph/shared-frontend/primitives';
+ <Button variant="primary">Save</Button>
```

## References

- `shared-frontend/README.md` - Full API documentation
- `studio-frontend/README.md` - Studio-specific features
- `ADR-077: Design System Consolidation` - Architecture decision
