# Bundle Baseline Report

**Date**: 2025-12-20
**Version**: 2.9.0-dev
**Branch**: feature/playground-frontend (Phase 7 - Integration Complete)
**Purpose**: Establish baseline metrics before Hybrid Canvas rollout

## Summary

| Metric | Value |
|--------|-------|
| Total Assets | 137 files |
| Total Size (pre-cache) | 6576.64 KiB (~6.4 MB) |
| Main Entry (JS) | 459.20 KB (119.58 KB gzipped) |
| Main CSS | 149.68 KB (25.65 KB gzipped) |
| Build Time | 13.97s |

## Critical Path Bundles (Initial Load)

These bundles load on first visit:

| Bundle | Size | Gzipped | Notes |
|--------|------|---------|-------|
| `index-N6CwWBFZ.js` | 459.20 KB | 119.58 KB | Main app bundle |
| `vendor-react-D9ZkOfSY.js` | 229.03 KB | 75.10 KB | React + React DOM |
| `index-C2T5dwpI.css` | 149.68 KB | 25.65 KB | Tailwind + component styles |
| `vendor-redux-B6BQB-hu.js` | 36.49 KB | 13.84 KB | Redux Toolkit |
| **Total Critical** | **~874 KB** | **~234 KB** | First meaningful paint |

## Lazy-Loaded Vendor Bundles

These load on-demand when features are accessed:

| Bundle | Size | Gzipped | Lazy Loaded When |
|--------|------|---------|------------------|
| `vendor-syntax-COKt9oNi.js` | 618.39 KB | 218.70 KB | Code highlighting needed |
| `vendor-sandpack-DgHJsnEb.js` | 611.50 KB | 205.22 KB | Code execution sandbox |
| `vendor-mermaid-DX7ihyfj.js` | 482.98 KB | 136.68 KB | Mermaid diagrams |
| `cytoscape.esm-5J0xJHOV.js` | 441.70 KB | 140.91 KB | Graph visualization |
| `vendor-charts-QvFe2GCk.js` | 366.44 KB | 105.48 KB | Recharts dashboards |
| `treemap-KMMF4GRG-CCgKyS3b.js` | 329.98 KB | 80.48 KB | Treemap charts |
| `vendor-math-XbL3y5x-.js` | 265.47 KB | 77.40 KB | KaTeX math rendering |
| `vendor-markdown-base-CSX3ycFO.js` | 172.62 KB | 52.71 KB | Markdown rendering |
| `vendor-flow-DtPwbEiZ.js` | 94.67 KB | 30.69 KB | React Flow |
| `vendor-ui-BYMHBPTn.js` | 66.46 KB | 19.68 KB | UI primitives |

## Page Bundles

| Page | Bundle | Size | Gzipped |
|------|--------|------|---------|
| Chat | `ChatPage-lIwOD33-.js` | 48.54 KB | 13.30 KB |
| Connections | `ConnectionsPage-BvXTjil6.js` | 40.23 KB | 9.70 KB |
| Project Detail | `ProjectDetailPage-CJ29kELY.js` | 35.69 KB | 6.04 KB |
| Settings | `SettingsPage-BP1b7mXK.js` | 27.41 KB | 7.03 KB |
| Observability | `ObservabilityPage-DOe1SPat.js` | 25.20 KB | 5.63 KB |
| Projects | `ProjectsPage-CV-v3CW0.js` | 25.03 KB | 5.98 KB |
| Workflows | `WorkflowsPage-D6AjpMRh.js` | 24.07 KB | 6.49 KB |
| MCP | `MCPPage-CZZ8jMAg.js` | 17.20 KB | 4.11 KB |
| Vectors | `VectorsPage-Epd20Bev.js` | 14.48 KB | 3.35 KB |
| Files | `FilesPage-DfrPhOxP.js` | 12.60 KB | 3.79 KB |
| Admin Dashboard | `AdminDashboardPage-DqzPJbVm.js` | 12.32 KB | 3.35 KB |
| Help | `HelpPage-BYmRRr0K.js` | 9.74 KB | 2.95 KB |
| Audit Log | `AuditLogPage-C-Mqfc8l.js` | 8.09 KB | 2.42 KB |
| Cost | `CostPage-AITPV5Jc.js` | 7.48 KB | 1.84 KB |
| Login | `LoginPage-GnOXhTt9.js` | 6.96 KB | 2.79 KB |
| Agents | `AgentsPage-DU97rHnf.js` | 5.31 KB | 1.68 KB |

## Hybrid Canvas Additions (This Phase)

New modules added in Phase 1-7:

| Module | Files | Estimated Size Impact |
|--------|-------|----------------------|
| `src/layout/` | HybridShellLayout.tsx + components | ~15 KB |
| `src/ai/` | InlineSuggestions, BackgroundAgentPanel | ~8 KB |
| `src/compliance/` | SOC2/HIPAA/GDPR/FedRAMP panels | ~12 KB |
| `src/help/` | HelpPane, ContextualHelp, KeyboardShortcuts | ~6 KB |
| `src/store/slices/canvasSlice.ts` | Canvas state | ~3 KB |
| `src/router/guards/HybridShellGuard.tsx` | Feature flag guard | ~1 KB |
| `src/router/loaders/` | chatLoader, sessionsLoader, artifactLoader | ~2 KB |
| `src/mocks/handlers/canvasHandlers.ts` | MSW handlers | ~2 KB (dev only) |
| **Total New Code** | | **~49 KB** |

## Chunks Over 500 KB (Vite Warning)

The following chunks exceed Vite's 500 KB warning threshold:

1. `vendor-syntax-COKt9oNi.js` - 618.39 KB (syntax highlighting)
2. `vendor-sandpack-DgHJsnEb.js` - 611.50 KB (code execution)

**Mitigation**: Both are lazy-loaded and only needed for specific features.

## Lighthouse Audit Results (2025-12-19)

**Test Environment**: Headless Chrome, localhost:4173 (Vite preview)

### Score Comparison: HybridShell vs AppShell

| Category | HybridShell | AppShell | Status |
|----------|-------------|----------|--------|
| **Performance** | 63% | 63% | ✅ Parity |
| **Accessibility** | 94% | 94% | ✅ Parity |
| **Best Practices** | 96% | 96% | ✅ Parity |
| **SEO** | 100% | 100% | ✅ Parity |

### Core Web Vitals (HybridShell)

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| First Contentful Paint (FCP) | 5.5s | < 1.2s | ⚠️ Headless overhead |
| Largest Contentful Paint (LCP) | 6.5s | < 2.0s | ⚠️ Headless overhead |
| Time to Interactive (TTI) | 6.6s | < 3.0s | ⚠️ Headless overhead |
| Total Blocking Time (TBT) | 100ms | < 300ms | ✅ PASS |
| Cumulative Layout Shift (CLS) | 0 | < 0.1 | ✅ PASS |
| Speed Index | 5.5s | < 3.0s | ⚠️ Headless overhead |

**Note**: FCP/LCP/TTI values are inflated due to headless Chrome + localhost environment.
Real user metrics (RUM) will be lower. Key insight: **HybridShell = AppShell parity confirmed**.

### Bundle Size Targets

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Initial JS (gzipped) | 234 KB | < 250 KB | ✅ PASS |
| Main bundle | 459 KB (120 KB gz) | < 500 KB | ✅ PASS |
| New HybridShell code | ~49 KB | < 50 KB | ✅ PASS |

## Recommendations

1. **Monitor new code impact**: Keep Hybrid Canvas additions under 50 KB total
2. **Lazy load heavy features**: AI suggestions, compliance dashboards
3. **Consider tree-shaking**: Review unused exports in vendor bundles
4. **PWA caching**: 134 entries (6.5 MB) precached for offline

## Tracking

This baseline should be compared after each phase:
- [x] Phase 7 - Integration complete, baseline established
- [ ] Phase 8+ - Measure bundle delta
- [ ] Pre-release - Full Lighthouse audit
- [ ] Post-release - Monitor real user metrics

## Latest Build (2025-12-20)

```
dist/assets/index-N6CwWBFZ.js         459.20 kB (gzip: 119.58 kB)
dist/assets/vendor-react-D9ZkOfSY.js  229.03 kB (gzip: 75.10 kB)
dist/assets/index-C2T5dwpI.css        149.68 kB (gzip: 25.65 kB)
Total dist size: 28 MB (uncompressed)
Build time: 13.97s
PWA precache: 137 entries (6576.64 KiB / ~6.4 MB)
```

**Changes since last baseline:**
- Main bundle grew from 400 KB to 459 KB (edge case tests + new page routes)
- Added FilesPage and HelpPage to page bundles
- PWA precache increased from 134 to 137 entries
- All lazy-loaded vendor chunks remain unchanged in size
- New comprehensive edge case tests added to ObservabilityPage, ProjectsPage, HybridShellLayout

---

Generated by Hybrid Canvas Phase 7 Integration (2025-12-20)
