/**
 * PermissionGuard Component
 *
 * Route guard that checks fine-grained permissions using the permission cache.
 * Integrates with usePermissionCache for efficient RBAC enforcement.
 *
 * Features:
 * - Permission-based access control
 * - AND/OR logic for multiple permissions
 * - Admin bypass
 * - Loading state handling
 * - Error fallback
 */

import { useState, useEffect, type ReactNode } from "react";
import { Navigate, Outlet } from "react-router";
import { useAppSelector } from "../../store/hooks";
import { selectPersona } from "../../store/slices/personaSlice";
import { usePermissionCache } from "../../hooks/usePermissionCache";

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
 * PermissionGuard wraps routes that require specific permissions.
 * Uses permission cache for efficient checks with automatic invalidation.
 */
export function PermissionGuard({
  requiredPermissions,
  requireAll = true,
  fallbackPath = "/studio/chat",
  loadingComponent,
  children,
}: PermissionGuardProps) {
  const persona = useAppSelector(selectPersona);
  const { checkPermissions, isLoading: isCacheLoading } = usePermissionCache({
    fetchPermissions: async () => {
      // In a real implementation, this would fetch from the API
      // For now, return empty array (permissions will be checked against cache)
      return [];
    },
  });

  const [isChecking, setIsChecking] = useState(true);
  const [hasAccess, setHasAccess] = useState(false);

  useEffect(() => {
    let mounted = true;

    const checkAccess = async () => {
      // Admin bypass - admins always have access
      if (persona === "admin") {
        if (mounted) {
          setHasAccess(true);
          setIsChecking(false);
        }
        return;
      }

      try {
        const results = await checkPermissions(requiredPermissions);

        if (mounted) {
          // Apply AND/OR logic
          const granted = requireAll
            ? results.every((r) => r)
            : results.some((r) => r);

          setHasAccess(granted);
          setIsChecking(false);
        }
      } catch {
        // On error, deny access
        if (mounted) {
          setHasAccess(false);
          setIsChecking(false);
        }
      }
    };

    checkAccess();

    return () => {
      mounted = false;
    };
  }, [persona, requiredPermissions, requireAll, checkPermissions]);

  // Show loading state
  if (isChecking || isCacheLoading) {
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
