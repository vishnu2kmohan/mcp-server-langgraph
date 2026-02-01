/**
 * LoginPage
 *
 * Native login page for the Studio application.
 *
 * Authentication: OAuth2 Authorization Code + PKCE flow (ADR-0071, RFC 9700)
 *
 * Features:
 * - Generic SSO button that redirects to Keycloak for authentication
 * - Dynamic SSO Identity Provider buttons fetched from Keycloak
 * - Each IdP button uses kc_idp_hint for direct provider redirect
 *
 * Per RFC 9700: ROPC MUST NOT be used. Use Authorization Code + PKCE instead.
 */

import { useEffect } from "react";
import { useNavigate, useLocation } from "react-router";
import { ExternalLink, Key, Shield, LogIn, Loader2 } from "lucide-react";
import { useGetIdentityProvidersQuery } from "../api";
import { useAppSelector } from "../store/hooks";
import { selectIsAuthenticated } from "../store/slices/authSlice";
import { setIntendedRoute } from "../utils/intendedRoute";
import { getDisplayVersion } from "../config/version";

// Import icon as module for proper Vite path resolution with base: '/studio/'
import iconSvg from "/icons/icon.svg";

// Provider icon mapping - returns appropriate Lucide icon or SVG for known providers
function getProviderIcon(icon: string) {
  switch (icon) {
    case "google":
      return (
        <svg className="w-5 h-5" viewBox="0 0 24 24">
          <path
            fill="currentColor"
            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
          />
          <path
            fill="currentColor"
            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
          />
          <path
            fill="currentColor"
            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
          />
          <path
            fill="currentColor"
            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
          />
        </svg>
      );
    case "github":
      return (
        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
        </svg>
      );
    case "microsoft":
      return (
        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M11.4 24H0V12.6h11.4V24zM24 24H12.6V12.6H24V24zM11.4 11.4H0V0h11.4v11.4zm12.6 0H12.6V0H24v11.4z" />
        </svg>
      );
    case "facebook":
      return (
        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
        </svg>
      );
    case "linkedin":
      return (
        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
        </svg>
      );
    case "apple":
      return (
        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z" />
        </svg>
      );
    case "key":
      return <Key className="w-5 h-5" />;
    case "shield":
      return <Shield className="w-5 h-5" />;
    default:
      return <ExternalLink className="w-5 h-5" />;
  }
}

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);

  // Fetch SSO identity providers from Keycloak
  const { data: idpData, isLoading: idpLoading } =
    useGetIdentityProvidersQuery();

  // Save intended route from AuthGuard's location state
  // This persists the route before OAuth redirect to external IdP
  useEffect(() => {
    // AuthGuard passes the protected route as state.from
    const from = (
      location.state as {
        from?: { pathname: string; search?: string; hash?: string };
      }
    )?.from;
    if (from?.pathname) {
      // Build the full route including query string and hash
      const fullRoute = `${from.pathname}${from.search || ""}${from.hash || ""}`;
      setIntendedRoute(fullRoute);
    }
  }, [location.state]);

  // Redirect to studio if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate("/studio", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  // Force dark mode on login page
  // This ensures consistent branding regardless of user's theme preference
  useEffect(() => {
    const htmlElement = document.documentElement;
    const wasDark = htmlElement.classList.contains("dark");

    // Force dark mode
    htmlElement.classList.add("dark");

    // Restore original theme on unmount
    return () => {
      if (!wasDark) {
        htmlElement.classList.remove("dark");
      }
    };
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-gradient-to-br from-neutral-1 to-neutral-2">
      <div className="w-full max-w-md">
        {/* Logo and Title */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl shadow-lg mb-4 overflow-hidden">
            <img src={iconSvg} alt="Agent Studio" className="w-16 h-16" />
          </div>
          <h1 className="text-2xl font-bold text-neutral-12 leading-tight">
            Agent Studio
          </h1>
          <p className="mt-2 text-sm text-neutral-11">Sign in to continue</p>
        </div>

        {/* Login Card - Minimal/borderless design */}
        <div className="rounded-2xl shadow-xl p-8 backdrop-blur-sm bg-neutral-2">
          {/* Loading state */}
          {idpLoading && (
            <div className="flex items-center justify-center py-8">
              <Loader2
                className="h-8 w-8 animate-spin text-primary-9"
                role="status"
                aria-label="Loading identity providers"
              />
            </div>
          )}

          {/* Main SSO Login Button (OAuth2 + PKCE) */}
          {!idpLoading && (
            <>
              {/* Only add bottom margin if IdP providers follow */}
              <div
                className={
                  idpData && (idpData.identity_providers?.length ?? 0) > 0
                    ? "mb-6"
                    : ""
                }
              >
                <a
                  href="/api/v1/auth/login"
                  className="w-full flex items-center justify-center gap-3 py-3 px-4 bg-primary-9 text-white font-semibold rounded-lg hover:bg-primary-10 focus:outline-none focus:ring-2 focus:ring-primary-7 focus:ring-offset-2 transition-colors"
                >
                  <LogIn className="h-5 w-5" />
                  Sign in with SSO
                </a>
                <p className="text-xs text-center mt-2 text-neutral-11">
                  Secure OAuth2 + PKCE authentication
                </p>
              </div>

              {/* SSO Identity Providers Section */}
              {idpData && (idpData.identity_providers?.length ?? 0) > 0 && (
                <>
                  {/* Divider */}
                  <div className="relative mb-6">
                    <div className="absolute inset-0 flex items-center">
                      <div className="w-full border-t border-neutral-5" />
                    </div>
                    <div className="relative flex justify-center text-sm">
                      <span className="px-2 bg-neutral-2 text-neutral-11">
                        or continue with
                      </span>
                    </div>
                  </div>

                  {/* IdP Buttons */}
                  <div className="space-y-3">
                    {idpData.identity_providers?.map((provider) => (
                      <a
                        key={provider.alias}
                        href={provider.login_url}
                        className="w-full flex items-center justify-center gap-3 py-3 px-4 rounded-lg text-neutral-12 font-medium transition-colors bg-neutral-3 hover:bg-neutral-4"
                      >
                        {getProviderIcon(provider.icon)}
                        <span>{provider.display_name}</span>
                      </a>
                    ))}
                  </div>
                </>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <p className="text-center text-xs mt-6 text-neutral-11 opacity-60">
          Agent Studio {getDisplayVersion()}
        </p>
      </div>
    </div>
  );
}

export default LoginPage;
