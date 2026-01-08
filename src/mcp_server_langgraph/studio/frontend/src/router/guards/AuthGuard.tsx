/**
 * AuthGuard Component
 *
 * Route guard that ensures users are authenticated.
 * Redirects to login page if not authenticated.
 */

import { Navigate, useLocation, Outlet } from "react-router";
import { useAppSelector } from "../../store/hooks";
import { selectUser, selectIsInitializing } from "../../store/slices/authSlice";

export interface AuthGuardProps {
  /** Path to redirect to if not authenticated */
  loginPath?: string;
  /** Children to render if authenticated */
  children?: React.ReactNode;
}

/**
 * AuthGuard wraps routes that require authentication.
 * Shows loading state during initialization, redirects to login if not authenticated.
 */
export function AuthGuard({ loginPath = "/login", children }: AuthGuardProps) {
  const location = useLocation();
  const user = useAppSelector(selectUser);
  const isInitializing = useAppSelector(selectIsInitializing);

  // Show loading during auth initialization
  if (isInitializing) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            Loading...
          </p>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!user) {
    // Save the attempted location for redirect after login
    return <Navigate to={loginPath} state={{ from: location }} replace />;
  }

  // Render children or outlet for nested routes
  return children ? <>{children}</> : <Outlet />;
}

export default AuthGuard;
