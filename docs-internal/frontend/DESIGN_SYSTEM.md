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
| `neutral-*` | General UI (text, borders, backgrounds) | `neutral-700` | `neutral-100` |

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
| `gray-*` | `neutral-*` | `text-gray-500` → `text-neutral-500` |

### ESLint Color Enforcement

```javascript
// eslint.config.js - prevents raw color usage (enforced)
{
  selector: "Literal[value=/\\b(text|bg|border|ring|hover:border)-(red|green|blue|yellow|amber|cyan|purple|orange)-\\d+/]",
  message: "Use semantic colors (error-*, success-*, warning-*, primary-*, info-*, insight-*, grafana-*)",
}
// gray-* → neutral-* migration is recommended but not enforced (4000+ existing usages)
```

## Color Utilities

### Global Utilities (`src/utils/colors.ts`)

```typescript
import {
  // Badge and status styles
  STATUS_BADGE_STYLES,    // Badge styles by status (success, warning, error, info, neutral)
  INTERACTIVE_COLORS,     // Hover states by type (danger, primary, success, warning)
  CONFIDENCE_COLORS,      // AI confidence levels (high, medium, low)

  // Semantic color constants
  INFO_COLORS,            // Info/informational styling (text, bg, badge, border)
  NEUTRAL_COLORS,         // General UI styling (text, textMuted, bg, bgHover, border, etc.)
  AI_INSIGHT_COLORS,      // AI feature styling (text, bg, badge)
  GRAFANA_COLORS,         // Grafana integration (primary, button, text)

  // Helper functions
  getStatusBadgeStyle,    // Dynamic badge style by status
  getConfidenceColor,     // Color by confidence score
  getRiskLevelColor,      // Risk level colors
  getComplianceStatusColor, // Compliance status colors
  getInfoStyle,           // Info style by variant
  getNeutralStyle,        // Neutral style by variant
  getAIInsightStyle,      // AI style variants
  getGrafanaButtonStyle,  // Grafana button styling
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

### Info Colors (Cyan)

For informational content, cloud/infrastructure indicators:

```typescript
INFO_COLORS.text    // text-info-600 dark:text-info-400
INFO_COLORS.bg      // bg-info-50 dark:bg-info-900/30
INFO_COLORS.badge   // bg-info-100 text-info-700 dark:bg-info-900/50 dark:text-info-300
INFO_COLORS.border  // border-info-200 dark:border-info-800

// Or use the helper function
getInfoStyle('text')   // Returns text style
getInfoStyle('badge')  // Returns badge style
```

### Neutral Colors (Gray)

For general UI elements (text, borders, backgrounds):

```typescript
// Text variants
NEUTRAL_COLORS.text       // text-neutral-900 dark:text-neutral-100 (primary text)
NEUTRAL_COLORS.textMuted  // text-neutral-600 dark:text-neutral-400 (secondary)
NEUTRAL_COLORS.textSubtle // text-neutral-400 dark:text-neutral-500 (tertiary)

// Background variants
NEUTRAL_COLORS.bg         // bg-neutral-50 dark:bg-neutral-900 (default)
NEUTRAL_COLORS.bgHover    // bg-neutral-100 dark:bg-neutral-800 (hover state)
NEUTRAL_COLORS.bgSelected // bg-neutral-200 dark:bg-neutral-700 (selected state)

// Border variants
NEUTRAL_COLORS.border      // border-neutral-200 dark:border-neutral-700
NEUTRAL_COLORS.borderLight // border-neutral-100 dark:border-neutral-800
NEUTRAL_COLORS.divide      // divide-neutral-200 dark:divide-neutral-700

// Or use the helper function
getNeutralStyle('text')     // Returns primary text style
getNeutralStyle('textMuted') // Returns muted text style
getNeutralStyle('bg')       // Returns default background style
```

**Note:** `gray-*` is still widely used (4000+ occurrences). New code should prefer `neutral-*` for semantic consistency, but migration is ongoing.

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

## AI-Native Components

### AIEmptyState

AI-powered empty state component with persona-aware suggestions.

```tsx
import { AIEmptyState } from '../components/EmptyState';

// Basic usage
<AIEmptyState context="sessions" />

// With search filter distinction
<AIEmptyState
  context="workflows"
  emptyType="no-matches"
  searchQuery={searchQuery}
/>

// With custom action (for modals)
<AIEmptyState
  context="projects"
  onAction={() => setShowCreateDialog(true)}
  actionLabel="Create Project"
/>
```

#### Supported Contexts (13 total)

| Context | Icon | Use Case |
|---------|------|----------|
| `sessions` | MessageSquare | Chat session list |
| `projects` | FolderOpen | Project list |
| `workflows` | GitBranch | Workflow list |
| `traces` | Activity | Trace explorer |
| `messages` | MessageCircle | Message thread |
| `files` | FileText | File browser (legacy) |
| `artifacts` | FileText | Artifact browser |
| `alerts` | Bell | Alert panel |
| `connections` | Plug | MCP connections |
| `prompts` | FileCode | Prompt library |
| `tools` | Wrench | MCP tools |
| `resources` | Database | MCP resources |
| `audit` | ClipboardList | Audit log |

#### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `context` | `EmptyStateContext` | required | Context identifier |
| `emptyType` | `"empty" \| "no-matches"` | `"empty"` | Distinguish true empty vs filtered |
| `searchQuery` | `string` | - | Search query for no-matches title |
| `onAction` | `() => void` | - | Custom action callback (for modals) |
| `onNavigate` | `(path: string) => void` | - | Navigation callback |
| `actionLabel` | `string` | from registry | Override CTA button text |
| `enableAI` | `boolean` | `true` | Enable AI suggestions |

#### Registry Configuration

Each context has default configuration in `EmptyStateRegistry.ts`:

```typescript
const DEFAULT_CONFIGS = {
  artifacts: {
    title: "No artifacts yet",
    motivation: "Create or upload artifacts to use in your workflows",
    ability: "Drag and drop supported",
    action: "Upload Artifact",
    target: "modal:artifact-upload",
  },
  // ... other contexts
};
```

Persona-specific overrides are applied automatically based on user's sub-persona.

---

### CommandPaletteContext

Dynamic command registration for route-aware command palette.

```tsx
import {
  CommandPaletteProvider,
  useCommandPalette
} from '../contexts/CommandPaletteContext';

// Provider wraps the shell layout
<CommandPaletteProvider staticCommands={PALETTE_COMMANDS}>
  <StudioShellLayout />
</CommandPaletteProvider>

// Register commands dynamically
function MyComponent() {
  const { registerCommands, unregisterCommands } = useCommandPalette();

  useEffect(() => {
    const commands = [
      { id: 'my-cmd', name: 'My Command', category: 'Custom' }
    ];
    registerCommands(commands);
    return () => unregisterCommands(commands.map(c => c.id));
  }, []);
}
```

#### Route Commands Hook

```tsx
import { useRouteCommands } from '../hooks/useRouteCommands';

// Auto-registers commands for current route
function StudioShellLayout() {
  useRouteCommands(); // Registers workflow commands at /studio/workflows, etc.
  // ...
}
```

See `feature-flags-mapping.md` for complete route-to-command mapping.

---

### WidgetArtifact

Generative UI widget artifact type for dynamic chart/table/text rendering.

```typescript
// src/types/artifacts.ts
interface WidgetArtifact extends BaseArtifact {
  type: "widget";
  widgetType: "chart" | "table" | "text";
  config: {
    id: string;
    title: string;
    data: WidgetChartData | WidgetTableData | WidgetTextData;
  };
}

// Chart data
interface WidgetChartData {
  labels: string[];   // X-axis labels
  values: number[];   // Y-axis values
}

// Table data
interface WidgetTableData {
  columns: string[];           // Column headers
  rows: (string | number)[][];  // Row data
}

// Text data
interface WidgetTextData {
  content: string;  // Markdown or plain text
}
```

#### Usage in Chat

Widgets are parsed from fenced code blocks with `widget` language:

````markdown
```widget
{
  "type": "chart",
  "title": "Sales by Quarter",
  "data": {
    "labels": ["Q1", "Q2", "Q3", "Q4"],
    "values": [100, 150, 200, 175]
  }
}
```
````

The `ArtifactRenderer` component handles widget artifacts:

```tsx
// ArtifactRenderer.tsx
case "widget":
  return <GenerativeWidget config={artifact.config} />;
```

---

## Chat Input Feature Gap (Sprint 1)

The `ConnectedChatInputForm` component supports advanced features when wired through the shell path:

### Props Added

| Prop | Type | Description |
|------|------|-------------|
| `showModelSelector` | `boolean` | Show model dropdown |
| `selectedModel` | `string` | Current model ID |
| `availableModels` | `ModelOption[]` | Available models |
| `onModelChange` | `(id: string) => void` | Model change handler |
| `modelSupportsThinking` | `boolean` | Enable reasoning UI |
| `reasoningEffort` | `ReasoningEffortLevel` | Reasoning level |
| `enableThinking` | `boolean` | Thinking toggle state |
| `enableUrlFetch` | `boolean` | Enable URL content fetch |

### Feature Flags

| Flag | Purpose |
|------|---------|
| `model_selector_in_shell` | Enable model selector in shell |
| `url_fetch_in_shell` | Enable #url fetch pattern |

---

## References

- `shared-frontend/README.md` - Full API documentation
- `studio-frontend/README.md` - Studio-specific features
- `ADR-077: Design System Consolidation` - Architecture decision
- `feature-flags-mapping.md` - Feature flag documentation
