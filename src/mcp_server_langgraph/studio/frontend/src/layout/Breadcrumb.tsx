/**
 * Breadcrumb Component
 *
 * Renders navigation breadcrumb trail with clickable items.
 * Current page is displayed as text (not clickable).
 *
 * Accessibility:
 * - Uses nav element with aria-label
 * - Ordered list for proper semantics
 * - aria-current="page" on current item
 * - Separators hidden from screen readers
 *
 * @see ADR-0091 - StudioShell UX Audit Phase 2.2
 */
import { Link } from "react-router";
import { useReducedMotion } from "motion/react";
import { cn } from "../utils/cn";
import type { BreadcrumbItem } from "../hooks/useBreadcrumb";

export interface BreadcrumbProps {
  /** Breadcrumb items to render */
  items: BreadcrumbItem[];
  /** Additional CSS classes */
  className?: string;
}

/**
 * Breadcrumb navigation component
 *
 * @example
 * ```tsx
 * const items = [
 *   { label: "Projects", path: "/studio/projects", isCurrent: false },
 *   { label: "My Project", path: "/studio/projects/123", isCurrent: true },
 * ];
 * <Breadcrumb items={items} />
 * ```
 */
export function Breadcrumb({ items, className }: BreadcrumbProps) {
  // WCAG 2.2 AA: Respect user's reduced motion preference
  const prefersReducedMotion = useReducedMotion();

  // Don't render if no items
  if (items.length === 0) {
    return null;
  }

  return (
    <nav
      data-testid="breadcrumb-nav"
      aria-label="Breadcrumb"
      className={cn("flex items-center", className)}
    >
      <ol className="flex items-center gap-2">
        {items.map((item, index) => (
          <li
            key={item.path}
            data-testid={`breadcrumb-item-${index}`}
            className="flex items-center gap-2"
          >
            {/* Separator (except for first item) */}
            {index > 0 && (
              <span
                className="text-neutral-9"
                aria-hidden="true"
              >
                /
              </span>
            )}

            {/* Link or current page text */}
            {item.isCurrent ? (
              <span
                aria-current="page"
                className="truncate max-w-32 min-w-0 text-sm font-medium text-neutral-12"
              >
                {item.label}
              </span>
            ) : (
              <Link
                to={item.path}
                className={cn(
                  "truncate max-w-32 min-w-0",
                  "text-sm font-medium",
                  "text-neutral-10",
                  "hover:text-neutral-11",
                  "hover:underline",
                  !prefersReducedMotion && "transition-colors",
                )}
              >
                {item.label}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
