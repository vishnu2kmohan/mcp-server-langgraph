/**
 * RootRedirect
 *
 * Simple redirect component for the root route.
 *
 * Always redirects to /studio - the feature flag check happens in App.tsx
 * which decides whether to render HybridShellLayout or AppShell.
 *
 * This provides a clean separation:
 * - RootRedirect: Just redirects to /studio
 * - App.tsx: Decides which shell to render based on feature flag
 */

import { Navigate } from "react-router";

export function RootRedirect() {
  // Always redirect to /studio - App.tsx handles shell selection based on feature flag
  return <Navigate to="/studio" replace />;
}

export default RootRedirect;
