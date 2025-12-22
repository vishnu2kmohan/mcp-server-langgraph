/**
 * HybridShellGuard
 *
 * Phase 7: Integration - Feature Flag Gating
 * Guards access to the Hybrid Canvas shell based on feature flag.
 *
 * When `canvas_hybrid_shell` is enabled:
 * - Renders children (HybridShellLayout)
 *
 * When `canvas_hybrid_shell` is disabled:
 * - Redirects to legacy /studio routes
 * - Maps /studio/v2/* paths to /studio/*
 */

import { Navigate, useLocation } from "react-router";
import { useFeatureFlags } from "../../contexts/FeatureFlagContext";
import type { ReactNode } from "react";

export interface HybridShellGuardProps {
  children: ReactNode;
}

/**
 * Loading skeleton for HybridShell
 * Shows a minimal app shell skeleton while feature flags are loading.
 */
function HybridShellSkeleton() {
  return (
    <div
      data-testid="hybrid-shell-loading"
      aria-busy="true"
      aria-label="Loading application"
      className="flex flex-col h-screen bg-white dark:bg-gray-900 animate-pulse"
    >
      {/* TopBar skeleton */}
      <div className="h-12 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700" />

      {/* Main content skeleton */}
      <div className="flex flex-1 overflow-hidden">
        {/* Activity bar skeleton */}
        <div className="w-14 bg-gray-50 dark:bg-gray-850 border-r border-gray-200 dark:border-gray-700" />

        {/* Session nav skeleton */}
        <div className="w-64 bg-gray-50 dark:bg-gray-850 border-r border-gray-200 dark:border-gray-700">
          <div className="p-4 space-y-3">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-2/3" />
          </div>
        </div>

        {/* Conversation panel skeleton */}
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

/**
 * Maps /studio/v2/* paths to legacy /studio/* paths for fallback redirect.
 * Preserves query params from original URL.
 */
function mapToLegacyPath(pathname: string, search: string): string {
  // Remove /v2 segment from path
  const legacyPath = pathname.replace("/studio/v2", "/studio");

  // Special handling for session ID in chat paths
  // /studio/v2/chat/:sessionId -> /studio/chat (session managed by query param in legacy)
  if (legacyPath.match(/^\/studio\/chat\/.+/)) {
    return `/studio/chat${search}`;
  }

  return `${legacyPath}${search}`;
}

export function HybridShellGuard({ children }: HybridShellGuardProps) {
  const { isLoading, isError, isEnabled } = useFeatureFlags();
  const { pathname, search } = useLocation();

  // Wait for feature flags to load before making a decision
  // This prevents premature redirect while flags are being fetched
  if (isLoading) {
    // Show skeleton while loading - better UX than blank screen
    return <HybridShellSkeleton />;
  }

  // On error, default to enabling hybrid shell (fail-open)
  // This allows users to access v2 even if feature flag API fails
  // Alternative: fail-closed by redirecting to legacy
  const isHybridShellEnabled = isError ? true : isEnabled("canvas_hybrid_shell");

  // If feature flag is enabled, render children (Hybrid Shell)
  if (isHybridShellEnabled) {
    return <>{children}</>;
  }

  // Otherwise, redirect to legacy studio routes
  const legacyPath = mapToLegacyPath(pathname, search);
  return <Navigate to={legacyPath} replace />;
}
