/**
 * PersonaRouter Component
 *
 * Routes users to appropriate sections based on their persona and permissions.
 */

import { useEffect } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { usePersonaStore } from '../stores/personaStore';
import { useAuthStore } from '../stores/authStore';

export function PersonaRouter() {
  const location = useLocation();
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const { persona, getDefaultRoute, canAccessRoute } = usePersonaStore();

  const isAuthenticated = user !== null;

  useEffect(() => {
    // If not authenticated, let AuthGuard handle redirect
    if (!isAuthenticated) {
      return;
    }

    const currentPath = location.pathname;

    // Redirect root to persona's default route
    if (currentPath === '/' || currentPath === '') {
      const defaultRoute = getDefaultRoute();
      navigate(defaultRoute, { replace: true });
      return;
    }

    // Check if user can access the current route
    if (!canAccessRoute(currentPath)) {
      navigate('/not-authorized', { replace: true });
      return;
    }
  }, [location.pathname, isAuthenticated, persona, getDefaultRoute, canAccessRoute, navigate]);

  // If not authenticated, don't render content
  if (!isAuthenticated) {
    return null;
  }

  return <Outlet />;
}
