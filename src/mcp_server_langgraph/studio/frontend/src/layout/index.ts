/**
 * Layout Module - Public API
 *
 * This barrel exports the public interface of the layout module.
 * Internal components (ActivityBar, SessionNav, TopBar, StatusBar, etc.)
 * are implementation details of StudioShellLayout and should be imported
 * directly from their source files when needed within the layout module.
 *
 * External consumers should only use StudioShellLayout.
 *
 * ## Barrel Export Patterns (ADR-0091 Appendix)
 *
 * This codebase uses three valid barrel export patterns:
 *
 * 1. **RTK Query API Exports** (src/api/index.ts)
 *    - Auto-generated hooks from RTK Query endpoints
 *    - Many exports are expected (one per endpoint)
 *    - Not all hooks are used in every file, but must be exported
 *
 * 2. **Code-Splitting Exports** (src/components/Admin/LazyComponents.tsx)
 *    - Components exported for React.lazy() dynamic import
 *    - Each export enables chunk splitting for performance
 *    - Usage: `const Component = lazy(() => import('./LazyComponents').then(m => ({ default: m.Component })))`
 *
 * 3. **Library-Style Exports** (src/types/hitl.ts, this file)
 *    - Types and utilities forming a coherent public API
 *    - Consumers import the specific exports they need
 *    - Internal types are NOT exported (file-local)
 *
 * ## This Barrel Pattern
 *
 * This layout barrel follows the library-style pattern:
 * - Primary export: StudioShellLayout (main component)
 * - Secondary exports: Navigation constants (for tests and store integration)
 * - Internal components: NOT exported (implementation details)
 */

// =============================================================================
// Main Shell Layout (Primary Export)
// =============================================================================

export { StudioShellLayout } from "./StudioShellLayout";

// =============================================================================
// Navigation Constants (for tests and store)
// =============================================================================

// KNOWN_NAV_IDS from pure constants file (no React dependencies)
export { KNOWN_NAV_IDS, NAV_ITEM_IDS, BOTTOM_ITEM_IDS } from "./navConstants";

// NAV_ITEMS and BOTTOM_ITEMS with React icons from ActivityBar
export { NAV_ITEMS, BOTTOM_ITEMS, type NavItem } from "./ActivityBar";
