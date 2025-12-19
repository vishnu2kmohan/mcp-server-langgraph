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
import { useFeatureFlag } from "../../contexts/FeatureFlagContext";
import type { ReactNode } from "react";

export interface HybridShellGuardProps {
  children: ReactNode;
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
  const isHybridShellEnabled = useFeatureFlag("canvas_hybrid_shell");
  const { pathname, search } = useLocation();

  // If feature flag is enabled, render children (Hybrid Shell)
  if (isHybridShellEnabled) {
    return <>{children}</>;
  }

  // Otherwise, redirect to legacy studio routes
  const legacyPath = mapToLegacyPath(pathname, search);
  return <Navigate to={legacyPath} replace />;
}
