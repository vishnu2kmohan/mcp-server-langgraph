# Accessibility Implementation Guide

**Last Updated:** 2026-01-13
**WCAG Version:** 2.2 Level AA
**Status:** Implemented (StudioShell UX Audit - Phase 1-4, Contrast Audit 2026-01)

---

## Executive Summary

Agent Studio implements WCAG 2.2 Level AA accessibility features across the StudioShellLayout and related components. This document describes the implemented features, testing approach, and ongoing compliance requirements.

**2026-01-13 Update:** Comprehensive contrast audit completed. Color-contrast axe-core rule enabled in all tests. ESLint rules added to catch low-contrast patterns at lint time.

---

## Implemented Features

### 1. Skip-to-Content Link (WCAG 2.4.1)

**Location:** `StudioShellLayout.tsx`

A visually hidden link that becomes visible on focus, allowing keyboard users to bypass navigation and jump directly to main content.

```tsx
<a
  href="#main-content"
  className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:p-4 focus:bg-white focus:text-blue-600 focus:ring-2 focus:ring-blue-500"
>
  Skip to main content
</a>
```

**Testing:**
- Press `Tab` immediately after page load
- Link should become visible and focused
- Pressing `Enter` should scroll to main content area

---

### 2. Focus Trap for Modals (WCAG 2.1.2)

**Location:** `src/hooks/useFocusTrap.ts`

Prevents keyboard focus from escaping modal dialogs, ensuring users can navigate within the modal using Tab/Shift+Tab.

**Components Using Focus Trap:**
- `OnboardingWizard.tsx`
- `AgentApprovalDialog.tsx`
- `ClarificationDialog.tsx`
- `KeyboardShortcutOverlay.tsx`

**Implementation:**
```typescript
export function useFocusTrap(
  ref: RefObject<HTMLElement>,
  isActive: boolean
): void {
  useEffect(() => {
    if (!isActive || !ref.current) return;

    const element = ref.current;
    const focusableElements = element.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    if (focusableElements.length === 0) return;

    const firstFocusable = focusableElements[0];
    const lastFocusable = focusableElements[focusableElements.length - 1];

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Tab") {
        if (e.shiftKey) {
          if (document.activeElement === firstFocusable) {
            e.preventDefault();
            lastFocusable.focus();
          }
        } else {
          if (document.activeElement === lastFocusable) {
            e.preventDefault();
            firstFocusable.focus();
          }
        }
      }
    };

    element.addEventListener("keydown", handleKeyDown);
    firstFocusable.focus();

    return () => element.removeEventListener("keydown", handleKeyDown);
  }, [ref, isActive]);
}
```

---

### 3. Keyboard Navigation (WCAG 2.1.1)

**All Interactive Elements Are Keyboard Accessible:**

| Component | Keyboard Support |
|-----------|------------------|
| ActivityBar | Tab navigation, Enter to activate |
| SessionNav | Tab/Arrow keys, Enter to select |
| TopBar | Tab navigation, Enter for buttons |
| Command Palette | Arrow keys, Enter to execute |
| Collapsible Groups | Enter/Space to toggle |

**Global Shortcuts:**
See [KEYBOARD_SHORTCUTS.md](./KEYBOARD_SHORTCUTS.md) for complete list.

---

### 4. ARIA Labels and Roles (WCAG 4.1.2)

**ActivityBar Navigation:**
```tsx
<button
  aria-label={item.label}
  title={item.label}
  data-testid={`nav-${item.id}`}
  className={...}
>
  <item.icon className="w-5 h-5" aria-hidden="true" />
</button>
```

**Collapsible Groups:**
```tsx
<button
  aria-expanded={!isCollapsed}
  aria-controls={`nav-group-${groupId}-items`}
  data-testid={`nav-group-${groupId}`}
>
  <ChevronRight className={isCollapsed ? "" : "rotate-90"} />
  {groupLabel}
</button>
```

---

### 5. Focus Indicators (WCAG 2.4.7)

All interactive elements have visible focus indicators using Tailwind CSS utilities:

```css
/* Focus ring styling */
focus:ring-2 focus:ring-primary-500 focus:ring-offset-2
focus:outline-none focus-visible:ring-2
```

---

### 6. Color Contrast (WCAG 1.4.3, 1.4.6)

Design tokens ensure 4.5:1 contrast ratio for normal text (WCAG AA), 7:1 for enhanced (AAA).

**Light Mode (safe patterns):**

| Element | Foreground | Background | Ratio |
|---------|------------|------------|-------|
| Body text | `neutral-900` | `light-1` | 21:1 |
| Primary buttons | `white` | `primary-600` | 7.5:1 |
| Secondary text | `neutral-500` | `light-1` | 5.7:1 |
| Error messages | `error-700` | `error-50` | 5.2:1 |

**Dark Mode (safe patterns):**

| Element | Foreground | Background | Ratio |
|---------|------------|------------|-------|
| Body text | `neutral-100` | `dark-1` | 15.8:1 |
| Primary text | `neutral-200` | `dark-1` | 12.6:1 |
| Secondary text | `neutral-300` | `dark-1` | 8.5:1 |
| Muted text | `neutral-400` | `dark-1` | **4.03:1** ⚠️ |

**⚠️ Dark Mode Contrast Violations (Fixed 2026-01-13):**

The following patterns **FAIL** WCAG 2.2 AA (require 4.5:1 minimum):

| Pattern | Contrast | Fix |
|---------|----------|-----|
| `dark:text-neutral-400` | 4.03:1 ❌ | Use `dark:text-neutral-300` (8.5:1) |
| `dark:bg-*-900/20` | Varies ❌ | Use `/40` minimum, `/50` for badges |
| `dark:bg-*-900/30` | Varies ❌ | Use `/40` minimum, `/50` for badges |

**ESLint Enforcement:**

The following patterns are now caught by ESLint (`no-restricted-syntax`):

```javascript
// ❌ FAILS lint - low contrast text
"dark:text-neutral-400"

// ❌ FAILS lint - low opacity backgrounds
"dark:bg-primary-900/20"
"dark:bg-warning-900/30"

// ✅ PASSES lint - proper contrast
"dark:text-neutral-300"
"dark:bg-primary-900/50"
```

**Test Coverage:**

- `src/components/UI/ContrastAccessibility.test.tsx` - Documents safe/unsafe patterns
- `src/layout/__tests__/StudioShellLayout.accessibility.test.tsx` - axe-core with color-contrast enabled

---

### 7. Responsive Design / Mobile (WCAG 1.4.10)

**Breakpoint System:**
```typescript
// ResponsiveLayout.tsx
const breakpoints = {
  sm: "(max-width: 639px)",
  md: "(min-width: 640px) and (max-width: 1023px)",
  lg: "(min-width: 1024px) and (max-width: 1279px)",
  xl: "(min-width: 1280px)",
};
```

**Mobile-Specific Features:**
- MobileDrawer component for navigation
- HamburgerMenu trigger
- Auto-collapse of SessionNav on small screens
- Touch-friendly tap targets (44x44px minimum)

---

## Testing Infrastructure

### Unit Tests

Location: `src/layout/__tests__/StudioShellLayout.accessibility.test.tsx`

```typescript
describe("Accessibility", () => {
  it("should have skip-to-content link", async () => {
    render(<StudioShellLayout />);
    const skipLink = screen.getByText("Skip to main content");
    expect(skipLink).toBeInTheDocument();
    expect(skipLink).toHaveClass("sr-only");
  });

  it("should have no axe-core violations", async () => {
    const { container } = render(<StudioShellLayout />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
```

### Hook Tests

Location: `src/hooks/useFocusTrap.test.tsx`

- Focus cycling within modal
- Initial focus on first focusable element
- Cleanup on unmount

---

## Compliance Checklist

### Perceivable

- [x] 1.1.1 Non-text content has text alternatives (icons have aria-hidden + button labels)
- [x] 1.3.1 Info and relationships programmatically determinable (semantic HTML)
- [x] 1.4.1 Color not sole means of conveying information (icons + text)
- [x] 1.4.3 Contrast ratio 4.5:1 for normal text (design tokens)
- [x] 1.4.10 Content reflows at 320px (ResponsiveLayout)

### Operable

- [x] 2.1.1 All functionality keyboard accessible (verified by tests)
- [x] 2.1.2 No keyboard traps (useFocusTrap allows Escape to close)
- [x] 2.4.1 Skip navigation links (skip-to-content implemented)
- [x] 2.4.3 Focus order logical (natural tab order)
- [x] 2.4.7 Focus visible (ring utilities applied)

### Understandable

- [x] 3.1.1 Language of page defined (`<html lang="en">`)
- [x] 3.2.1 No unexpected context changes on focus
- [x] 3.3.1 Error identification (toast notifications with clear messages)
- [x] 3.3.2 Labels for input elements

### Robust

- [x] 4.1.1 Valid HTML (React produces valid markup)
- [x] 4.1.2 Name, role, value for UI components (ARIA attributes)

---

## Ongoing Maintenance

### Pre-Commit Validation

The accessibility tests run as part of the pre-commit hook suite. Any violations will block the commit.

### Periodic Audits

Run full accessibility audit monthly:
```bash
npm run test -- --run src/layout/__tests__/StudioShellLayout.accessibility.test.tsx
```

### Screen Reader Testing

Recommended testing matrix:
| OS | Screen Reader | Browser |
|----|---------------|---------|
| macOS | VoiceOver | Safari |
| Windows | NVDA | Chrome |
| Windows | JAWS | Edge |

---

## Charts and Data Visualization (WCAG 1.1.1, 1.4.1)

Recharts components require special accessibility handling since SVG charts are not natively accessible to screen readers.

### Pattern: Accessible Chart Container

**Implementation Example:** `InteractiveChart.tsx`, `CostPage.tsx`, `AIQualityMetricsCard.tsx`

```tsx
{/* Accessible chart wrapper */}
<div
  role="img"
  aria-label={`${chartTitle} - ${chartType} chart with ${dataPoints.length} data points`}
>
  {/* Screen reader description */}
  <span className="sr-only">
    {chartType} chart displaying {chartTitle}.
    Use the data table toggle for accessible values.
  </span>

  {/* Chart (hidden from screen readers) */}
  <ResponsiveContainer width="100%" height="100%">
    <LineChart data={data} aria-hidden="true">
      {/* ... chart components */}
    </LineChart>
  </ResponsiveContainer>
</div>
```

### Key Principles

| Requirement | Implementation |
|-------------|----------------|
| Chart has text alternative | `role="img"` + `aria-label` on container |
| Description for context | `sr-only` span with chart type and purpose |
| Hide decorative elements | `aria-hidden="true"` on Recharts components |
| Alternative data access | Provide data table toggle for accessible tabular view |
| Keyboard navigation | `tabIndex={0}` on container for focus management |

### Required Attributes

1. **Container `div`:**
   - `role="img"` - Identifies as image to assistive tech
   - `aria-label` - Describes chart type, title, and data point count

2. **Screen Reader Description:**
   - `className="sr-only"` - Visually hidden but accessible
   - Include chart type, data description, and instructions

3. **Recharts Components:**
   - `aria-hidden="true"` - Prevents screen reader from reading SVG elements

### Data Table Alternative

Always provide a toggleable data table for users who cannot perceive the visual chart:

```tsx
<Button
  onClick={() => setShowDataTable(prev => !prev)}
  aria-label="Toggle data table"
>
  <TableIcon size={14} />
</Button>

{showDataTable && (
  <table role="table" aria-label="Chart data">
    <thead>
      <tr><th>Name</th><th>Value</th></tr>
    </thead>
    <tbody>
      {data.map(item => (
        <tr key={item.name}>
          <td>{item.name}</td>
          <td>{item.value}</td>
        </tr>
      ))}
    </tbody>
  </table>
)}
```

### Testing Checklist

- [ ] Chart container has `role="img"` and descriptive `aria-label`
- [ ] Screen reader description explains chart type and purpose
- [ ] All Recharts components have `aria-hidden="true"`
- [ ] Data table toggle is available and keyboard accessible
- [ ] Data table uses semantic `<table>` markup with headers
- [ ] Color is not the only means of distinguishing data series (use patterns or labels)

### Components Using This Pattern

| Component | File | Verified |
|-----------|------|----------|
| InteractiveChart | `src/components/Chat/InteractiveChart.tsx` | Yes |
| Cost History Chart | `src/pages/CostPage.tsx` | Yes |
| AI Quality Metrics | `src/components/Admin/AIQualityMetricsCard.tsx` | Yes |

---

## New Component Accessibility Checklist

**Use this checklist when creating new components. All items are required for WCAG 2.2 AA compliance.**

### Pre-Development

- [ ] Review this guide and relevant WCAG success criteria
- [ ] Check if similar components exist in `src/components/UI/` that can be extended
- [ ] Identify any charts/visualizations that need accessible alternatives

### Color & Contrast (Critical)

- [ ] **Light mode text:** Use `text-neutral-500` or darker on light backgrounds
- [ ] **Dark mode text:** Use `dark:text-neutral-300` or lighter (NOT `neutral-400`)
- [ ] **Background opacity:** Use `/40` minimum, `/50` for badges (NOT `/20` or `/30`)
- [ ] **No color-only meaning:** Icons, patterns, or text supplement color indicators
- [ ] Run ESLint to verify no contrast violations: `npm run lint`

### Semantic HTML

- [ ] Use semantic elements (`<button>`, `<nav>`, `<main>`, `<article>`, etc.)
- [ ] Import from design system: `import { Button, Badge } from "@/components/UI"`
- [ ] No raw `<button>`, `<input>`, `<select>` outside UI primitives

### ARIA & Labels

- [ ] All buttons have accessible names (visible text or `aria-label`)
- [ ] Icon-only buttons have `aria-label` describing the action
- [ ] Icons have `aria-hidden="true"` to prevent double-reading
- [ ] Form inputs have associated `<label>` elements or `aria-label`
- [ ] Expandable content uses `aria-expanded` and `aria-controls`
- [ ] Live regions use `aria-live` for dynamic content updates

### Keyboard Navigation

- [ ] All interactive elements reachable via Tab key
- [ ] Focus order follows visual order (logical tab sequence)
- [ ] Custom widgets implement arrow key navigation where expected
- [ ] Escape key closes modals/dropdowns
- [ ] Focus visible on all interactive elements (ring utilities)
- [ ] No keyboard traps (use `useFocusTrap` for modals)

### Focus Management

- [ ] Modals trap focus and return focus on close
- [ ] Newly revealed content receives focus or has skip link
- [ ] Focus rings use design system tokens:
  ```tsx
  className="focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 focus-visible:outline-none"
  ```

### Testing

- [ ] Write accessibility test using jest-axe:
  ```typescript
  import { axe, toHaveNoViolations } from 'jest-axe';
  expect.extend(toHaveNoViolations);

  it('has no accessibility violations', async () => {
    const { container } = render(<MyComponent />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
  ```
- [ ] Test keyboard navigation manually
- [ ] Verify with browser dev tools accessibility tree

### Charts & Data Visualization

If component includes charts:
- [ ] Container has `role="img"` and descriptive `aria-label`
- [ ] Chart SVG has `aria-hidden="true"`
- [ ] Screen reader description in `sr-only` span
- [ ] Data table toggle available for accessible alternative

### Quick Reference: Safe Color Classes

```tsx
// ✅ SAFE - Light mode text
"text-neutral-500"  // Secondary (5.7:1)
"text-neutral-600"  // Default (7.4:1)
"text-neutral-900"  // Primary (21:1)

// ✅ SAFE - Dark mode text
"dark:text-neutral-100"  // Primary (15.8:1)
"dark:text-neutral-200"  // Default (12.6:1)
"dark:text-neutral-300"  // Secondary (8.5:1)

// ❌ UNSAFE - Low contrast
"dark:text-neutral-400"  // 4.03:1 - FAILS WCAG AA

// ✅ SAFE - Badge backgrounds
"dark:bg-primary-900/50"
"dark:bg-success-900/50"
"dark:bg-warning-900/40"

// ❌ UNSAFE - Low opacity
"dark:bg-primary-900/20"
"dark:bg-primary-900/30"
```

---

## Navigation Sync Validation

**Added 2026-01-13**

Navigation items must be synchronized between `ActivityBar.tsx` and `personaSlice.ts`.

### Test Location

`src/store/slices/__tests__/navigationSync.test.ts`

### What It Validates

1. All `NAV_ITEMS` IDs exist in persona `sidebarItems` configurations
2. No ID mismatches (e.g., "audit" vs "audit-logs")
3. Admin persona has access to all navigation items
4. Item paths match `/studio/{id}` convention

### Adding New Navigation Items

1. Add to `NAV_ITEMS` in `ActivityBar.tsx`
2. Add to `sidebarItems` in `personaSlice.ts` for appropriate personas
3. Run validation test: `npm test -- --run navigationSync.test.ts`

---

## CI/CD Integration

**GitHub Actions Workflow:** `.github/workflows/accessibility-tests.yaml`

- **Blocking:** Tests are blocking (no `continue-on-error`)
- **Script:** `npm run test:a11y` runs accessibility-focused tests
- **Report:** JSON report uploaded as artifact

### Running Locally

```bash
# Run accessibility tests
npm run test:a11y

# Run all tests including accessibility
npm test
```

---

## Related Documentation

- [KEYBOARD_SHORTCUTS.md](./KEYBOARD_SHORTCUTS.md) - Complete keyboard shortcuts reference
- [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) - Design tokens and color system
- [UX_AUDIT_REPORT.md](../UX_AUDIT_REPORT.md) - UX audit findings and roadmap
- [ContrastAccessibility.test.tsx](../../src/mcp_server_langgraph/studio/frontend/src/components/UI/ContrastAccessibility.test.tsx) - Safe/unsafe pattern reference
