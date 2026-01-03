/**
 * usePermission Hook
 *
 * Returns permission check result for the current user.
 * Used for conditional UI rendering based on user permissions.
 *
 * @example
 * ```tsx
 * function AdminButton() {
 *   const { allowed, reason } = usePermission('admin:users:write');
 *
 *   if (!allowed) {
 *     return <Tooltip content={reason}><Button disabled>Manage Users</Button></Tooltip>;
 *   }
 *
 *   return <Button onClick={handleManageUsers}>Manage Users</Button>;
 * }
 * ```
 */

import { useAppSelector } from "../store/hooks";
import {
  selectHasPermission,
  selectPersona,
  selectCanAccessRoute,
} from "../store/slices/personaSlice";

export interface PermissionResult {
  /** Whether the user has the permission */
  allowed: boolean;
  /** Reason for denial (null if allowed) */
  reason: string | null;
}

/**
 * Hook to check if the current user has a specific permission.
 *
 * @param permission - Permission string to check (e.g., 'admin:users:write')
 * @returns PermissionResult with allowed status and denial reason
 */
export function usePermission(permission: string): PermissionResult {
  const hasPermission = useAppSelector(selectHasPermission(permission));
  const persona = useAppSelector(selectPersona);

  return {
    allowed: hasPermission,
    reason: hasPermission
      ? null
      : `Permission "${permission}" not granted for ${persona} role`,
  };
}

/**
 * Hook to check if the current user can access a specific route.
 *
 * @param route - Route path to check (e.g., '/studio/admin')
 * @returns PermissionResult with allowed status and denial reason
 */
export function useRoutePermission(route: string): PermissionResult {
  const canAccess = useAppSelector(selectCanAccessRoute(route));
  const persona = useAppSelector(selectPersona);

  return {
    allowed: canAccess,
    reason: canAccess
      ? null
      : `Route "${route}" not accessible for ${persona} role`,
  };
}

/**
 * Hook to check multiple permissions at once.
 *
 * @param permissions - Array of permission strings to check
 * @param mode - 'all' requires all permissions, 'any' requires at least one
 * @returns PermissionResult with allowed status
 */
export function usePermissions(
  permissions: string[],
  mode: "all" | "any" = "all",
): PermissionResult {
  const persona = useAppSelector(selectPersona);

  // Check each permission
  const results = permissions.map((permission) =>
    // eslint-disable-next-line react-hooks/rules-of-hooks
    useAppSelector(selectHasPermission(permission)),
  );

  const allowed =
    mode === "all" ? results.every(Boolean) : results.some(Boolean);

  const missingPermissions = permissions.filter((_, index) => !results[index]);

  return {
    allowed,
    reason: allowed
      ? null
      : mode === "all"
        ? `Missing permissions: ${missingPermissions.join(", ")}`
        : `None of the required permissions granted for ${persona} role`,
  };
}

export default usePermission;
