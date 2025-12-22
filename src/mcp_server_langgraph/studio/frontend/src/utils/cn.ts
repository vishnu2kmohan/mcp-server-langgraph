/**
 * cn (classNames) Utility
 *
 * A lightweight utility for conditionally joining class names.
 * Filters out falsy values (undefined, null, false, empty strings).
 *
 * @example
 * cn("base", isActive && "active", isError && "error")
 * // Returns "base active" if isActive is true, isError is false
 */
export function cn(
  ...classes: (string | undefined | boolean | null)[]
): string {
  return classes.filter(Boolean).join(" ");
}
