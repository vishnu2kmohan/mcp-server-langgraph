/**
 * useSafeRouteLoaderData Hook
 *
 * A safe wrapper around useRouteLoaderData that gracefully handles
 * cases where the component is not within a data router context.
 *
 * This is useful for components that need to work in both:
 * - Data router context (createBrowserRouter) - v2 routes with loaders
 * - Non-data router context (MemoryRouter) - tests and legacy routes
 */
import { useContext, useMemo } from "react";
import { UNSAFE_DataRouterContext } from "react-router";

/**
 * Check if we're inside a data router context.
 * Returns true if useRouteLoaderData is safe to call.
 */
export function useIsDataRouter(): boolean {
  const context = useContext(UNSAFE_DataRouterContext);
  return context !== null;
}

/**
 * Safe version of useRouteLoaderData.
 * Returns undefined if not in a data router context instead of throwing.
 *
 * This hook directly accesses the router state instead of calling useRouteLoaderData
 * to avoid the invariant check that throws when not in a data router.
 *
 * @param routeId - The route ID to get loader data from
 * @returns The loader data or undefined
 */
export function useSafeRouteLoaderData<T>(routeId: string): T | undefined {
  const dataRouterContext = useContext(UNSAFE_DataRouterContext);

  return useMemo(() => {
    // Not in a data router context
    if (!dataRouterContext?.router?.state) {
      return undefined;
    }

    const state = dataRouterContext.router.state;
    const loaderData = state.loaderData?.[routeId];

    return loaderData as T | undefined;
  }, [dataRouterContext, routeId]);
}
