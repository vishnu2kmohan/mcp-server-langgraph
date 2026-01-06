# Agent Studio Keyboard Shortcuts

**Last Updated:** 2026-01-05
**Status:** Production Ready
**Implementation:** `StudioShellLayout.tsx`, `KeyboardShortcutOverlay.tsx`

---

## Overview

Agent Studio provides comprehensive keyboard navigation to support power users and accessibility requirements (WCAG 2.1 AA compliance). Press `Shift+?` or `?` at any time to view the shortcuts overlay.

---

## Global Shortcuts

These shortcuts work from anywhere in the application.

| Shortcut | Windows/Linux | macOS | Action | Description |
|----------|---------------|-------|--------|-------------|
| Command Palette | `Ctrl+K` | `Cmd+K` | Opens AI-powered command palette | Quick access to all commands with AI interpretation |
| Toggle Canvas | `Ctrl+/` | `Cmd+/` | Expand/collapse the right panel | Focus on conversation or show canvas workspace |
| Toggle DevTools | `Ctrl+Shift+I` | `Cmd+Shift+I` | Open/close developer tools | View traces, logs, metrics, and alerts |
| Toggle Focus Mode | `Ctrl+Shift+F` | `Cmd+Shift+F` | Enter/exit distraction-free mode | Minimizes UI chrome for focused work |
| Show Shortcuts | `?` or `Shift+?` | `?` or `Shift+?` | Display shortcuts overlay | Quick reference for all keyboard shortcuts |
| Exit Focus Mode | `Escape` | `Escape` | Exit focus mode | Only active when focus mode is enabled |

---

## Navigation Shortcuts

| Shortcut | Windows/Linux | macOS | Action |
|----------|---------------|-------|--------|
| Insights Panel | `Ctrl+I` | `Cmd+I` | Toggle Cross-Insights panel |

---

## Command Palette Commands

Access via `Ctrl+K` / `Cmd+K`:

| Command | Description |
|---------|-------------|
| `new-chat` | Create a new chat session |
| `toggle-canvas` | Toggle the canvas panel |
| `toggle-sidebar` | Toggle the session navigation sidebar |
| `open-settings` | Navigate to settings page |
| `open-help` | Navigate to help page |
| `open-observability` | Navigate to observability dashboard |
| `open-compliance` | Navigate to compliance page |

---

## Accessibility Features

### Skip to Content Link

A "Skip to main content" link appears when you press `Tab` at the start of page navigation, allowing screen reader users to bypass the 15+ navigation items.

### Focus Trap in Modals

All modal dialogs (Onboarding Wizard, Approval Dialogs, etc.) implement focus trapping to ensure keyboard users can navigate within the modal without escaping to background content.

### ARIA Support

- All interactive elements have proper `aria-label` attributes
- ActivityBar navigation items have `title` attributes for tooltips
- Collapsible groups have `aria-expanded` state indicators

---

## Implementation Details

### KeyboardShortcutOverlay Component

Location: `src/components/Common/KeyboardShortcutOverlay.tsx`

Features:
- Displays all registered shortcuts from `keyboardShortcuts` map
- Groups shortcuts by category (Navigation, Panels, Focus)
- Platform-aware display (shows Cmd on macOS, Ctrl on Windows/Linux)
- Closes on `Escape` or clicking outside

### useFocusTrap Hook

Location: `src/hooks/useFocusTrap.ts`

Usage:
```typescript
import { useFocusTrap } from "@/hooks/useFocusTrap";

function MyModal({ isOpen }: { isOpen: boolean }) {
  const modalRef = useRef<HTMLDivElement>(null);
  useFocusTrap(modalRef, isOpen);

  return (
    <div ref={modalRef} role="dialog" aria-modal="true">
      {/* Modal content */}
    </div>
  );
}
```

---

## Related Documentation

- [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) - Design tokens and component architecture
- [ACCESSIBILITY_IMPLEMENTATION.md](./ACCESSIBILITY_IMPLEMENTATION.md) - WCAG compliance details
- [UX_AUDIT_REPORT.md](../UX_AUDIT_REPORT.md) - UX audit findings and roadmap
