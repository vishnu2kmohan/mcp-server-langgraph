/**
 * StudioShellGuard
 *
 * Conditionally wraps /studio routes with StudioShellLayout when
 * studio_canvas_shell feature flag is enabled.
 *
 * When studio_canvas_shell is enabled:
 * - Renders StudioShellLayout (new Canvas-style UI)
 *
 * When studio_canvas_shell is disabled:
 * - Renders Outlet directly (child routes render without shell wrapper)
 *
 * This allows /studio/* to use either shell based on feature flag.
 */

import { Outlet } from "react-router";
import { useFeatureFlags } from "../../contexts/FeatureFlagContext";
import { StudioShellLayout } from "../../layout";

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
      className="flex flex-col h-screen bg-white dark:bg-neutral-900 animate-pulse"
    >
      {/* TopBar skeleton */}
      <div className="h-12 bg-neutral-100 dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700" />

      {/* Main content skeleton */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar skeleton */}
        <div className="w-64 bg-neutral-50 dark:bg-neutral-800 border-r border-neutral-200 dark:border-neutral-700">
          <div className="p-4 space-y-3">
            <div className="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-3/4" />
            <div className="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-1/2" />
            <div className="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-2/3" />
          </div>
        </div>

        {/* Main content area skeleton */}
        <div className="flex-1 bg-white dark:bg-neutral-900">
          <div className="p-6 space-y-4">
            <div className="h-6 bg-neutral-200 dark:bg-neutral-700 rounded w-1/3" />
            <div className="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-full" />
            <div className="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-5/6" />
          </div>
        </div>
      </div>

      {/* StatusBar skeleton */}
      <div className="h-6 bg-neutral-100 dark:bg-neutral-800 border-t border-neutral-200 dark:border-neutral-700" />
    </div>
  );
}

export function StudioShellGuard() {
  const { isLoading, isError, isEnabled } = useFeatureFlags();

  // Show skeleton while feature flags are loading
  if (isLoading) {
    return <ShellSkeleton />;
  }

  // On error, default to StudioShell (fail-open) for better UX
  const isStudioShellEnabled = isError
    ? true
    : isEnabled("studio_canvas_shell");

  // When studio shell is enabled, render StudioShellLayout
  // StudioShellLayout includes its own Outlet for child routes
  if (isStudioShellEnabled) {
    return <StudioShellLayout />;
  }

  // When disabled, render Outlet directly
  // Child routes render without shell wrapper (legacy mode)
  return <Outlet />;
}

export default StudioShellGuard;
