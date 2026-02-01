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
  selectSubPersona,
} from "../../store/slices/personaSlice";
import type { Persona } from "../../types/auth";
import {
  PERSONA_DEFAULT_VIEW,
  getDefaultView,
  type ModuleId,
} from "../../persona/PersonaVariants";

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

/**
 * PersonaGuard wraps routes that require specific personas.
 * Redirects to persona-appropriate default route if not authorized.
 *
 * Sprint 5: Uses PersonaVariants as source of truth for default routes,
 * supporting sub-persona-specific default views (e.g., alice-analyst → /studio/observability).
 */
export function PersonaGuard({
  allowedPersonas,
  fallbackPath,
  children,
}: PersonaGuardProps) {
  const persona = useAppSelector(selectPersona);
  const subPersona = useAppSelector(selectSubPersona);
  const isLoading = useAppSelector(selectPersonaLoading);

  // While loading persona info, show loading spinner
  // This prevents a blank page during the race between authSlice and personaSlice
  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-10 border-t-transparent" />
          <p className="mt-2 text-sm text-neutral-10">Loading...</p>
        </div>
      </div>
    );
  }

  // Check if user's persona is in allowed list
  if (allowedPersonas.includes(persona)) {
    return children ? <>{children}</> : <Outlet />;
  }

  // Redirect to fallback or persona-appropriate default route
  // Use sub-persona for more specific routing (e.g., alice-analyst → /studio/observability)
  // Falls back to base persona if sub-persona not found in PersonaVariants
  const redirectPath =
    fallbackPath ||
    (subPersona ? getDefaultView(subPersona) : null) ||
    PERSONA_DEFAULT_VIEW[persona] ||
    "/studio/chat";
  return <Navigate to={redirectPath} replace />;
}

/**
 * Sprint 4: ModuleGuard wraps routes that require access to specific modules.
 * Uses server-provided visible_modules for fine-grained access control.
 *
 * This is preferred over PersonaGuard for routes tied to specific features,
 * as it respects the server-side RBAC configuration.
 *
 * Sprint 5: Uses PersonaVariants as source of truth for default routes.
 */
export function ModuleGuard({
  requiredModule,
  fallbackPath,
  children,
}: ModuleGuardProps) {
  const persona = useAppSelector(selectPersona);
  const subPersona = useAppSelector(selectSubPersona);
  const isLoading = useAppSelector(selectPersonaLoading);
  const visibleModules = useAppSelector(selectVisibleModules);

  // While loading persona info, show loading spinner
  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-10 border-t-transparent" />
          <p className="mt-2 text-sm text-neutral-10">Loading...</p>
        </div>
      </div>
    );
  }

  // Check if user has access to the required module
  if (visibleModules.includes(requiredModule)) {
    return children ? <>{children}</> : <Outlet />;
  }

  // Redirect to fallback or persona-appropriate default route
  // Use sub-persona for more specific routing, with fallback chain
  const redirectPath =
    fallbackPath ||
    (subPersona ? getDefaultView(subPersona) : null) ||
    PERSONA_DEFAULT_VIEW[persona] ||
    "/studio/chat";
  return <Navigate to={redirectPath} replace />;
}

export default PersonaGuard;
