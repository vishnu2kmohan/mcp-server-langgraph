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

## Semantic Colors

The design system uses **semantic color names** instead of raw Tailwind colors:

| Semantic Color | Use Case | Light Mode | Dark Mode |
|----------------|----------|------------|-----------|
| `error-*` | Errors, destructive actions | `error-600` | `error-400` |
| `success-*` | Success, confirmations | `success-600` | `success-400` |
| `warning-*` | Warnings, cautions | `warning-600` | `warning-400` |
| `primary-*` | Primary actions | `primary-600` | `primary-400` |
| `info-*` | Informational, cloud/infrastructure | `info-600` | `info-400` |
| `insight-*` | AI features, suggestions | `insight-600` | `insight-400` |
| `grafana-*` | Observability, Grafana | `grafana-500` | `grafana-400` |

### Color Mapping Reference

| Raw Color | Semantic | Example |
|-----------|----------|---------|
| `red-*` | `error-*` | `text-red-500` → `text-error-500` |
| `green-*` | `success-*` | `bg-green-100` → `bg-success-100` |
| `blue-*` | `primary-*` | `border-blue-500` → `border-primary-500` |
| `yellow-*`, `amber-*` | `warning-*` | `text-yellow-600` → `text-warning-600` |
| `cyan-*` | `info-*` | `text-cyan-500` → `text-info-500` |
| `purple-*` | `insight-*` | `text-purple-500` → `text-insight-500` |
| `orange-*` | `grafana-*` | Use `GRAFANA_COLORS` constant |

### ESLint Color Enforcement

```javascript
// eslint.config.js - prevents raw color usage
{
  selector: "Literal[value=/\\b(text|bg|border|ring|hover:border)-(red|green|blue|yellow|amber|cyan|purple|orange)-\\d+/]",
  message: "Use semantic colors (error-*, success-*, warning-*, primary-*, info-*, insight-*, grafana-*)",
}
```

## Color Utilities

### Global Utilities (`src/utils/colors.ts`)

```typescript
import {
  STATUS_BADGE_STYLES,    // Badge styles by status
  INTERACTIVE_COLORS,     // Hover states by type
  CONFIDENCE_COLORS,      // AI confidence levels
  AI_INSIGHT_COLORS,      // AI feature styling
  GRAFANA_COLORS,         // Grafana integration
  getStatusBadgeStyle,    // Dynamic badge style
  getConfidenceColor,     // Color by score
  getRiskLevelColor,      // Risk level colors
  getComplianceStatusColor, // Compliance colors
  getAIInsightStyle,      // AI style variants
  getGrafanaButtonStyle,  // Grafana button
} from '../utils/colors';
```

### AI Insight Colors

```typescript
AI_INSIGHT_COLORS.text   // text-insight-600 dark:text-insight-400
AI_INSIGHT_COLORS.bg     // bg-insight-50 dark:bg-insight-900/30
AI_INSIGHT_COLORS.badge  // Full badge styling
```

### Grafana Colors

```typescript
GRAFANA_COLORS.primary   // #F46800 (official brand)
GRAFANA_COLORS.button    // Button styling
GRAFANA_COLORS.text      // Text styling
```

## Reusable UI Components

### StatusBadge

```tsx
import { StatusBadge } from '../components/UI';

<StatusBadge status="success">Active</StatusBadge>
<StatusBadge status="error" showIcon>Failed</StatusBadge>
<StatusBadge status="warning" size="sm" pill>Pending</StatusBadge>
```

### ConfidenceIndicator

```tsx
import { ConfidenceIndicator } from '../components/UI';

<ConfidenceIndicator score={0.85} />           // "85%"
<ConfidenceIndicator score={0.85} label="AI" /> // "AI: 85%"
```

Color thresholds: High (≥0.9) → success, Medium (≥0.7) → warning, Low (<0.7) → error

### RiskBadge

```tsx
import { RiskBadge } from '../components/UI';

<RiskBadge level="low" />       // Green
<RiskBadge level="high" showIcon /> // Red with icon
<RiskBadge level="critical" label="Severity" />
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
