/**
 * Application Version Configuration
 *
 * Tracks the version from package.json and GitHub releases.
 * The version is injected at build time via Vite's define plugin.
 *
 * Version format follows semver:
 * - Released versions: "2.8.0"
 * - Development versions: "2.9.0-dev"
 * - Pre-release versions: "2.9.0-alpha.1", "2.9.0-beta.1", "2.9.0-rc.1"
 */

// Version is injected by Vite at build time from package.json
// Fallback to development version if not available (e.g., in tests)
export const APP_VERSION =
  typeof __APP_VERSION__ !== "undefined" ? __APP_VERSION__ : "2.9.0-dev";

// Build timestamp (ISO format) - useful for debugging
export const BUILD_TIMESTAMP =
  typeof __BUILD_TIMESTAMP__ !== "undefined" ? __BUILD_TIMESTAMP__ : null;

// Whether this is a development build
export const IS_DEV = APP_VERSION.includes("-dev");

// Whether this is a pre-release (alpha, beta, rc)
export const IS_PRERELEASE =
  APP_VERSION.includes("-alpha") ||
  APP_VERSION.includes("-beta") ||
  APP_VERSION.includes("-rc");

/**
 * Get formatted version string for display
 * Returns version with optional "v" prefix
 */
export function getDisplayVersion(includePrefix = true): string {
  return includePrefix ? `v${APP_VERSION}` : APP_VERSION;
}

// Type declarations for Vite-injected globals
declare global {
  const __APP_VERSION__: string | undefined;
  const __BUILD_TIMESTAMP__: string | undefined;
}
