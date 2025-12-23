/**
 * usePermissionCache Hook
 *
 * Implements the PERMISSION_CACHE pattern from the plan:
 * - Cache permissions for 5 minutes (maxAge)
 * - Invalidate on 401/403 errors
 * - Store in memory (not localStorage)
 *
 * Usage:
 * ```tsx
 * const { checkPermission, invalidateCache } = usePermissionCache({
 *   fetchPermissions: async () => api.getPermissions(),
 * });
 *
 * const canEdit = await checkPermission('edit');
 * ```
 */
import {
  createContext,
  useContext,
  useCallback,
  useRef,
  useState,
  useMemo,
  type ReactNode,
} from "react";
import { useSelector } from "react-redux";
import { selectPersona } from "../store/slices/personaSlice";

// =============================================================================
// Configuration
// =============================================================================

// eslint-disable-next-line react-refresh/only-export-components
export const PERMISSION_CACHE_CONFIG = {
  /** Cache duration in milliseconds (5 minutes) */
  maxAge: 5 * 60 * 1000,
  /** HTTP status codes that trigger cache invalidation */
  invalidateOn: [401, 403] as const,
  /** Storage type (memory only, not localStorage) */
  storage: "memory" as const,
};

// =============================================================================
// Types
// =============================================================================

interface PermissionCache {
  permissions: string[];
  timestamp: number;
}

interface PermissionCacheContextValue {
  cache: React.MutableRefObject<PermissionCache | null>;
  invalidate: () => void;
}

interface UsePermissionCacheOptions {
  /** Function to fetch permissions from the server */
  fetchPermissions: () => Promise<string[]>;
}

interface UsePermissionCacheResult {
  /** Check if user has a specific permission */
  checkPermission: (permission: string) => Promise<boolean>;
  /** Check multiple permissions at once */
  checkPermissions: (permissions: string[]) => Promise<boolean[]>;
  /** Invalidate cache based on error code */
  invalidateOnError: (statusCode: number) => void;
  /** Manually invalidate the cache */
  invalidateCache: () => void;
  /** Called when tokens are refreshed to invalidate cache */
  onTokenRefresh: () => void;
  /** Whether permissions are currently being fetched */
  isLoading: boolean;
  /** Error message if fetch failed */
  error: string | null;
}

// =============================================================================
// Context
// =============================================================================

const PermissionCacheContext =
  createContext<PermissionCacheContextValue | null>(null);

/**
 * Provider for permission cache context.
 * Should be placed near the root of the app.
 */
export function PermissionCacheProvider({ children }: { children: ReactNode }) {
  const cacheRef = useRef<PermissionCache | null>(null);

  const invalidate = useCallback(() => {
    cacheRef.current = null;
  }, []);

  const value = useMemo(
    () => ({
      cache: cacheRef,
      invalidate,
    }),
    [invalidate],
  );

  return (
    <PermissionCacheContext.Provider value={value}>
      {children}
    </PermissionCacheContext.Provider>
  );
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook for checking permissions with caching.
 *
 * Features:
 * - Caches permissions in memory for 5 minutes
 * - Invalidates on 401/403 errors
 * - Admin users bypass all permission checks
 * - Supports batch permission checking
 */
// eslint-disable-next-line react-refresh/only-export-components
export function usePermissionCache({
  fetchPermissions,
}: UsePermissionCacheOptions): UsePermissionCacheResult {
  const context = useContext(PermissionCacheContext);

  if (!context) {
    throw new Error(
      "usePermissionCache must be used within a PermissionCacheProvider",
    );
  }

  const { cache, invalidate } = context;
  const persona = useSelector(selectPersona);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Track if we're currently fetching to prevent duplicate requests
  const fetchingRef = useRef<Promise<string[]> | null>(null);

  /**
   * Get permissions from cache or fetch from server.
   */
  const getPermissions = useCallback(async (): Promise<string[]> => {
    // Check if cache is valid
    if (cache.current) {
      const age = Date.now() - cache.current.timestamp;
      if (age < PERMISSION_CACHE_CONFIG.maxAge) {
        return cache.current.permissions;
      }
      // Cache expired
      cache.current = null;
    }

    // If already fetching, wait for that request
    if (fetchingRef.current) {
      return fetchingRef.current;
    }

    // Fetch new permissions
    setIsLoading(true);
    setError(null);

    try {
      fetchingRef.current = fetchPermissions();
      const permissions = await fetchingRef.current;

      // Update cache
      cache.current = {
        permissions,
        timestamp: Date.now(),
      };

      setIsLoading(false);
      return permissions;
    } catch (err) {
      setIsLoading(false);
      const errorMessage = err instanceof Error ? err.message : "Unknown error";
      setError(errorMessage);
      throw err;
    } finally {
      fetchingRef.current = null;
    }
  }, [cache, fetchPermissions]);

  /**
   * Check if user has a specific permission.
   * Admin users always return true.
   */
  const checkPermission = useCallback(
    async (permission: string): Promise<boolean> => {
      // Admin bypasses all permission checks
      if (persona === "admin") {
        return true;
      }

      try {
        const permissions = await getPermissions();
        return permissions.includes(permission);
      } catch {
        // Deny by default on error
        return false;
      }
    },
    [persona, getPermissions],
  );

  /**
   * Check multiple permissions at once.
   */
  const checkPermissions = useCallback(
    async (permissionList: string[]): Promise<boolean[]> => {
      // Admin bypasses all permission checks
      if (persona === "admin") {
        return permissionList.map(() => true);
      }

      try {
        const permissions = await getPermissions();
        return permissionList.map((p) => permissions.includes(p));
      } catch {
        // Deny all by default on error
        return permissionList.map(() => false);
      }
    },
    [persona, getPermissions],
  );

  /**
   * Invalidate cache based on error code.
   * Only invalidates for 401 and 403 errors.
   */
  const invalidateOnError = useCallback(
    (statusCode: number) => {
      if (
        PERMISSION_CACHE_CONFIG.invalidateOn.includes(
          statusCode as (typeof PERMISSION_CACHE_CONFIG.invalidateOn)[number],
        )
      ) {
        invalidate();
      }
    },
    [invalidate],
  );

  /**
   * Manually invalidate the cache.
   * Use this when you know permissions have changed.
   */
  const invalidateCache = useCallback(() => {
    invalidate();
    setError(null);
  }, [invalidate]);

  /**
   * Called when tokens are refreshed.
   * Invalidates the permission cache since new tokens may have different permissions.
   */
  const onTokenRefresh = useCallback(() => {
    invalidate();
  }, [invalidate]);

  return {
    checkPermission,
    checkPermissions,
    invalidateOnError,
    invalidateCache,
    onTokenRefresh,
    isLoading,
    error,
  };
}
