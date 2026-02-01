/**
 * Indent Level Utility
 *
 * Provides design-system compliant indentation classes for tree structures.
 * Replaces inline `style={{ paddingLeft: `${depth * 16}px` }}` patterns.
 *
 * @example
 * // Before:
 * <div style={{ paddingLeft: `${depth * 16}px` }}>
 *
 * // After:
 * <div className={getIndentClass(depth)}>
 *
 * @see docs-internal/frontend/STYLE.md
 */

/**
 * Maps depth level to Tailwind padding-left class.
 *
 * Uses standard Tailwind spacing scale (4px base unit):
 * - pl-0 = 0px
 * - pl-4 = 16px
 * - pl-8 = 32px
 * - pl-12 = 48px
 * - etc.
 *
 * For depths > 10, falls back to arbitrary value to handle deep nesting.
 *
 * @param depth - The nesting depth (0 = root level)
 * @param baseUnit - Base spacing multiplier in Tailwind units (default: 4 = 16px)
 * @returns Tailwind padding-left class string
 */
export function getIndentClass(depth: number, baseUnit: number = 4): string {
  // Handle invalid inputs
  if (depth < 0 || !Number.isFinite(depth)) {
    return "pl-0";
  }

  // Standard Tailwind spacing values (in 4px units)
  const standardUnits = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 20, 24];

  const targetUnits = depth * baseUnit;

  // Check if we can use a standard Tailwind class
  if (standardUnits.includes(targetUnits)) {
    return `pl-${targetUnits}`;
  }

  // For non-standard values, use arbitrary value syntax
  const pxValue = targetUnits * 4; // Convert to pixels
  return `pl-[${pxValue}px]`;
}

/**
 * Maps depth level to margin-left class (alternative to padding).
 *
 * @param depth - The nesting depth (0 = root level)
 * @param baseUnit - Base spacing multiplier in Tailwind units (default: 4 = 16px)
 * @returns Tailwind margin-left class string
 */
export function getIndentMarginClass(
  depth: number,
  baseUnit: number = 4,
): string {
  if (depth < 0 || !Number.isFinite(depth)) {
    return "ml-0";
  }

  const standardUnits = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 20, 24];
  const targetUnits = depth * baseUnit;

  if (standardUnits.includes(targetUnits)) {
    return `ml-${targetUnits}`;
  }

  const pxValue = targetUnits * 4;
  return `ml-[${pxValue}px]`;
}

/**
 * Returns inline style for indent when arbitrary values exceed Tailwind limits.
 *
 * Use this only when depth can be very large (>10 levels) and you need
 * exact pixel control.
 *
 * @param depth - The nesting depth
 * @param pxPerLevel - Pixels per indent level (default: 16px)
 * @returns React CSSProperties object with paddingLeft
 */
export function getIndentStyle(
  depth: number,
  pxPerLevel: number = 16,
): React.CSSProperties {
  return {
    paddingLeft: `${Math.max(0, depth) * pxPerLevel}px`,
  };
}

/**
 * Pre-computed indent class map for common depths (0-6).
 * Use for performance-critical rendering with many tree nodes.
 * For depths > 6, use getIndentClass() which handles arbitrary values.
 *
 * Note: Only standard Tailwind tokens are used here to satisfy ESLint.
 * Deep nesting (7+) falls back to getIndentClass() with arbitrary values.
 */
export const INDENT_CLASSES: Record<number, string> = {
  0: "pl-0",
  1: "pl-4",
  2: "pl-8",
  3: "pl-12",
  4: "pl-16",
  5: "pl-20",
  6: "pl-24",
};

/**
 * Fast lookup for indent class using pre-computed map.
 *
 * @param depth - The nesting depth (0-10)
 * @returns Tailwind padding-left class string
 */
export function getIndentClassFast(depth: number): string {
  return (
    INDENT_CLASSES[Math.min(Math.max(0, depth), 10)] ?? getIndentClass(depth)
  );
}
