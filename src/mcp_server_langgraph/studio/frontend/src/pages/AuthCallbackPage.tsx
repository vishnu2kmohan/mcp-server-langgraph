/**
 * AuthCallbackPage
 *
 * Handles OAuth2 Authorization Code + PKCE callback.
 * Receives tokens from URL fragment and stores them.
 *
 * Per ADR-0071: Tokens are passed in URL fragment (after #) for security.
 * Fragments are not sent to the server, only available client-side.
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { Loader2, AlertCircle, CheckCircle } from "lucide-react";
import { useAppDispatch } from "../store/hooks";
import { setUser } from "../store/slices/authSlice";
import { setUserInfo } from "../store/slices/personaSlice";
import { setAuthTokens } from "../utils/storage";
import { getIntendedRoute, clearIntendedRoute } from "../utils/intendedRoute";

// Direct imports to avoid Rollup circular dependency warnings
// (page chunks end up separate from UI barrel)
import { Button } from "@/components/UI/Button";

// Parse URL fragment into key-value pairs
function parseFragment(fragment: string): Record<string, string> {
  const params: Record<string, string> = {};
  if (!fragment) return params;

  // Remove leading # if present
  const clean = fragment.startsWith("#") ? fragment.slice(1) : fragment;

  for (const pair of clean.split("&")) {
    const [key, value] = pair.split("=");
    if (key && value) {
      params[decodeURIComponent(key)] = decodeURIComponent(value);
    }
  }

  return params;
}

// Decode JWT payload without verification (just for extracting user info)
function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;

    const payload = parts[1];
    if (!payload) return null;
    // Base64url decode
    const decoded = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(decoded);
  } catch {
    return null;
  }
}

export function AuthCallbackPage() {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [status, setStatus] = useState<"processing" | "success" | "error">(
    "processing",
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const processCallback = async () => {
      try {
        // Parse tokens from URL fragment
        const fragment = window.location.hash;
        const params = parseFragment(fragment);

        // Check for error in fragment
        if (params.error) {
          throw new Error(params.error_description || params.error);
        }

        // Extract tokens
        const accessToken = params.access_token;
        const refreshToken = params.refresh_token;

        if (!accessToken) {
          throw new Error("No access token received");
        }

        // Store tokens using centralized storage utility
        // Sets access_token, auth_token (legacy), and refresh_token
        setAuthTokens(accessToken, refreshToken || undefined);

        // Decode JWT to get user info
        const payload = decodeJwtPayload(accessToken);
        if (!payload) {
          throw new Error("Invalid access token format");
        }

        // Extract user info from JWT
        const username =
          (payload.preferred_username as string) ||
          (payload.username as string) ||
          (payload.sub as string) ||
          "unknown";
        const email = payload.email as string | undefined;

        // Extract roles from realm_access or roles claim
        let roles: string[] = [];
        if (payload.realm_access && typeof payload.realm_access === "object") {
          const realmAccess = payload.realm_access as { roles?: string[] };
          roles = realmAccess.roles || [];
        } else if (Array.isArray(payload.roles)) {
          roles = payload.roles as string[];
        }

        // Compute persona from roles
        let persona: "admin" | "developer" | "user" = "user";
        if (roles.includes("admin")) {
          persona = "admin";
        } else if (roles.includes("developer")) {
          persona = "developer";
        }

        // Update Redux state
        dispatch(
          setUser({
            username,
            email: email ?? undefined,
            roles,
            persona,
          }),
        );
        // Update persona slice - setUserInfo also sets isPersonaLoading=false
        dispatch(
          setUserInfo({
            username,
            email: email ?? undefined,
            roles,
            persona,
          }),
        );

        // Clear fragment from URL for security
        window.history.replaceState(null, "", window.location.pathname);

        // Get the intended route saved by LoginPage (if any)
        const intendedRoute = getIntendedRoute();
        clearIntendedRoute(); // Clear immediately (one-time use)

        setStatus("success");

        // Redirect to intended route or /studio after a brief success display
        setTimeout(() => {
          navigate(intendedRoute || "/studio", { replace: true });
        }, 1000);
      } catch (err) {
        setStatus("error");
        setErrorMessage(
          err instanceof Error ? err.message : "Authentication failed",
        );
      }
    };

    processCallback();
  }, [dispatch, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-1 px-4">
      <div className="w-full max-w-md">
        <div className="bg-neutral-2 rounded-2xl shadow-xl p-8 border border-neutral-6 text-center">
          {status === "processing" && (
            <>
              <Loader2 className="w-12 h-12 text-primary-10 animate-spin mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-neutral-12 mb-2">
                Completing sign in...
              </h2>
              <p className="text-neutral-11">
                Please wait while we verify your credentials.
              </p>
            </>
          )}

          {status === "success" && (
            <>
              <CheckCircle className="w-12 h-12 text-success-10 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-neutral-12 mb-2">
                Sign in successful!
              </h2>
              <p className="text-neutral-11">
                Redirecting to Agent Studio...
              </p>
            </>
          )}

          {status === "error" && (
            <>
              <AlertCircle className="w-12 h-12 text-error-10 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-neutral-12 mb-2">
                Sign in failed
              </h2>
              <p className="text-error-10 mb-4">
                {errorMessage}
              </p>
              <Button
                variant="primary"
                onClick={() => navigate("/login", { replace: true })}
              >
                Try again
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default AuthCallbackPage;
