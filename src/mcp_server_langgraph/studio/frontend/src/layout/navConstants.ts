/**
 * Navigation Constants
 *
 * Pure data constants for navigation that can be imported without
 * pulling in React dependencies. This allows the Redux store (personaSlice)
 * to validate nav IDs without creating circular dependencies with React Router.
 *
 * Note: This file MUST NOT import anything from React, React Router, or
 * components that use them. Keep it pure TypeScript data.
 */

// =============================================================================
// Navigation Item Type (for typed nav ID references)
// =============================================================================

/**
 * Navigation item interface (data-only, no React nodes).
 * For the full NavItem with icon, see ActivityBar.tsx.
 */
export interface NavItemData {
  id: string;
  label: string;
  path?: string;
}

// =============================================================================
// Navigation Item IDs
// =============================================================================

/**
 * Main navigation item IDs.
 * Must stay in sync with NAV_ITEMS in ActivityBar.tsx.
 */
export const NAV_ITEM_IDS = [
  "projects",
  "chat",
  "workflows",
  "agents",
  "mcp",
  "vectors",
  "connections",
  "artifacts",
  "observability",
  "cost",
  "admin",
  "skills",
  "audit",
  "compliance",
] as const;

/**
 * Bottom navigation item IDs.
 * Must stay in sync with BOTTOM_ITEMS in ActivityBar.tsx.
 */
export const BOTTOM_ITEM_IDS = ["help", "settings"] as const;

// =============================================================================
// Known Nav IDs Set
// =============================================================================

/**
 * KNOWN_NAV_IDS - Set of all valid navigation item IDs
 *
 * Used by selectSidebarItems (personaSlice) to filter server-provided
 * visible_modules to only include IDs that have corresponding nav items.
 * This prevents invisible entries in the sidebar.
 *
 * Single source of truth - imported by:
 * - personaSlice.ts (to validate server-provided visibleModules)
 * - ActivityBar.tsx (for reference, but keeps its own NAV_ITEMS with icons)
 */
export const KNOWN_NAV_IDS: Set<string> = new Set([
  ...NAV_ITEM_IDS,
  ...BOTTOM_ITEM_IDS,
]);
