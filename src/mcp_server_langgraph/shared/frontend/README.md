# Shared Frontend

Shared frontend components, hooks, and design tokens for MCP Server LangGraph.

This package serves as the **Single Source of Truth (SSOT)** for:
- Design tokens (colors, typography, spacing)
- UI primitives (Button, Card, Badge, Input)
- Common hooks (accessibility, metrics, i18n)
- Tailwind preset for consistent styling

## Installation

```bash
npm install @mcp-server-langgraph/shared-frontend
```

## Quick Start

```tsx
// Import components
import { Button, Card, Badge, Input } from '@mcp-server-langgraph/shared-frontend/primitives';

// Import hooks
import { useHeartMetrics, useWebVitals, useDarkMode } from '@mcp-server-langgraph/shared-frontend/hooks';

// Import i18n
import { initI18n, useAppTranslation } from '@mcp-server-langgraph/shared-frontend/i18n';

// Import design tokens
import { colors, typography } from '@mcp-server-langgraph/shared-frontend/styles';

// Import utilities
import { cn } from '@mcp-server-langgraph/shared-frontend/utils';
```

## Package Exports

| Export | Description |
|--------|-------------|
| `./primitives` | UI primitives (Button, Card, Badge, Input) |
| `./hooks` | React hooks (metrics, accessibility, dark mode) |
| `./i18n` | Internationalization (react-i18next) |
| `./styles` | Design tokens (colors, typography) |
| `./utils` | Utilities (cn, class merging) |
| `./tailwind-preset` | Tailwind CSS preset |

## Components

### UI Primitives

All primitives use [CVA (class-variance-authority)](https://cva.style/) for type-safe variants.

#### Button

```tsx
import { Button } from '@mcp-server-langgraph/shared-frontend/primitives';

<Button variant="primary" size="md">Save</Button>
<Button variant="secondary" size="sm">Cancel</Button>
<Button variant="destructive" isLoading>Deleting...</Button>
<Button variant="ghost">View More</Button>
```

**Variants:** `primary`, `secondary`, `ghost`, `destructive`
**Sizes:** `sm`, `md`, `lg`

#### Card

```tsx
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@mcp-server-langgraph/shared-frontend/primitives';

<Card variant="elevated">
  <CardHeader>
    <CardTitle>Project Settings</CardTitle>
  </CardHeader>
  <CardContent>
    <p>Configure your project...</p>
  </CardContent>
  <CardFooter>
    <Button>Save</Button>
  </CardFooter>
</Card>
```

**Variants:** `default`, `outlined`, `elevated`

#### Badge

```tsx
import { Badge } from '@mcp-server-langgraph/shared-frontend/primitives';

<Badge variant="success">Active</Badge>
<Badge variant="warning">Pending</Badge>
<Badge variant="error">Failed</Badge>
<Badge variant="info">New</Badge>
```

**Variants:** `default`, `success`, `warning`, `error`, `info`, `outline`

#### Input

```tsx
import { Input } from '@mcp-server-langgraph/shared-frontend/primitives';

<Input placeholder="Enter email" />
<Input variant="error" aria-invalid="true" />
<Input disabled />
```

## Hooks

### useWebVitals

Collects Core Web Vitals (LCP, CLS, INP, FCP, TTFB) with persona context.

```tsx
import { useWebVitals } from '@mcp-server-langgraph/shared-frontend/hooks';

function App() {
  const { metrics, isCollecting, exportMetrics } = useWebVitals({
    persona: 'admin',
    userId: 'user:123',
    onMetric: (metric) => {
      // Send to analytics backend
      console.log(`${metric.name}: ${metric.value}ms (${metric.rating})`);
    },
  });

  return (
    <div>
      {metrics.LCP && <p>LCP: {metrics.LCP.value}ms</p>}
      {metrics.CLS && <p>CLS: {metrics.CLS.value}</p>}
    </div>
  );
}
```

**Features:**
- Respects Do Not Track browser setting
- Includes persona context in all metrics
- Exports metrics for backend reporting

### useHeartMetrics

HEART framework metrics (Happiness, Engagement, Adoption, Retention, Task Success).

```tsx
import { HeartMetricsProvider, useHeartMetrics } from '@mcp-server-langgraph/shared-frontend/hooks';

// Wrap your app
<HeartMetricsProvider>
  <App />
</HeartMetricsProvider>

// In components
function MyComponent() {
  const {
    trackTaskStart,
    trackTaskComplete,
    trackFeatureUsed,
    recordNPSScore,
    isTrackingEnabled,
  } = useHeartMetrics();

  const handleSave = async () => {
    trackTaskStart('save_project');
    try {
      await saveProject();
      trackTaskComplete('save_project');
    } catch (error) {
      trackTaskError('save_project', error.message);
    }
  };

  return <Button onClick={handleSave}>Save</Button>;
}
```

### useDarkMode

System-aware dark mode with persistence.

```tsx
import { useDarkMode } from '@mcp-server-langgraph/shared-frontend/hooks';

function ThemeToggle() {
  const { isDarkMode, toggle, setMode } = useDarkMode();

  return (
    <button onClick={toggle}>
      {isDarkMode ? 'Light Mode' : 'Dark Mode'}
    </button>
  );
}
```

### useAccessibility

Accessibility utilities (focus trap, announcements, skip links).

```tsx
import { useFocusTrap, useAnnounce, useSkipLink } from '@mcp-server-langgraph/shared-frontend/hooks';

function Modal({ isOpen, children }) {
  const { trapRef } = useFocusTrap({ enabled: isOpen });
  const { announce } = useAnnounce();

  useEffect(() => {
    if (isOpen) announce('Dialog opened');
  }, [isOpen]);

  return <div ref={trapRef}>{children}</div>;
}
```

## Internationalization (i18n)

Uses [react-i18next](https://react.i18next.com/) with bundled translations.

### Setup

```tsx
// In app entry point
import { initI18n } from '@mcp-server-langgraph/shared-frontend/i18n';

await initI18n();
```

### Usage

```tsx
import { useAppTranslation } from '@mcp-server-langgraph/shared-frontend/i18n';

function Navigation() {
  const { t } = useAppTranslation();

  return (
    <nav>
      <a href="/projects">{t('nav.projects')}</a>
      <a href="/chat">{t('nav.chat')}</a>
      <a href="/workflows">{t('nav.workflows')}</a>
    </nav>
  );
}
```

### Available Translation Keys

```
nav.projects      -> "Projects"
nav.chat          -> "Chat"
nav.workflows     -> "Workflows"
nav.agents        -> "Agents"
nav.settings      -> "Settings"

actions.save      -> "Save"
actions.cancel    -> "Cancel"
actions.delete    -> "Delete"
actions.create    -> "Create"

status.loading    -> "Loading..."
status.success    -> "Success"
status.error      -> "Error"

errors.generic    -> "Something went wrong. Please try again."
errors.network    -> "Network error. Please check your connection."

a11y.skipToContent -> "Skip to main content"
a11y.loading       -> "Loading, please wait"
```

### Language Detection

By default, i18n detects language from:
1. localStorage (`i18nextLng`)
2. Browser navigator
3. HTML lang attribute

Fallback: English (`en`)

## Tailwind Preset

Use the shared Tailwind preset for consistent styling.

### tailwind.config.ts

```typescript
import sharedPreset from '@mcp-server-langgraph/shared-frontend/tailwind-preset';

export default {
  presets: [sharedPreset],
  content: ['./src/**/*.{ts,tsx}'],
  // Local overrides...
};
```

### Design Tokens

The preset includes:
- **Colors:** primary, success, warning, error scales
- **Typography:** Inter (sans), JetBrains Mono (mono)
- **Spacing:** Consistent scale
- **Dark mode:** Built-in support

## Utilities

### cn()

Merge Tailwind classes with conflict resolution.

```tsx
import { cn } from '@mcp-server-langgraph/shared-frontend/utils';

<div className={cn(
  'p-4 bg-white',
  isActive && 'bg-blue-500 text-white',
  className
)}>
  ...
</div>
```

## Testing

```bash
npm test              # Watch mode
npm run test:run      # Single run
npm run test:coverage # With coverage
```

All components include:
- Unit tests with Vitest
- Accessibility tests with jest-axe
- WCAG 2.2 AA compliance validation

## Accessibility

All components are designed for WCAG 2.2 AA compliance:
- Focus-visible styles
- ARIA attributes
- Keyboard navigation
- Screen reader support

### A11yDevTools (Development Only)

```tsx
import { A11yDevTools } from '@mcp-server-langgraph/shared-frontend/components';

// In development, shows accessibility violations in console
function App() {
  return (
    <>
      <A11yDevTools />
      <MainApp />
    </>
  );
}
```

## Architecture

```
src/
├── components/
│   ├── primitives/     # Button, Card, Badge, Input
│   ├── A11yDevTools.tsx
│   └── index.ts
├── hooks/
│   ├── useAccessibility.ts
│   ├── useDarkMode.ts
│   ├── useHeartMetrics.tsx
│   ├── useWebVitals.tsx
│   └── index.ts
├── i18n/
│   └── index.ts        # i18n configuration + hooks
├── styles/
│   └── design-tokens.ts
├── utils/
│   └── cn.ts
├── tailwind-preset.ts  # ESM export
└── tailwind-preset.cjs # CommonJS export
```

## Contributing

1. Write tests first (TDD)
2. Ensure WCAG 2.2 AA compliance
3. Export from appropriate index.ts
4. Update this README
