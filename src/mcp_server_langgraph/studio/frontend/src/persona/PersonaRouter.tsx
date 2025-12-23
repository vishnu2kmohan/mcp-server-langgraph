/**
 * PersonaRouter
 *
 * Persona-aware router component that:
 * - Redirects users to their default view based on persona
 * - Blocks access to unauthorized routes
 * - Shows loading state while persona is loading
 */
import { useEffect, useMemo, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router";
import { Loader2, ShieldX, ArrowRight } from "lucide-react";
import { useAppSelector } from "../store/hooks";
import {
  selectPersona,
  selectSubPersona,
  selectPersonaLoading,
  selectDefaultRoute,
  selectVisibleModules,
} from "../store/slices/personaSlice";
import { type ModuleId } from "./PersonaVariants";
import { cn } from "../utils/cn";

// =============================================================================
// Types
// =============================================================================

export interface PersonaRouterProps {
  children: ReactNode;
  /** Additional class name */
  className?: string;
}

// =============================================================================
// Route to Module Mapping
// =============================================================================

const ROUTE_TO_MODULE: Record<string, ModuleId> = {
  "/studio/v2/chat": "chat",
  "/studio/v2/admin": "admin",
  "/studio/v2/compliance": "compliance",
  "/studio/v2/audit": "audit",
  "/studio/v2/flows": "flows",
  "/studio/v2/agents": "agents",
  "/studio/v2/mcp": "mcp",
  "/studio/v2/files": "files",
  "/studio/v2/traces": "traces",
  "/studio/v2/costs": "costs",
  "/studio/v2/observability": "metrics",
  "/studio/v2/connections": "connections",
  "/studio/v2/projects": "projects",
  "/studio/v2/help": "help",
};

/**
 * Extract module from route path
 */
function getModuleFromRoute(pathname: string): ModuleId | null {
  // Direct match
  if (ROUTE_TO_MODULE[pathname]) {
    return ROUTE_TO_MODULE[pathname];
  }

  // Check if route starts with any known path
  for (const [route, module] of Object.entries(ROUTE_TO_MODULE)) {
    if (pathname.startsWith(route)) {
      return module;
    }
  }

  return null;
}

// =============================================================================
// Component
// =============================================================================

export function PersonaRouter({ children, className }: PersonaRouterProps) {
  const location = useLocation();
  const navigate = useNavigate();

  const persona = useAppSelector(selectPersona);
  const subPersona = useAppSelector(selectSubPersona);
  const isLoading = useAppSelector(selectPersonaLoading);
  const defaultRoute = useAppSelector(selectDefaultRoute);
  const visibleModules = useAppSelector(selectVisibleModules);

  // Check if current route is accessible
  const routeModule = useMemo(
    () => getModuleFromRoute(location.pathname),
    [location.pathname],
  );

  const canAccess = useMemo(() => {
    // Allow access to exact index route (will redirect)
    if (
      location.pathname === "/studio/v2" ||
      location.pathname === "/studio/v2/"
    ) {
      return true;
    }

    // Admin can access everything
    if (persona === "admin" && !subPersona) {
      return true;
    }

    // If we can't determine the module, allow access (let other guards handle it)
    if (!routeModule) {
      return true;
    }

    // Check if module is visible for current persona
    return visibleModules.includes(routeModule);
  }, [location.pathname, persona, subPersona, routeModule, visibleModules]);

  // Handle index route redirect
  useEffect(() => {
    if (isLoading) return;

    // Redirect index route to default view
    if (
      location.pathname === "/studio/v2" ||
      location.pathname === "/studio/v2/"
    ) {
      navigate(defaultRoute, { replace: true });
    }
  }, [isLoading, location.pathname, defaultRoute, navigate]);

  // Loading state
  if (isLoading) {
    return (
      <div
        data-testid="persona-loading"
        role="status"
        aria-label="Loading persona"
        className={cn(
          "flex flex-col items-center justify-center h-full gap-4",
          "text-gray-500 dark:text-gray-400",
          className,
        )}
      >
        <Loader2 className="h-8 w-8 animate-spin" />
        <p className="text-sm">Loading your workspace...</p>
      </div>
    );
  }

  // Access denied state
  if (!canAccess) {
    return (
      <div
        data-testid="access-denied"
        role="alert"
        aria-label="Access denied"
        className={cn(
          "flex flex-col items-center justify-center h-full gap-4 p-8",
          "text-gray-500 dark:text-gray-400",
          className,
        )}
      >
        <ShieldX className="h-16 w-16 text-red-400" />
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Access Denied
        </h2>
        <p className="text-sm text-center max-w-md">
          You don&apos;t have permission to access this page. Your current role
          ({subPersona || persona}) doesn&apos;t include access to this module.
        </p>
        <div className="flex gap-4 mt-4">
          <button
            onClick={() => navigate(defaultRoute)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-md",
              "bg-primary-600 text-white",
              "hover:bg-primary-700 transition-colors",
            )}
          >
            Go to Home
            <ArrowRight className="h-4 w-4" />
          </button>
          <a
            href="mailto:admin@example.com?subject=Access Request"
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-md",
              "border border-gray-300 dark:border-gray-600",
              "text-gray-700 dark:text-gray-300",
              "hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors",
            )}
          >
            Request Access
          </a>
        </div>
      </div>
    );
  }

  // Render children if access is granted
  return <>{children}</>;
}
