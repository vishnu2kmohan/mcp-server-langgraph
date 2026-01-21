/**
 * OAuth2CallbackPage
 *
 * Handles OAuth2 authorization callback:
 * - Extracts code and state from URL parameters
 * - Calls backend to exchange code for tokens
 * - Shows success or error state
 * - Redirects to connections page on success
 */

import { useEffect, useState, useCallback } from "react";
import { useSearchParams, useNavigate } from "react-router";
import {
  CheckCircle,
  XCircle,
  Loader2,
  RefreshCw,
  ArrowLeft,
} from "lucide-react";
import { authenticatedFetch } from "../utils/authenticatedFetch";
import { saveCurrentRouteAsIntended } from "../utils/intendedRoute";
import { transformSnakeToCamel } from "../api/transforms";

// Direct imports to avoid Rollup circular dependency warnings
// (page chunks end up separate from UI barrel)
import { Button } from "@/components/UI/Button";

type CallbackState = "processing" | "success" | "error";

interface CallbackError {
  type:
    | "missing_code"
    | "missing_state"
    | "oauth_error"
    | "api_error"
    | "network_error";
  message: string;
  detail?: string;
}

export function OAuth2CallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const handleAuthFailure = useCallback(() => {
    saveCurrentRouteAsIntended();
    navigate("/login", { replace: true });
  }, [navigate]);

  const [state, setState] = useState<CallbackState>("processing");
  const [error, setError] = useState<CallbackError | null>(null);
  const [connectionId, setConnectionId] = useState<string | null>(null);

  // Extract parameters from URL
  const code = searchParams.get("code");
  const oauthState = searchParams.get("state");
  const oauthError = searchParams.get("error");
  const oauthErrorDescription = searchParams.get("error_description");

  const processCallback = useCallback(async () => {
    // Reset state
    setState("processing");
    setError(null);

    // Check for OAuth error in URL
    if (oauthError) {
      setState("error");
      setError({
        type: "oauth_error",
        message: oauthError,
        detail: oauthErrorDescription || undefined,
      });
      return;
    }

    // Validate required parameters
    if (!code) {
      setState("error");
      setError({
        type: "missing_code",
        message: "Missing authorization code",
        detail:
          "The authorization server did not return an authorization code.",
      });
      return;
    }

    if (!oauthState) {
      setState("error");
      setError({
        type: "missing_state",
        message: "Missing state parameter",
        detail:
          "The authorization response did not include a state parameter for CSRF protection.",
      });
      return;
    }

    // Call backend API
    try {
      const response = await authenticatedFetch(
        "/api/v1/connections/oauth/callback",
        {
          method: "POST",
          body: JSON.stringify({
            code,
            state: oauthState,
          }),
          onAuthFailure: handleAuthFailure,
        },
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ detail: "Unknown error" }));
        setState("error");
        setError({
          type: "api_error",
          message: "Authorization failed",
          detail: errorData.detail || `Server returned ${response.status}`,
        });
        return;
      }

      const rawData = await response.json();
      // Transform snake_case to camelCase per ADR-0091 Phase 6
      const data = transformSnakeToCamel<{ connectionId: string }>(rawData);
      setConnectionId(data.connectionId);
      setState("success");

      // Redirect to connections page after a brief delay
      setTimeout(() => {
        navigate("/studio/connections");
      }, 2000);
    } catch (err) {
      setState("error");
      setError({
        type: "network_error",
        message: "Connection error",
        detail:
          err instanceof Error ? err.message : "Failed to connect to server",
      });
    }
  }, [
    code,
    oauthState,
    oauthError,
    oauthErrorDescription,
    navigate,
    handleAuthFailure,
  ]);

  // Process callback on mount
  useEffect(() => {
    processCallback();
  }, [processCallback]);

  // Render processing state
  if (state === "processing") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-neutral-1">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-primary-9 mx-auto mb-4" />
          <h1 className="text-xl font-semibold text-neutral-12 mb-2">
            Processing Authorization
          </h1>
          <p className="text-neutral-11">
            Please wait while we complete the OAuth2 flow...
          </p>
        </div>
      </div>
    );
  }

  // Render success state
  if (state === "success") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-neutral-1">
        <div className="text-center">
          <CheckCircle className="w-16 h-16 text-success-9 mx-auto mb-4" />
          <h1 className="text-xl font-semibold text-neutral-12 mb-2">
            Authorization Successful
          </h1>
          <p className="text-neutral-11 mb-4">
            Your MCP connection has been authorized.
            {connectionId && (
              <span className="block text-sm mt-1">
                Connection ID: {connectionId}
              </span>
            )}
          </p>
          <p className="text-sm text-neutral-9">
            Redirecting to connections...
          </p>
        </div>
      </div>
    );
  }

  // Render error state
  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-1">
      <div className="text-center max-w-md mx-4">
        <XCircle className="w-16 h-16 text-error-9 mx-auto mb-4" />
        <h1 className="text-xl font-semibold text-neutral-12 mb-2">
          Authorization Failed
        </h1>
        {error && (
          <>
            <p className="text-error-10 mb-2">
              {error.message}
            </p>
            {error.detail && (
              <p className="text-neutral-11 text-sm mb-4">
                {error.detail}
              </p>
            )}
          </>
        )}
        <div className="flex items-center justify-center gap-4 mt-6">
          <Button
            variant="primary"
            className="gap-2"
            onClick={() => processCallback()}
          >
            <RefreshCw className="w-4 h-4" />
            Try Again
          </Button>
          <Button
            variant="ghost"
            className="gap-2"
            onClick={() => navigate("/studio/connections")}
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Connections
          </Button>
        </div>
      </div>
    </div>
  );
}
