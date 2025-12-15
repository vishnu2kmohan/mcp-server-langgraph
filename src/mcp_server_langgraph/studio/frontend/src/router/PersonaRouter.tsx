/**
 * PersonaRouter Component
 *
 * Routes users to appropriate sections based on their persona and permissions.
 */

import { useEffect } from "react";
import { Outlet, useLocation, useNavigate } from "react-router";
import { useAppSelector } from "../store/hooks";
import { selectUser } from "../store/slices/authSlice";
import {
  selectPersona,
  selectDefaultRoute,
  selectCanAccessRoute,
} from "../store/slices/personaSlice";

export function PersonaRouter() {
  const location = useLocation();
  const navigate = useNavigate();
  const user = useAppSelector(selectUser);
  const persona = useAppSelector(selectPersona);
  const defaultRoute = useAppSelector(selectDefaultRoute);
  const canAccessRoute = useAppSelector(
    selectCanAccessRoute(location.pathname),
  );

  const isAuthenticated = user !== null;

  useEffect(() => {
    // If not authenticated, let AuthGuard handle redirect
    if (!isAuthenticated) {
      return;
    }

    const currentPath = location.pathname;

    // Redirect root to persona's default route
    if (currentPath === "/" || currentPath === "") {
      navigate(defaultRoute, { replace: true });
      return;
    }

    // Check if user can access the current route
    if (!canAccessRoute) {
      navigate("/not-authorized", { replace: true });
      return;
    }
  }, [
    location.pathname,
    isAuthenticated,
    persona,
    defaultRoute,
    canAccessRoute,
    navigate,
  ]);

  // If not authenticated, don't render content
  if (!isAuthenticated) {
    return null;
  }

  return <Outlet />;
}
