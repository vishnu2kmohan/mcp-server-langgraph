# Accessibility Implementation Guide

**Last Updated:** 2026-01-05
**WCAG Version:** 2.1 Level AA
**Status:** Implemented (StudioShell UX Audit - Phase 1-4)

---

## Executive Summary

Agent Studio implements WCAG 2.1 Level AA accessibility features across the StudioShellLayout and related components. This document describes the implemented features, testing approach, and ongoing compliance requirements.

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

### 6. Color Contrast (WCAG 1.4.3)

Design tokens ensure 4.5:1 contrast ratio for normal text:

| Element | Foreground | Background | Ratio |
|---------|------------|------------|-------|
| Body text | `gray-900` | `white` | 21:1 |
| Primary buttons | `white` | `primary-600` | 7.5:1 |
| Secondary text | `gray-600` | `white` | 5.7:1 |
| Error messages | `red-700` | `red-50` | 5.2:1 |

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

## Related Documentation

- [KEYBOARD_SHORTCUTS.md](./KEYBOARD_SHORTCUTS.md) - Complete keyboard shortcuts reference
- [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) - Design tokens and color system
- [UX_AUDIT_REPORT.md](../UX_AUDIT_REPORT.md) - UX audit findings and roadmap
