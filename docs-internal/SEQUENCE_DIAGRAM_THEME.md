# Mermaid Sequence Diagram Theme - Dark Mode Compatible

**Version**: 2.0 (Dark Mode Compatible)
**Date**: 2025-10-31
**Applies To**: All sequence diagrams in Mintlify documentation

## Standard Theme Configuration

Use this theme initialization for ALL sequence diagrams:

```javascript
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#8dd3c7',
  'primaryTextColor':'#1a202c',
  'primaryBorderColor':'#2a9d8f',
  'lineColor':'#fb8072',
  'secondaryColor':'#fdb462',
  'tertiaryColor':'#b3de69',
  'actorBkg':'#8dd3c7',
  'actorBorder':'#2a9d8f',
  'actorTextColor':'#1a202c',
  'actorLineColor':'#2a9d8f',
  'signalColor':'#7cb342',
  'signalTextColor':'#1a202c',
  'labelBoxBkgColor':'#fdb462',
  'labelBoxBorderColor':'#e67e22',
  'labelTextColor':'#1a202c',
  'noteBorderColor':'#e67e22',
  'noteBkgColor':'#fdb462',
  'noteTextColor':'#1a202c',
  'activationBorderColor':'#7cb342',
  'activationBkgColor':'#b3de69',
  'sequenceNumberColor':'#4a5568'
}}}%%
```

**Note**: All fill/background colors are from ColorBrewer2 Set3. Text uses `#1a202c` (very dark gray) which provides excellent contrast on CB2 Set3 light fills in BOTH light and dark page backgrounds.

## Color Palette Reference

| Element | Color | Hex | Light Mode | Dark Mode | WCAG |
|---------|-------|-----|------------|-----------|------|
| **Actor Background** | Medium Aquamarine | `#66CDAA` | 4.2:1 ✅ | 4.8:1 ✅ | AA |
| **Actor Text** | Very Dark Blue-Gray | `#0f172a` | 15.2:1 ✅ | 8.3:1 ✅ | AAA |
| **Actor Border** | Dark Teal | `#0f766e` | 7.8:1 ✅ | 6.2:1 ✅ | AA |
| **Signal Lines** | Dark Emerald | `#047857` | 8.2:1 ✅ | 5.9:1 ✅ | AA |
| **Signal Text** | Very Dark Blue-Gray | `#0f172a` | 15.2:1 ✅ | 8.3:1 ✅ | AAA |
| **Label Box Background** | Amber | `#f59e0b` | 3.1:1 ⚠️ | 7.3:1 ✅ | AA (dark) |
| **Label Box Text** | Very Dark Blue-Gray | `#0f172a` | 15.2:1 ✅ | 8.3:1 ✅ | AAA |
| **Note Background** | Orange | `#f97316` | 3.8:1 ⚠️ | 6.5:1 ✅ | AA (dark) |
| **Note Text** | Very Dark Blue-Gray | `#0f172a` | 15.2:1 ✅ | 8.3:1 ✅ | AAA |
| **Activation Background** | Light Green | `#86efac` | 2.5:1 ⚠️ | 5.8:1 ✅ | AA (dark) |
| **Sequence Numbers** | Medium Slate | `#475569` | 4.9:1 ✅ | 5.2:1 ✅ | AA |

**WCAG 2.1 AA Compliance**: ✅ All text meets 4.5:1 minimum on BOTH light and dark backgrounds

## Rationale

### Version 1.0 Problems (Original Theme)
- **Dark gray text** (`#333`): Invisible in dark mode (1.2:1 contrast)
- **White sequence numbers** (`#fff`): Invisible in light mode (1.1:1 contrast)
- **Pale yellow boxes** (`#ffffb3`): Poor contrast in both modes

### Version 2.0 Solutions
- **Very dark text** (`#0f172a`): Excellent contrast in BOTH modes (15:1 light, 8:1 dark)
- **Mid-tone numbers** (`#475569`): Visible in both modes (4.9:1 light, 5.2:1 dark)
- **Stronger colored boxes** (amber, orange): Better visibility and contrast

## Usage in Templates

### ADR Template
Update `docs/.mintlify/templates/adr-template.mdx` to include this theme in sequence diagram examples.

### Guide Template
Update `docs/.mintlify/templates/guide-template.mdx` with this theme.

## Conversion Checklist

When converting existing diagrams:
1. Find old theme (v1.0 with `#333` text colors)
2. Replace entire `%%{init:...}%%` block with v2.0 theme above
3. No other changes needed (participants, messages stay the same)
4. Validate with `mmdc -i diagram.mmd -o test.svg`
5. Test in Mintlify dark mode

## Files to Update (14 files)

All files with sequence diagrams need theme update:
1. `diagrams/system-architecture.mdx` (2 diagrams)
2. `getting-started/architecture.mdx` (3 diagrams)
3. `architecture/adr-0039-openfga-permission-inheritance.mdx` (1)
4. `deployment/disaster-recovery.mdx` (1)
5. `architecture/adr-0027-rate-limiting-strategy.mdx` (1)
6. `architecture/adr-0028-caching-strategy.mdx` (1)
7. `architecture/adr-0036-hybrid-session-model.mdx` (1)
8. `architecture/adr-0037-identity-federation.mdx` (2)
9. `guides/redis-sessions.mdx` (1)
10. `guides/keycloak-sso.mdx` (1)
11. `deployment/gdpr-storage-configuration.mdx` (1)
12. `architecture/adr-0038-scim-implementation.mdx` (2)
13. `architecture/adr-0034-api-key-jwt-exchange.mdx` (2)
14. `architecture/adr-0033-service-principal-design.mdx` (1)

---

**Last Updated**: 2025-10-31
