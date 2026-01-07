/**
 * useBreadcrumb Hook
 *
 * Provides navigation breadcrumb items based on current route hierarchy.
 * Uses react-router's useMatches() to get matched routes with handle.breadcrumb metadata.
 *
 * Usage:
 * 1. Add handle: { breadcrumb: "Label" } to route definitions
 * 2. For dynamic labels, use: handle: { breadcrumb: (params) => `Item: ${params.id}` }
 * 3. Use useBreadcrumb() in components to get BreadcrumbItem[]
 *
 * @see ADR-0091 - StudioShell UX Audit Phase 2.2
 */
import { useMemo } from "react";
import { useMatches } from "react-router";

/**
 * Breadcrumb item for navigation hierarchy
 */
export interface BreadcrumbItem {
  /** Display text for the breadcrumb */
  label: string;
  /** Navigation path */
  path: string;
  /** Whether this is the current page (last item) */
  isCurrent: boolean;
}

/**
 * Route handle with optional breadcrumb configuration
 */
interface RouteHandle {
  breadcrumb?: string | ((params: Record<string, string>) => string) | null;
}

/**
 * Match object from useMatches with handle typed
 */
interface RouteMatch {
  id: string;
  pathname: string;
  params?: Record<string, string>;
  handle?: RouteHandle;
}

/**
 * Hook to generate breadcrumb items from route hierarchy
 *
 * @returns Array of BreadcrumbItem for rendering
 *
 * @example
 * ```tsx
 * // In a component
 * const breadcrumbs = useBreadcrumb();
 * return <Breadcrumb items={breadcrumbs} />;
 *
 * // In router config
 * {
 *   path: "projects",
 *   handle: { breadcrumb: "Projects" },
 *   children: [
 *     {
 *       path: ":projectId",
 *       handle: { breadcrumb: (params) => `Project: ${params.projectId}` },
 *     }
 *   ]
 * }
 * ```
 */
export function useBreadcrumb(): BreadcrumbItem[] {
  const matches = useMatches() as RouteMatch[];

  return useMemo(() => {
    // Filter routes that have breadcrumb metadata
    const breadcrumbMatches = matches.filter((match) => {
      const handle = match.handle;
      if (!handle || handle.breadcrumb === undefined) return false;
      if (handle.breadcrumb === null || handle.breadcrumb === "") return false;
      return true;
    });

    // Map to BreadcrumbItem array
    return breadcrumbMatches.map((match, index) => {
      const isLast = index === breadcrumbMatches.length - 1;
      const handle = match.handle!;
      const breadcrumb = handle.breadcrumb!;

      // Resolve label - can be string or function
      let label: string;
      if (typeof breadcrumb === "function") {
        label = breadcrumb(match.params ?? {});
      } else {
        label = breadcrumb;
      }

      return {
        label,
        path: match.pathname,
        isCurrent: isLast,
      };
    });
  }, [matches]);
}
