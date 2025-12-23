/**
 * RootRedirect
 *
 * Simple redirect component for the root route.
 *
 * Always redirects to /studio where StudioShellGuard handles shell rendering
 * based on the studio_canvas_shell feature flag.
 *
 * This provides a clean separation:
 * - RootRedirect: Just redirects to /studio
 * - StudioShellGuard: Decides which shell to render based on feature flag
 */

import { Navigate } from "react-router";

export function RootRedirect() {
  // Always redirect to /studio - StudioShellGuard handles shell selection
  return <Navigate to="/studio" replace />;
}

export default RootRedirect;
