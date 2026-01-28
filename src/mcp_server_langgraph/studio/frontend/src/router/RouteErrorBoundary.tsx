/**
 * RouteErrorBoundary
 *
 * Error boundary component for React Router routes.
 * Catches route-level errors and displays user-friendly error UI.
 *
 * Features:
 * - Handles thrown errors from route components
 * - Handles 404 (route not found) errors
 * - Retry and Go Home navigation options
 * - WCAG 2.1 AA accessible
 * - Radix 1-12 color tokens
 */

import { useRouteError, isRouteErrorResponse, Link } from "react-router";
import { AlertTriangle, Home, RefreshCw } from "lucide-react";
import { Button } from "@/components/UI";

export function RouteErrorBoundary(): JSX.Element {
  const error = useRouteError();

  // Check if this is a route-level error (404, etc.)
  const isRouteError = isRouteErrorResponse(error);

  // Extract error message
  const errorMessage = isRouteError
    ? error.statusText
    : error instanceof Error
      ? error.message
      : "An unexpected error occurred";

  // Handle 404 specifically
  if (isRouteError && error.status === 404) {
    return (
      <div
        role="alert"
        aria-live="assertive"
        data-testid="route-error-boundary"
        className="flex min-h-screen flex-col items-center justify-center bg-neutral-1 p-6 text-center"
      >
        <div className="mb-6 text-8xl font-bold text-neutral-9">404</div>
        <h1 className="mb-2 text-2xl font-semibold text-neutral-12">
          Page not found
        </h1>
        <p className="mb-8 max-w-md text-neutral-11">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <Link
          to="/"
          className="inline-flex items-center gap-2 rounded-lg bg-primary-9 px-4 py-2 text-sm font-medium text-white hover:bg-primary-10 focus:outline-none focus:ring-2 focus:ring-primary-9 focus:ring-offset-2"
        >
          <Home className="h-4 w-4" aria-hidden="true" />
          Go home
        </Link>
      </div>
    );
  }

  // General error UI
  return (
    <div
      role="alert"
      aria-live="assertive"
      data-testid="route-error-boundary"
      className="flex min-h-screen flex-col items-center justify-center bg-neutral-1 p-6 text-center"
    >
      <AlertTriangle
        className="mb-6 h-16 w-16 text-error-9"
        aria-hidden="true"
      />
      <h1 className="mb-2 text-2xl font-semibold text-neutral-12">
        Something went wrong
      </h1>
      <p className="mb-8 max-w-md text-neutral-11">{errorMessage}</p>
      <div className="flex gap-4">
        <Button
          variant="primary"
          onClick={() => window.location.reload()}
          className="inline-flex items-center gap-2"
        >
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          Try again
        </Button>
        <Link
          to="/"
          className="inline-flex items-center gap-2 rounded-lg border border-neutral-6 bg-neutral-2 px-4 py-2 text-sm font-medium text-neutral-12 hover:bg-neutral-3 focus:outline-none focus:ring-2 focus:ring-primary-9 focus:ring-offset-2"
        >
          <Home className="h-4 w-4" aria-hidden="true" />
          Go home
        </Link>
      </div>
    </div>
  );
}
