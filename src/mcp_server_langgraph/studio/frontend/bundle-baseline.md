# Bundle Baseline Report - Phase 0

**Date:** 2025-12-19
**Build Tool:** Vite 6.x
**Purpose:** Establish baseline before Studio Shell implementation

---

## Summary

| Metric | Value |
|--------|-------|
| **Total dist/ size** | 28 MB (includes source maps) |
| **Total JS (uncompressed)** | ~6.4 MB |
| **Total JS (gzipped)** | ~1.5 MB |
| **Critical path (uncompressed)** | ~842 KB |
| **Critical path (gzipped)** | ~335 KB |
| **PWA precache entries** | 134 files |
| **PWA precache size** | 6,464 KB |

---

## Critical Path Bundles (Always Loaded)

| Bundle | Uncompressed | Gzipped |
|--------|-------------|---------|
| vendor-react | 228.73 KB | 75.01 KB |
| index-Bxgnkw4i (main) | 383.37 KB | 100.66 KB |
| index-BzOnaqGg | 149.68 KB | 25.65 KB |
| vendor-ui | 63.87 KB | 19.01 KB |
| vendor-redux | 36.49 KB | 13.84 KB |
| **Total** | **~862 KB** | **~234 KB** |

---

## Top 10 Largest Chunks

| Chunk | Size | Gzip | Notes |
|-------|------|------|-------|
| vendor-syntax | 618.39 KB | 218.70 KB | Syntax highlighting (Monaco, Prism) |
| vendor-sandpack | 611.50 KB | 205.22 KB | Executable code sandbox |
| vendor-mermaid | 482.98 KB | 136.69 KB | Mermaid diagrams |
| cytoscape.esm | 441.70 KB | 140.91 KB | Graph visualization |
| index-Bxgnkw4i | 383.37 KB | 100.66 KB | Main application entry |
| vendor-charts | 366.44 KB | 105.48 KB | Recharts |
| treemap-KMMF4GRG | 329.98 KB | 80.48 KB | Mermaid treemap |
| vendor-math | 265.47 KB | 77.40 KB | Math rendering (KaTeX) |
| vendor-react | 228.73 KB | 75.01 KB | React core |
| vendor-markdown-base | 172.62 KB | 52.70 KB | Markdown rendering |

---

## Lazy-Loaded Heavy Dependencies

These are already code-split and only loaded when needed:

| Dependency | Load Trigger | Size (gzip) |
|------------|--------------|-------------|
| vendor-syntax | First code artifact | 218.70 KB |
| vendor-sandpack | First executable | 205.22 KB |
| vendor-mermaid | First diagram | 136.69 KB |
| cytoscape | Workflow builder | 140.91 KB |
| vendor-charts | Cost/observability page | 105.48 KB |

---

## Warnings from Build

```
(!) Some chunks are larger than 500 kB after minification:
- vendor-syntax (618 KB)
- vendor-sandpack (611 KB)
- vendor-mermaid (482 KB)
```

**These are expected** - heavy third-party libraries that are already lazy-loaded.

---

## Phase 0 StudioShell Impact

| New Code | Size | Notes |
|----------|------|-------|
| StudioShellLayout.tsx | ~2 KB | Skeleton component |
| types/artifacts.ts extension | ~3 KB | Canvas types |
| layout/index.ts | <1 KB | Module export |

**Estimated impact:** < 5 KB added (negligible)

---

## Targets for Studio Shell Rebuild

Per the plan, focus on:

1. **Not making it worse** - New StudioShell code should be < 50 KB total
2. **Lazy loading heavy deps** - Already implemented
3. **Measuring impact of each new feature** - Track per phase

### Phase 0 Success Criteria

- [x] Baseline documented
- [x] Top chunks identified
- [x] Lazy loading strategy confirmed
- [ ] StudioShellLayout < 10 KB (when fully built)

---

## Comparison Metrics (for future phases)

Use these commands to measure impact:

```bash
# Full build with output
npm run build 2>&1 | tee build-output.txt

# Just JS sizes
find dist -name "*.js" -exec du -b {} \; | awk '{sum+=$1} END {print sum/1024 " KB"}'

# Gzipped sizes for top bundles
gzip -9 -k dist/assets/*.js
du -h dist/assets/*.js.gz | sort -hr | head -10
```

---

**Next Steps:**
1. Monitor bundle size in each PR (CI should report delta)
2. If new chunks > 50 KB, investigate code splitting opportunities
3. Phase 1: Ensure react-resizable-panels is tree-shaken properly
