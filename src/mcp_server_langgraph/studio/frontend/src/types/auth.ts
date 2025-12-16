/**
 * Authentication and Authorization Types
 *
 * Defines types for user authentication, personas, and JWT claims.
 */

/**
 * User persona determines default dashboard and available features.
 * Derived from JWT claims and role membership.
 */
export type Persona = "admin" | "developer" | "user";

/**
 * Organization role within a specific organization.
 */
export type OrganizationRole = "admin" | "member" | "viewer";

/**
 * User representation from authentication provider.
 */
export interface User {
  /** Unique user identifier (UUID) */
  id: string;
  /** Username for display */
  username: string;
  /** Email address */
  email: string;
  /** First name from Keycloak (given_name claim) */
  firstName?: string;
  /** Last name from Keycloak (family_name claim) */
  lastName?: string;
  /** Display name (full name from Keycloak name claim) */
  displayName?: string;
  /** User's roles from realm/client */
  roles: string[];
  /** Derived persona for UI customization */
  persona: Persona;
  /** Avatar URL (optional) */
  avatarUrl?: string;
}

/**
 * Organization/Tenant information.
 */
export interface Organization {
  /** Organization UUID */
  id: string;
  /** Organization display name */
  name: string;
  /** User's role within this organization */
  role: OrganizationRole;
  /** Organization tier for feature gating */
  tier: "shared" | "hybrid" | "dedicated";
}

/**
 * JWT claims extracted from access token.
 * Based on Keycloak token structure with custom claims.
 */
export interface JWTClaims {
  /** Subject (user ID) */
  sub: string;
  /** Email address */
  email: string;
  /** Preferred username */
  preferred_username: string;
  /** Display name */
  name?: string;
  /** Current organization ID (custom claim) */
  org_id?: string;
  /** Organization role (custom claim) */
  org_role?: OrganizationRole;
  /** Derived persona (custom claim) */
  persona?: Persona;
  /** Realm access roles */
  realm_access?: {
    roles: string[];
  };
  /** Resource access roles */
  resource_access?: Record<
    string,
    {
      roles: string[];
    }
  >;
  /** Token expiration timestamp */
  exp: number;
  /** Token issued at timestamp */
  iat: number;
}

/**
 * Authentication tokens from login or refresh.
 */
export interface AuthTokens {
  /** JWT access token */
  accessToken: string;
  /** Refresh token for obtaining new access tokens */
  refreshToken: string;
  /** Access token expiration timestamp (ms) */
  expiresAt: number;
  /** Refresh token expiration timestamp (ms) */
  refreshExpiresAt: number;
}

/**
 * Authentication state stored in authStore.
 */
export interface AuthState {
  /** Current authenticated user (null if not logged in) */
  user: User | null;
  /** Authentication tokens */
  tokens: AuthTokens | null;
  /** Current organization context */
  currentOrg: Organization | null;
  /** Available organizations for the user */
  organizations: Organization[];
  /** Whether authentication is being initialized */
  isInitializing: boolean;
  /** Whether a login attempt is in progress */
  isLoading: boolean;
  /** Last authentication error */
  error: string | null;
}

/**
 * Authentication store actions.
 */
export interface AuthActions {
  /** Initialize auth state from stored tokens */
  initialize: () => Promise<void>;
  /** Login with username and password */
  login: (username: string, password: string) => Promise<void>;
  /** Logout and clear all auth state */
  logout: () => void;
  /** Refresh access token using refresh token */
  refreshToken: () => Promise<void>;
  /** Switch to a different organization */
  switchOrganization: (orgId: string) => Promise<void>;
  /** Clear any authentication errors */
  clearError: () => void;
  /** Get current access token (refreshing if needed) */
  getAccessToken: () => Promise<string | null>;
}

/**
 * Complete auth store type (state + actions).
 */
export type AuthStore = AuthState & AuthActions;
