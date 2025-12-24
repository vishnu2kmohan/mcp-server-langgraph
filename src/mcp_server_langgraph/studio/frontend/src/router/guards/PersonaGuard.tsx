/**
 * PersonaGuard Component
 *
 * Route guard that ensures users have the required persona/role.
 * Redirects to appropriate page if persona doesn't match.
 *
 * Sprint 4: Enhanced with module-based access control using server-provided
 * visible_modules from /api/v1/me endpoint.
 */

import { Navigate, Outlet } from "react-router";
import { useAppSelector } from "../../store/hooks";
import {
  selectPersona,
  selectPersonaLoading,
  selectVisibleModules,
} from "../../store/slices/personaSlice";
import type { Persona } from "../../types/auth";
import type { ModuleId } from "../../persona/PersonaVariants";

export interface PersonaGuardProps {
  /** Required personas to access this route */
  allowedPersonas: Persona[];
  /** Path to redirect to if persona doesn't match */
  fallbackPath?: string;
  /** Children to render if authorized */
  children?: React.ReactNode;
}

/**
 * Sprint 4: Module-based guard props.
 * Uses server-provided visible_modules for access control.
 */
export interface ModuleGuardProps {
  /** Required module to access this route */
  requiredModule: ModuleId;
  /** Path to redirect to if module not accessible */
  fallbackPath?: string;
  /** Children to render if authorized */
  children?: React.ReactNode;
}

/** Default routes for each persona */
const PERSONA_DEFAULT_ROUTES: Record<Persona, string> = {
  admin: "/studio/admin/dashboard",
  developer: "/studio/workflows",
  user: "/studio/chat",
};

/**
 * PersonaGuard wraps routes that require specific personas.
 * Redirects to persona-appropriate default route if not authorized.
 */
export function PersonaGuard({
  allowedPersonas,
  fallbackPath,
  children,
}: PersonaGuardProps) {
  const persona = useAppSelector(selectPersona);
  const isLoading = useAppSelector(selectPersonaLoading);

  // While loading persona info, show loading spinner
  // This prevents a blank page during the race between authSlice and personaSlice
  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            Loading...
          </p>
        </div>
      </div>
    );
  }

  // Check if user's persona is in allowed list
  if (allowedPersonas.includes(persona)) {
    return children ? <>{children}</> : <Outlet />;
  }

  // Redirect to fallback or persona-appropriate default route
  const redirectPath = fallbackPath || PERSONA_DEFAULT_ROUTES[persona];
  return <Navigate to={redirectPath} replace />;
}

/**
 * Sprint 4: ModuleGuard wraps routes that require access to specific modules.
 * Uses server-provided visible_modules for fine-grained access control.
 *
 * This is preferred over PersonaGuard for routes tied to specific features,
 * as it respects the server-side RBAC configuration.
 */
export function ModuleGuard({
  requiredModule,
  fallbackPath = "/studio/chat",
  children,
}: ModuleGuardProps) {
  const persona = useAppSelector(selectPersona);
  const isLoading = useAppSelector(selectPersonaLoading);
  const visibleModules = useAppSelector(selectVisibleModules);

  // While loading persona info, show loading spinner
  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            Loading...
          </p>
        </div>
      </div>
    );
  }

  // Check if user has access to the required module
  if (visibleModules.includes(requiredModule)) {
    return children ? <>{children}</> : <Outlet />;
  }

  // Redirect to fallback or persona-appropriate default route
  const redirectPath = fallbackPath || PERSONA_DEFAULT_ROUTES[persona];
  return <Navigate to={redirectPath} replace />;
}

export default PersonaGuard;
