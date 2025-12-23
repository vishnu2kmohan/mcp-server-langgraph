/**
 * StudioShellGuard
 *
 * Conditionally wraps /studio routes with HybridShellLayout when
 * canvas_hybrid_shell feature flag is enabled.
 *
 * When canvas_hybrid_shell is enabled:
 * - Renders HybridShellLayout (new Canvas-style UI)
 *
 * When canvas_hybrid_shell is disabled:
 * - Renders Outlet directly (App.tsx wraps with AppShell)
 *
 * This allows /studio/* to use either shell based on feature flag,
 * eliminating the need for a separate /studio/v2/* route.
 */

import { Outlet } from "react-router";
import { useFeatureFlags } from "../../contexts/FeatureFlagContext";
import { HybridShellLayout } from "../../layout";

/**
 * Loading skeleton while feature flags are loading.
 * Shows a minimal app shell skeleton for better UX.
 */
function ShellSkeleton() {
  return (
    <div
      data-testid="studio-shell-loading"
      aria-busy="true"
      aria-label="Loading application"
      className="flex flex-col h-screen bg-white dark:bg-gray-900 animate-pulse"
    >
      {/* TopBar skeleton */}
      <div className="h-12 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700" />

      {/* Main content skeleton */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar skeleton */}
        <div className="w-64 bg-gray-50 dark:bg-gray-850 border-r border-gray-200 dark:border-gray-700">
          <div className="p-4 space-y-3">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-2/3" />
          </div>
        </div>

        {/* Main content area skeleton */}
        <div className="flex-1 bg-white dark:bg-gray-900">
          <div className="p-6 space-y-4">
            <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full" />
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6" />
          </div>
        </div>
      </div>

      {/* StatusBar skeleton */}
      <div className="h-6 bg-gray-100 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700" />
    </div>
  );
}

export function StudioShellGuard() {
  const { isLoading, isError, isEnabled } = useFeatureFlags();

  // Show skeleton while feature flags are loading
  if (isLoading) {
    return <ShellSkeleton />;
  }

  // On error, default to HybridShell (fail-open) for better UX
  const isHybridShellEnabled = isError
    ? true
    : isEnabled("canvas_hybrid_shell");

  // When hybrid shell is enabled, render HybridShellLayout
  // HybridShellLayout includes its own Outlet for child routes
  if (isHybridShellEnabled) {
    return <HybridShellLayout />;
  }

  // When disabled, render Outlet directly
  // App.tsx will wrap with AppShell for legacy rendering
  return <Outlet />;
}

export default StudioShellGuard;
