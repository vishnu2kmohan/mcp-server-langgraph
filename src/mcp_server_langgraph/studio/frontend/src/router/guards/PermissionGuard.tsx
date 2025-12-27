/**
 * PermissionGuard Component
 *
 * Route guard that checks fine-grained permissions using Redux state.
 *
 * Features:
 * - Permission-based access control derived from visible_modules and persona
 * - AND/OR logic for multiple permissions
 * - Admin bypass (admins always have access)
 * - Developer bypass for most permissions
 * - Loading state handling while persona is loading
 *
 * Permission Derivation:
 * - "compliance:read" → requires "compliance" in visible_modules OR developer persona
 * - "audit:read" → requires "audit" in visible_modules OR developer persona
 * - "admin:access" → requires admin persona only
 */

import { useMemo, type ReactNode } from "react";
import { Navigate, Outlet } from "react-router";
import { useAppSelector } from "../../store/hooks";
import {
  selectPersona,
  selectVisibleModules,
  selectPersonaLoading,
} from "../../store/slices/personaSlice";

export interface PermissionGuardProps {
  /** Required permissions to access this route */
  requiredPermissions: string[];
  /** If true, all permissions are required (AND). If false, any permission is sufficient (OR). Default: true */
  requireAll?: boolean;
  /** Path to redirect to if permission check fails */
  fallbackPath?: string;
  /** Component to show while loading permissions */
  loadingComponent?: ReactNode;
  /** Children to render if authorized */
  children?: ReactNode;
}

/**
 * Map permission strings to their derivation logic.
 * Permission format: "module:action" (e.g., "compliance:read", "admin:access")
 *
 * Returns true if the permission is granted based on persona and visible modules.
 */
function hasPermission(
  permission: string,
  persona: string,
  visibleModules: string[],
): boolean {
  // Admin always has all permissions
  if (persona === "admin") {
    return true;
  }

  // Parse permission (format: "module:action")
  const [module, action] = permission.split(":");

  // Special case: admin:access is admin-only
  if (module === "admin" && action === "access") {
    return persona === "admin";
  }

  // Developer has read access to most modules
  if (persona === "developer" && action === "read") {
    // Developers can read compliance, audit, etc.
    return true;
  }

  // For other personas, check if the module is in their visible_modules
  // The server sends visible_modules based on the user's roles/permissions
  if (module && visibleModules.includes(module)) {
    return true;
  }

  // Default: deny
  return false;
}

/**
 * PermissionGuard wraps routes that require specific permissions.
 * Derives permissions from Redux state (persona and visible_modules).
 */
export function PermissionGuard({
  requiredPermissions,
  requireAll = true,
  fallbackPath = "/studio/chat",
  loadingComponent,
  children,
}: PermissionGuardProps) {
  const persona = useAppSelector(selectPersona);
  const visibleModules = useAppSelector(selectVisibleModules);
  const isPersonaLoading = useAppSelector(selectPersonaLoading);

  // Derive access synchronously from Redux state
  const hasAccess = useMemo(() => {
    // Admin bypass - admins always have access
    if (persona === "admin") {
      return true;
    }

    // Check each required permission
    const results = requiredPermissions.map((p) =>
      hasPermission(p, persona, visibleModules),
    );

    // Apply AND/OR logic
    return requireAll ? results.every((r) => r) : results.some((r) => r);
  }, [persona, visibleModules, requiredPermissions, requireAll]);

  // Show loading state while persona is being fetched
  if (isPersonaLoading) {
    return loadingComponent ? <>{loadingComponent}</> : null;
  }

  // Access granted
  if (hasAccess) {
    return children ? <>{children}</> : <Outlet />;
  }

  // Access denied - redirect
  return <Navigate to={fallbackPath} replace />;
}

export default PermissionGuard;
