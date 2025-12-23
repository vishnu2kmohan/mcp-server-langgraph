/**
 * usePersonaRouting Hook
 *
 * Provides persona-based routing functionality for StudioShellLayout.
 * Extracted from PersonaRouter to work with component wrapper pattern.
 *
 * Features:
 * - Authentication status check
 * - Default route redirect for index paths
 * - Route access validation based on persona
 * - Persona info for UI filtering
 */
import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router";
import { useAppSelector } from "../store/hooks";
import { selectUser } from "../store/slices/authSlice";
import {
  selectPersona,
  selectDefaultRoute,
  selectCanAccessRoute,
} from "../store/slices/personaSlice";

export interface PersonaRoutingResult {
  /** Whether the user is authenticated */
  isAuthenticated: boolean;
  /** Current persona (admin, developer, user) */
  persona: string;
  /** Default route for current persona */
  defaultRoute: string;
  /** Whether current route is accessible by persona */
  canAccessRoute: boolean;
}

/**
 * Hook for persona-based routing in StudioShellLayout.
 *
 * Handles:
 * - Redirect to default route when on index path
 * - Route access validation
 * - Returns persona info for UI filtering
 *
 * @returns PersonaRoutingResult with auth status, persona, and routing info
 */
export function usePersonaRouting(): PersonaRoutingResult {
  const location = useLocation();
  const navigate = useNavigate();

  // Get auth and persona state from Redux
  const user = useAppSelector(selectUser);
  const persona = useAppSelector(selectPersona);
  const defaultRoute = useAppSelector(selectDefaultRoute);
  const canAccessRoute = useAppSelector(
    selectCanAccessRoute(location.pathname),
  );

  const isAuthenticated = user !== null;

  // Handle redirects
  useEffect(() => {
    // If not authenticated, let AuthGuard handle redirect
    if (!isAuthenticated) {
      return;
    }

    const currentPath = location.pathname;

    // Only redirect legacy root paths to persona's default route
    // /studio/v2 and /studio/v2/ are handled by the router's index redirect
    // (Navigate to="chat" in router config)
    if (currentPath === "/" || currentPath === "") {
      navigate(defaultRoute, { replace: true });
      return;
    }

    // Note: Route access blocking is handled by PermissionGuard
    // This hook provides canAccessRoute for informational purposes
  }, [location.pathname, isAuthenticated, defaultRoute, navigate]);

  return {
    isAuthenticated,
    persona,
    defaultRoute,
    canAccessRoute,
  };
}
