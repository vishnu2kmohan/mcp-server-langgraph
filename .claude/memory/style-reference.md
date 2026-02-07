---
purpose: Quick reference to STYLE.md patterns
priority: medium
category: reference
last-updated: 2026-02-07
---

# Frontend Style Quick Reference

**Full Guide**: `docs-internal/frontend/STYLE.md` (1900 lines)

---

## Quick Patterns

| Pattern | File Location |
|---------|---------------|
| CVA template | STYLE.md Section 2 |
| Button variants | STYLE.md Section 3.1 |
| Radix colors | STYLE.md Section 4.1 |
| Accessibility | STYLE.md Section 5 |
| Animation | STYLE.md Section 6 |
| Responsive | STYLE.md Section 8 |

---

## Radix Color Scale Reference

| Purpose | Radix Class | Tailwind (WRONG) |
|---------|-------------|------------------|
| Background | `bg-neutral-1` | `bg-gray-50` |
| Subtle bg | `bg-neutral-2` | `bg-gray-100` |
| Interactive bg | `bg-neutral-4` | `bg-gray-200` |
| Borders | `border-neutral-7` | `border-gray-300` |
| Solid buttons | `bg-primary-9` | `bg-blue-500` |
| Text | `text-neutral-12` | `text-gray-900` |

---

## Button Variant Quick Reference

| Action Type | Variant | Example |
|-------------|---------|---------|
| Primary action | `primary` | Save, Submit, Confirm |
| Secondary action | `secondary` | Cancel, Close, Back |
| Destructive action | `danger` | Delete, Remove, Clear |
| Minimal/toolbar | `ghost` | Icon buttons |
| Link-style | `link` | Navigation |

---

## Migration Scripts

```bash
# Fix color scale violations
python scripts/design-system.py --fix --category=color

# Fix variant violations
python scripts/design-system.py --fix --category=variants

# Audit all patterns
npm run audit:design-system
```

---

## Common Violations

| Violation | Fix |
|-----------|-----|
| `bg-gray-100` | `bg-neutral-2` |
| `text-gray-900` | `text-neutral-12` |
| `border-gray-300` | `border-neutral-7` |
| `z-50` | `z-dropdown` |
| `outline-none` alone | Add `focus-visible:ring-2` |
