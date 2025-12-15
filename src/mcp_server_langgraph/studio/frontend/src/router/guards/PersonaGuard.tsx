/**
 * PersonaGuard Component
 *
 * Route guard that ensures users have the required persona/role.
 * Redirects to appropriate page if persona doesn't match.
 */

import { Navigate, Outlet } from "react-router";
import { useAppSelector } from "../../store/hooks";
import {
  selectPersona,
  selectPersonaLoading,
} from "../../store/slices/personaSlice";
import type { Persona } from "../../types/auth";

export interface PersonaGuardProps {
  /** Required personas to access this route */
  allowedPersonas: Persona[];
  /** Path to redirect to if persona doesn't match */
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

  // While loading persona info, render nothing
  if (isLoading) {
    return null;
  }

  // Check if user's persona is in allowed list
  if (allowedPersonas.includes(persona)) {
    return children ? <>{children}</> : <Outlet />;
  }

  // Redirect to fallback or persona-appropriate default route
  const redirectPath = fallbackPath || PERSONA_DEFAULT_ROUTES[persona];
  return <Navigate to={redirectPath} replace />;
}

export default PersonaGuard;
