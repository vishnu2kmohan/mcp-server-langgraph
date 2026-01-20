# Design System Changelog

Track design system evolution, migrations, and tooling improvements.

---

## [2026-01-15] Raw Color Token Migration & Pre-commit Hook

### Overview

Comprehensive migration of raw Tailwind colors (`text-white`, `bg-black`) to Radix semantic tokens (`text-neutral-12`, `bg-neutral-12`) across 100+ files. Added automated pre-commit hook to prevent future violations.

### Root Cause: Dark Mode Theme Issues

Login, OAuth callback, and onboarding pages showed light backgrounds in dark mode because:
- Used `from-neutral-12 to-neutral-11` for gradients (inverted Radix semantics)
- Used `text-white`, `bg-black` which don't respond to theme changes
- Button components missing `variant` prop defaulted to purple primary

### Infrastructure Added

| File | Purpose |
|------|---------|
| `.pre-commit-hooks/check_frontend_design_system.py` | Pre-commit hook to detect color violations |
| `scripts/fix-design-system-colors.py` | Bulk fix script for color token migration |
| `.pre-commit-config.yaml` | Added `frontend-design-system` hook at pre-commit stage |

### Patterns Fixed

| Pattern | Before | After |
|---------|--------|-------|
| Text contrast | `text-white` | `text-neutral-12` |
| Dark backgrounds | `bg-black`, `bg-black/50` | `bg-neutral-12`, `bg-neutral-12/50` |
| Light backgrounds | `bg-white` | `bg-neutral-1` |
| Redundant dark mode | `dark:text-white` | (removed - Radix handles) |
| Inverted gradients | `from-neutral-12 to-neutral-11` | `from-neutral-1 to-neutral-2` |
| Button variants | `<Button className="...">` | `<Button variant="ghost" className="...">` |

### Files Fixed

- `pages/LoginPage.tsx` - Fixed inverted gradient semantics
- `pages/AuthCallbackPage.tsx` - Fixed inverted semantics and text colors
- `pages/OAuth2CallbackPage.tsx` - Replaced all inline hex colors
- `components/Onboarding/OnboardingWizard.tsx` - Added Button variants, fixed text colors
- 100+ component files via bulk-fix script

### Prevention

The new pre-commit hook catches:
- Raw Tailwind colors: `text-white`, `bg-black`, `border-white`, etc.
- Inline hex/rgba colors in styles
- Redundant `dark:` prefixes for colors
- Button components without `variant` prop (warning)

Run manually: `python .pre-commit-hooks/check_frontend_design_system.py`
Auto-fix: `python src/mcp_server_langgraph/studio/frontend/scripts/fix-design-system-colors.py`

---

## [2026-01-15] Inline Styles Migration to CSS Custom Properties

### Overview

Comprehensive audit and migration of inline styles to design system conventions across 54 files with 106 violations.

### Infrastructure Added

| File | Purpose |
|------|---------|
| `src/utils/indent.ts` | `getIndentClass()` utility for tree indentation |
| `src/index.css` | Progress bar utilities (`.progress-bar-fill`, color variants) |
| `src/index.css` | Dynamic styling utilities (`.dynamic-height`, `.grid-dynamic-cols`, `.tree-indent`, `.position-left`) |
| `tailwind.config.ts` | Semantic sizing tokens (modal, panel, dialog, touch) |
| `tailwind.config.ts` | Animation delay plugin (`animation-delay-0`, `animation-delay-150`, `animation-delay-300`, etc.) |
| `src/design-system/animation-utilities.test.ts` | TDD contract tests for animation utilities |

### Migration Scripts Created

| Script | Purpose | Fixes Applied |
|--------|---------|---------------|
| `scripts/migrate-inline-styles.py` | Automated pattern detection and migration | 9 auto-fixes |
| `scripts/fix-progress-bars.py` | Progress bar CSS variable migration | 21 fixes |
| `scripts/fix-duplicate-classnames.py` | Merge duplicate className attributes with `cn()` | 3 fixes |

### Key Pattern Changes

**Progress Bars (Before):**
```tsx
style={{ width: `${percentage}%` }}
```

**Progress Bars (After):**
```tsx
className="progress-bar-fill"
style={{ '--progress': `${percentage}%` } as React.CSSProperties}
```

**Tree Indentation (Before):**
```tsx
style={{ paddingLeft: `${depth * 16}px` }}
```

**Tree Indentation (After):**
```tsx
className={cn("flex items-center", getIndentClass(depth))}
```

**Animation Delays (Before):**
```tsx
style={{ animationDelay: "150ms" }}
```

**Animation Delays (After):**
```tsx
className="animate-bounce animation-delay-150"
```

**Dynamic Heights (Before):**
```tsx
style={{ height: `${height}%` }}
```

**Dynamic Heights (After):**
```tsx
className="dynamic-height"
style={{ "--height": `${height}%` } as React.CSSProperties}
```

**Dynamic Grid Columns (Before):**
```tsx
style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
```

**Dynamic Grid Columns (After):**
```tsx
className="grid-dynamic-cols"
style={{ "--cols": cols } as React.CSSProperties}
```

### Components Updated

- `ProgressIndicator.tsx` - Uses `progress-bar-fill` class with `--progress` CSS variable
- `MessageBubble.tsx` - Uses `animation-delay-*` classes for typing indicator
- `MessageList.tsx` - Uses `animation-delay-*` classes for streaming indicator
- `TokenUsageDashboard.tsx` - Uses `dynamic-height` class with `--height` CSS variable
- `TimelineBar.tsx` - Uses `dynamic-height` class with `--height` CSS variable
- `MDXArtifact.tsx` - Uses `grid-dynamic-cols` class with `--cols` CSS variable
- `StateTab.tsx` - Uses `tree-indent` class with `--indent` CSS variable
- `JSONArtifact.tsx` - Uses `getIndentClass()` for tree indentation
- `AICacheMetricsDashboard.tsx` - Progress bars use CSS variables
- Multiple progress bar components across the codebase

### Semantic Sizing Tokens Added

```typescript
// tailwind.config.ts
maxHeight: { modal: '90vh', panel: '80vh', drawer: '70vh' }
minHeight: { touch: '44px', 'input-rich': '100px' }
width: { 'dialog-sm': '300px', 'dialog-md': '500px', 'dialog-lg': '600px' }
maxWidth: { message: '70%' }
```

### Legitimate Exceptions (4 remaining)

Files with intentional inline styles not migrated:
1. `MDXArtifact.tsx` - Dynamic component sizing
2. `SandpackExecutor.tsx` - Template literal styling
3. `AIErrorBoundary.tsx` - Error resilience styling
4. Tree components with non-standard offsets (e.g., StateTab uses +8px base offset)

### Documentation Updated

- `STYLE.md` - Added "Dynamic Styling Patterns" section
- Progress bar pattern with CSS custom properties
- Tree indentation pattern with `getIndentClass()`
- Semantic sizing tokens reference

---

## [2026-01-15] Complete Design System Token Implementation & Contract Testing

### Root Cause Analysis: White Screen Bug

The Studio frontend was showing a white/unstyled UI instead of dark theme because:
- `tailwind.config.ts` referenced CSS variables like `var(--primary-9)`
- `index.css` never defined these CSS variables
- CSS silently falls back when variables are undefined
- No tests validated this contract

### Complete CSS Variable Implementation

Added **65+ CSS variables** to `src/index.css`:

| Category | Variables Added | Examples |
|----------|-----------------|----------|
| **Colors** | 108 (9 palettes × 12 steps) | `--violet-1` to `--violet-12`, etc. |
| **Semantic Colors** | 96 (8 × 12 steps) | `--primary-1` to `--primary-12`, etc. |
| **Typography** | 23 | `--font-size-*`, `--font-weight-*`, `--line-height-*`, `--letter-spacing-*` |
| **Spacing** | 21 | `--spacing-0` to `--spacing-24` |
| **Shadows** | 10 | `--shadow-sm` to `--shadow-modal` |
| **Border Radius** | 9 | `--radius-none` to `--radius-full` |
| **Animation** | 9 | `--duration-*`, `--ease-*` |
| **Z-Index** | 9 | `--z-base` to `--z-toast` |

### Tailwind Config Updates

Updated `tailwind.config.ts` to use CSS variables:
- `fontSize`, `fontWeight`, `lineHeight`, `letterSpacing`
- `spacing` (full 22-value scale)
- `boxShadow` (11 values including semantic aliases)
- `borderRadius` (9 values including `none`, `3xl`, `full`)
- `transitionDuration` (5 values: instant, fast, normal, slow, slower)
- `transitionTimingFunction` (4 easing functions)
- `zIndex` (semantic values: tooltip, dropdown, modal, etc.)

### Contract Testing (Prevents Future Regression)

New test file: `src/design-system/design-system-contract.test.ts`
- **15 test cases** validating CSS/Tailwind contract
- Validates all CSS variables referenced in Tailwind exist in CSS
- Validates all design tokens have CSS variable definitions
- Validates dark mode has proper color overrides
- Validates value consistency (4px spacing base, Radix 1-12 scale)

Run: `npm run test:design-system-contract`

### Pre-commit Hook

New hook: `frontend-design-system-contract`
- Runs on pre-push when `tailwind.config.ts`, `index.css`, or `design-system/*.ts` changes
- Prevents CSS variable drift from reaching production
- ~20s execution time

### Why Existing Tests Didn't Catch This

1. **CSS variables don't fail at build time** - undefined vars silently fall back
2. **Tailwind compilation doesn't validate CSS vars** - just generates classes
3. **TypeScript can't type-check CSS** - no connection between TS tokens and CSS
4. **Unit tests mock styles** - JSDOM doesn't compute CSS
5. **E2E tests check behavior, not styles** - Playwright verified clicks, not colors
6. **No contract tests existed** - nothing validated tokens.ts ↔ CSS sync

---

## [2025-01-14] Comprehensive Pattern Extensions

### New Categories Added

#### Opacity Token Enforcement
- Added `OPACITY_PATTERNS` to audit-patterns.ts
- Detects `opacity-[0.5]` and color opacity modifiers `/[0.5]`
- Auto-fix maps decimals to token percentages (0.5 → 50)
- Added to ViolationCategory type

#### Line Height & Letter Spacing Audit
- Added tests for `TYPOGRAPHY_PATTERNS.arbitraryLineHeight`
- Added tests for `TYPOGRAPHY_PATTERNS.arbitraryLetterSpacing`
- Detects `leading-[24px]` and `tracking-[0.5px]`

#### Border Radius Auto-fix
- Added `BORDER_RADIUS_REPLACEMENTS` to fix script
- Maps px/rem to tokens: `rounded-[8px]` → `rounded-lg`
- Supports directional variants (rounded-t, rounded-tl, etc.)

#### Shadow Auto-fix
- Added `SHADOW_REPLACEMENTS` to fix script
- Maps common shadow patterns to tokens (soft, elevated, modal)

### Test Coverage
- 82 audit pattern tests (up from 74)
- 8 new opacity pattern tests
- 4 new line-height tests
- 4 new letter-spacing tests

### Fix Script Categories (8 total)
1. Color (legacy neutrals)
2. Z-index (non-token values)
3. Spacing (arbitrary px/rem)
4. Animation (arbitrary durations)
5. Typography (arbitrary font sizes)
6. Border Radius (arbitrary px/rem)
7. Shadow (common patterns)
8. Opacity (decimals to tokens)

---

## [2025-01-14] Shadow Token Validation & Typography Auto-fix

### Enhancements

#### Shadow Token Validation
- Added comprehensive shadow pattern tests (7 new tests)
- Enhanced `getSuggestion()` with context-aware shadow recommendations:
  - Inset shadows → `shadow-inner`
  - Subtle shadows (0.1 opacity, 2px) → `shadow-soft` or `shadow-sm`
  - Elevated shadows (12px, 0.15) → `shadow-elevated` or `shadow-lg`
  - Modal shadows (48px, 0.25) → `shadow-modal` or `shadow-2xl`
- Documents custom tokens: `shadow-soft`, `shadow-elevated`, `shadow-modal`

#### Typography Auto-fix
- Added typography fix category to `fix-design-system-violations.py`
- Maps arbitrary font sizes to Tailwind tokens:
  - `text-[12px]` → `text-xs`
  - `text-[14px]` → `text-sm`
  - `text-[16px]` → `text-base`
  - `text-[18px]` → `text-lg`
  - `text-[20px]` → `text-xl`
  - `text-[24px]` → `text-2xl`
  - And more (px and rem supported)

### Test Coverage
- 74 audit pattern tests (up from 62)
- 5 new shadow suggestion tests
- Shadow validation tests for multiple formats (rgba, hex, inset, multiple)

---

## [2025-01-14] Comprehensive Design System Audit

### Summary

Conducted a full design system audit with automated tooling. Fixed 139 violations across 4 categories.

### Violations Fixed

| Category | Count | Description |
|----------|-------|-------------|
| Color | 35 | Legacy neutral-XXX (50-950) → Radix 1-12 scale |
| Z-Index | 20 | Non-token values → token values (z-0, z-10, z-50, z-55, z-60, z-65, z-70, z-75) |
| Sizing | 80 | Arbitrary values documented as legitimate patterns |
| Spacing | 4 | Arbitrary spacing → design tokens |

### Tooling Added

#### 1. Design System Audit Script (`scripts/audit-design-system.ts`)

Comprehensive audit tool with ripgrep-based scanning:

```bash
npm run audit:design-system           # Full audit
npm run audit:design-system -- --json # Machine-readable output
npm run audit:design-system -- --strict # Exit code 1 on violations
```

Categories audited:
- Sizing consistency (arbitrary h-[X], w-[X])
- Color compliance (raw Tailwind, legacy neutrals)
- Spacing violations (arbitrary m-[X], p-[X])
- Typography deviations (arbitrary text-[X])
- Border/shadow/z-index (non-token values)
- Animation consistency (arbitrary durations)

#### 2. Auto-Fix Script (`scripts/fix-design-system-violations.py`)

Automated fixer for common violations:

```bash
python scripts/fix-design-system-violations.py           # Fix all
python scripts/fix-design-system-violations.py --dry-run # Preview
python scripts/fix-design-system-violations.py --category=color
python scripts/fix-design-system-violations.py --category=zindex
python scripts/fix-design-system-violations.py --category=spacing
python scripts/fix-design-system-violations.py --category=animation
```

#### 3. Audit Pattern Library (`scripts/lib/audit-patterns.ts`)

Centralized regex patterns for all design system checks:

- `SIZING_PATTERNS` - Height, width, non-standard sizes
- `COLOR_PATTERNS` - Raw Tailwind, legacy neutrals
- `SPACING_PATTERNS` - Arbitrary spacing, gap values
- `TYPOGRAPHY_PATTERNS` - Font sizes, font families
- `BORDER_PATTERNS` - Border radius
- `SHADOW_PATTERNS` - Custom shadows
- `ZINDEX_PATTERNS` - Arbitrary and non-token z-index
- `ANIMATION_PATTERNS` - Durations, inline transitions

Helper functions:
- `categorizeViolation()` - Categorize a class name
- `getSuggestion()` - Get migration suggestion
- `isLegitimateSizing()` - Check if sizing is valid exception
- `isLegitimateSpacing()` - Check if spacing is valid exception

#### 4. Storybook Token Validation (`src/stories/DesignTokenValidation.stories.tsx`)

Interactive Storybook documentation with 5 stories:

- **Dashboard** - Overview of all design token categories
- **ZIndex** - Visual z-index layer demonstration
- **Animation** - Interactive duration preview
- **Sizing** - Legitimate sizing patterns reference
- **AuditCommands** - Quick reference for audit commands

#### 5. Pre-commit Hook Integration

Added design system check to pre-commit hooks:

```yaml
# .pre-commit-config.yaml
- id: check-design-system-violations
  name: Check design system violations
  entry: npm run audit:design-system -- --strict
  language: system
  types: [tsx, ts, css]
```

#### 6. Test Coverage (62 tests)

Added comprehensive tests for audit patterns:

- `tests/scripts/audit-design-system.test.ts`
  - Sizing pattern tests
  - Color pattern tests
  - Spacing pattern tests
  - Typography pattern tests
  - Border pattern tests
  - Shadow pattern tests
  - Z-index pattern tests
  - Animation pattern tests
  - `categorizeViolation()` tests
  - `getSuggestion()` tests
  - `isLegitimateSizing()` tests (15 categories)
  - `isLegitimateSpacing()` tests

### Legitimate Patterns Established

Documented and coded exceptions for valid use cases:

| Category | Pattern | Justification |
|----------|---------|---------------|
| Viewport-relative | `max-h-[90vh]`, `w-[80vw]` | Responsive layouts |
| Percentage-based | `max-w-[70%]` | Fluid containers |
| Calc-based | `h-[calc(100vh-48px)]` | Header/footer offsets |
| WCAG touch targets | `min-h-[44px]`, `min-w-[44px]` | Accessibility compliance |
| Workflow nodes | `min-w-[180px]` | Standard node width |
| Table columns | `min-w-[60px]`, `max-w-[300px]` | Data grid alignment |
| Truncation | `max-w-[120px]` | Text overflow limits |
| Input constraints | `min-h-[40px]`, `max-h-[200px]` | Textarea bounds |
| Container heights | `h-[300px]` - `h-[600px]` | Fixed viewport sections |
| Dropdown widths | `min-w-[120px]`, `min-w-[150px]` | Menu consistency |
| Badge widths | `min-w-[20px]`, `min-w-[1.5rem]` | Pill badges |
| Large containers | `min-w-[500px]`, `min-w-[700px]` | Dialogs, panels |

### Documentation Updates

- **STYLE.md**: Added IDE Integration section with VS Code, JetBrains, Neovim configs
- **STYLE.md**: Updated Related Documentation with new tool references
- **DESIGN_SYSTEM_EXCEPTIONS.md**: Referenced for inline ESLint exceptions

---

## [2025-01-10] Radix Color System Adoption

### Migration

Migrated from Tailwind 50-950 neutral scale to Radix 1-12 semantic scale:

| Old (Tailwind) | New (Radix) | Semantic Purpose |
|----------------|-------------|------------------|
| neutral-50 | neutral-1 | App background |
| neutral-100 | neutral-2 | Subtle background |
| neutral-200 | neutral-3 | UI element background |
| neutral-300 | neutral-5 | Hovered UI element |
| neutral-400 | neutral-9 | Solid backgrounds |
| neutral-500 | neutral-10 | Hovered solid |
| neutral-600 | neutral-11 | Low-contrast text |
| neutral-700 | neutral-11 | Secondary text |
| neutral-800 | neutral-12 | High-contrast text |
| neutral-900 | neutral-12 | Primary text |
| neutral-950 | neutral-12 | Maximum contrast |

### Tooling

- Created `scripts/migrate-legacy-neutrals.py`
- Added ESLint rules to block legacy patterns
- Updated Tailwind config with Radix color definitions

---

## [2025-01-07] Z-Index Token System

### Token Scale

Established centralized z-index token system:

| Token | Value | Use Case |
|-------|-------|----------|
| z-0 | 0 | Base layer |
| z-10 | 10 | Elevated cards |
| z-50 | 50 | Dropdowns, tooltips |
| z-55 | 55 | Floating panels |
| z-60 | 60 | DevTools, sidebars |
| z-65 | 65 | Command palette |
| z-70 | 70 | Modals, dialogs |
| z-75 | 75 | Global overlays, toasts |

### Migration

Replaced arbitrary z-index values:
- `z-20` → `z-10`
- `z-30` → `z-50`
- `z-40` → `z-50`
- `z-100` → `z-75`
- `z-999` → `z-75`
- `z-1000` → `z-75`

---

## [2025-01-05] Animation Token System

### Duration Tokens

Standardized animation durations:

| Token | Duration | Use Case |
|-------|----------|----------|
| duration-75 | 75ms | Micro-interactions |
| duration-100 | 100ms | Quick feedback |
| duration-150 | 150ms | Standard transitions |
| duration-200 | 200ms | Default duration |
| duration-300 | 300ms | Content transitions |
| duration-500 | 500ms | Larger animations |
| duration-700 | 700ms | Page transitions |
| duration-1000 | 1000ms | Slow reveals |

### Easing Tokens

Standard easing functions:
- `ease-in` - Acceleration
- `ease-out` - Deceleration (recommended for UI)
- `ease-in-out` - Smooth start/end
- `ease-linear` - Constant speed

---

## Future Roadmap

### Planned Improvements

1. **Shadow token validation** - Add shadow-[X] detection
2. **Typography audit** - Enforce font-size tokens
3. **Border radius audit** - Catch rounded-[X] violations
4. **Accessibility contrast checks** - WCAG AA/AAA validation
5. **Bundle impact tracking** - Monitor design system bundle size

### Maintenance

- Run `npm run audit:design-system` before each release
- Review legitimate patterns quarterly
- Update DESIGN_SYSTEM_EXCEPTIONS.md when adding new exceptions
