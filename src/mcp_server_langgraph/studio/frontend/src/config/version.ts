/**
 * Application and Protocol Version Configuration
 *
 * Tracks the version from package.json and GitHub releases.
 * The version is injected at build time via Vite's define plugin.
 *
 * Version format follows semver:
 * - Released versions: "2.8.0"
 * - Development versions: "2.9.0-dev"
 * - Pre-release versions: "2.9.0-alpha.1", "2.9.0-beta.1", "2.9.0-rc.1"
 *
 * Protocol Version:
 * - Tracks WebSocket protocol compatibility between frontend and backend
 * - Major version changes indicate breaking protocol changes
 * - Minor version changes are backwards compatible
 * - See: ADR-0076 WebSocket Protocol Versioning
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

// =============================================================================
// Protocol Version (WebSocket Compatibility)
// =============================================================================

/**
 * WebSocket protocol version for client-server compatibility checking.
 *
 * This version tracks the WebSocket message format compatibility:
 * - Major: Breaking changes (message format changes, removed fields)
 * - Minor: Backwards-compatible additions (new message types, optional fields)
 * - Patch: Bug fixes only (no protocol changes)
 *
 * When updating:
 * - Bump major for breaking changes (requires coordinated frontend+backend deploy)
 * - Bump minor for new features (server can support older clients)
 * - Bump patch for bug fixes (no compatibility impact)
 *
 * @see ADR-0076 WebSocket Protocol Versioning
 */
export const PROTOCOL_VERSION = "1.0.0";

/**
 * Parse a semantic version string into components.
 *
 * @param version - Version string like "1.0.0"
 * @returns Tuple of [major, minor, patch] or null if invalid
 */
export function parseSemanticVersion(
  version: string,
): [number, number, number] | null {
  if (!version || typeof version !== "string") {
    return null;
  }

  const parts = version.split(".");
  if (parts.length !== 3) {
    return null;
  }

  const [major, minor, patch] = parts.map(Number);
  if (isNaN(major) || isNaN(minor) || isNaN(patch)) {
    return null;
  }

  return [major, minor, patch];
}

/**
 * Check if a client protocol version is compatible with a server version.
 *
 * Compatibility rules (following semver):
 * - Major version must match exactly (breaking changes)
 * - Minor version: server >= client (backwards compatible features)
 * - Patch version: any (bug fixes only)
 *
 * @param clientVersion - Client's protocol version
 * @param serverVersion - Server's protocol version (defaults to PROTOCOL_VERSION)
 * @returns true if versions are compatible
 *
 * @example
 * ```typescript
 * isProtocolVersionCompatible("1.0.0", "1.0.0") // true
 * isProtocolVersionCompatible("1.0.0", "1.1.0") // true (server has newer features)
 * isProtocolVersionCompatible("1.1.0", "1.0.0") // false (client needs newer server)
 * isProtocolVersionCompatible("2.0.0", "1.0.0") // false (major version mismatch)
 * ```
 */
export function isProtocolVersionCompatible(
  clientVersion: string,
  serverVersion: string = PROTOCOL_VERSION,
): boolean {
  const client = parseSemanticVersion(clientVersion);
  const server = parseSemanticVersion(serverVersion);

  if (!client || !server) {
    return false;
  }

  const [clientMajor, clientMinor] = client;
  const [serverMajor, serverMinor] = server;

  // Major version must match exactly
  if (clientMajor !== serverMajor) {
    return false;
  }

  // Client can't require features from a newer server
  if (clientMinor > serverMinor) {
    return false;
  }

  return true;
}
