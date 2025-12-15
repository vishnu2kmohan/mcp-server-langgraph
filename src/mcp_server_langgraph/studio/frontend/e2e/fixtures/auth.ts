/**
 * Authentication Fixtures for E2E Tests
 *
 * Provides pre-authenticated browser contexts for different personas:
 * - admin: Full administrative access
 * - alice: Power user (developer)
 * - bob: Standard user (read-only for most resources)
 *
 * When BACKEND_ENABLED=true, uses real Keycloak authentication.
 * Otherwise, mocks authentication for frontend-only testing.
 */

import { test as base, type Page } from '@playwright/test';

// Test user credentials (from default-realm.json)
const TEST_USERS = {
  admin: {
    username: 'admin',
    password: 'admin123',
    persona: 'admin',
  },
  alice: {
    username: 'alice',
    password: 'alice123',
    persona: 'developer',
  },
  bob: {
    username: 'bob',
    password: 'bob123',
    persona: 'user',
  },
} as const;

type TestUser = keyof typeof TEST_USERS;

// Keycloak endpoints (when backend is enabled)
// Note: Keycloak is configured with http-relative-path=/authn
const KEYCLOAK_BASE = process.env.KEYCLOAK_URL || 'http://localhost:9082';
const KEYCLOAK_REALM = process.env.KEYCLOAK_REALM || 'default';
const KEYCLOAK_PATH_PREFIX = process.env.KEYCLOAK_PATH_PREFIX || '/authn';
const KEYCLOAK_TOKEN_URL = `${KEYCLOAK_BASE}${KEYCLOAK_PATH_PREFIX}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token`;
// Client credentials for mcp-server (configured in default-realm.json)
const KEYCLOAK_CLIENT_ID = process.env.KEYCLOAK_CLIENT_ID || 'mcp-server';
const KEYCLOAK_CLIENT_SECRET = process.env.KEYCLOAK_CLIENT_SECRET || 'test-client-secret-for-e2e-tests';

interface AuthFixtures {
  authenticatedPage: Page;
  adminPage: Page;
  alicePage: Page;
  bobPage: Page;
}

/**
 * Skip onboarding modal for e2e tests.
 * This is applied to all pages to ensure onboarding doesn't block interactions.
 */
async function skipOnboarding(page: Page): Promise<void> {
  await page.addInitScript(() => {
    // Skip onboarding modal for e2e tests
    localStorage.setItem('langgraph_onboarding_completed', 'true');
  });
}

/**
 * Get access token from Keycloak using Resource Owner Password Credentials grant.
 */
async function getKeycloakToken(username: string, password: string): Promise<string | null> {
  try {
    const response = await fetch(KEYCLOAK_TOKEN_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        grant_type: 'password',
        client_id: KEYCLOAK_CLIENT_ID,
        client_secret: KEYCLOAK_CLIENT_SECRET,
        username,
        password,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => 'unknown');
      console.warn(`Keycloak token fetch failed: ${response.status} - ${errorText}`);
      return null;
    }

    const data = await response.json();
    return data.access_token;
  } catch (error) {
    console.warn('Keycloak not available, using mock auth:', error);
    return null;
  }
}

/**
 * Parse JWT token to extract expiration time.
 */
function parseJwtExpiry(token: string): number {
  try {
    const base64Payload = token.split('.')[1];
    const payload = JSON.parse(atob(base64Payload));
    // exp is in seconds, convert to milliseconds
    return payload.exp * 1000;
  } catch {
    // Default to 1 hour from now if parsing fails
    return Date.now() + 60 * 60 * 1000;
  }
}

/**
 * Set up authenticated page with either real Keycloak token or mock auth.
 */
async function setupAuthenticatedPage(page: Page, user: TestUser): Promise<void> {
  // Backend is enabled by default. Set BACKEND_ENABLED=false for frontend-only testing.
  const backendEnabled = process.env.BACKEND_ENABLED !== 'false';
  const userInfo = TEST_USERS[user];

  if (backendEnabled) {
    // Try to get real Keycloak token
    const token = await getKeycloakToken(userInfo.username, userInfo.password);

    if (token) {
      // Calculate token expiry from JWT payload
      const tokenExpiry = parseJwtExpiry(token);
      // Refresh token expires in 30 days (typical)
      const refreshExpiry = Date.now() + 30 * 24 * 60 * 60 * 1000;

      // Inject token into local storage before navigation
      // Must match the format expected by:
      // - authSlice.ts (AUTH_STORAGE_KEY = 'studio-auth')
      // - api/index.ts prepareHeaders (reads 'auth_token')
      await page.addInitScript(
        ({ token, tokenExpiry, refreshExpiry, user }) => {
          // Store in the format expected by authSlice.ts
          const authState = {
            state: {
              tokens: {
                accessToken: token,
                refreshToken: token, // Use same token as placeholder
                expiresAt: tokenExpiry,
                refreshExpiresAt: refreshExpiry,
              },
            },
          };
          localStorage.setItem('studio-auth', JSON.stringify(authState));

          // CRITICAL: Also set 'auth_token' directly - this is what api/index.ts prepareHeaders reads
          localStorage.setItem('auth_token', token);

          // Also store user info for components that read it directly
          localStorage.setItem('user_info', JSON.stringify({
            username: user.username,
            persona: user.persona,
            roles: user.persona === 'admin' ? ['admin'] : user.persona === 'developer' ? ['developer'] : ['user'],
            authenticated: true,
          }));

          // Skip onboarding modal for e2e tests
          localStorage.setItem('langgraph_onboarding_completed', 'true');
        },
        { token, tokenExpiry, refreshExpiry, user: userInfo }
      );
    } else {
      // Fallback to mock auth
      await setupMockAuth(page, userInfo);
    }
  } else {
    // Mock authentication for frontend-only testing
    await setupMockAuth(page, userInfo);
  }
}

/**
 * Set up mock authentication for frontend-only testing.
 */
async function setupMockAuth(
  page: Page,
  user: { username: string; persona: string }
): Promise<void> {
  await page.addInitScript(
    ({ user }) => {
      // Create a mock token (expiry 1 hour from now)
      const now = Date.now();
      const tokenExpiry = now + 60 * 60 * 1000; // 1 hour
      const refreshExpiry = now + 30 * 24 * 60 * 60 * 1000; // 30 days

      // Store in the format expected by authSlice.ts (AUTH_STORAGE_KEY = 'studio-auth')
      const authState = {
        state: {
          tokens: {
            accessToken: 'mock-access-token',
            refreshToken: 'mock-refresh-token',
            expiresAt: tokenExpiry,
            refreshExpiresAt: refreshExpiry,
          },
        },
      };
      localStorage.setItem('studio-auth', JSON.stringify(authState));
      // CRITICAL: Also set 'auth_token' directly - this is what api/index.ts prepareHeaders reads
      localStorage.setItem('auth_token', 'mock-access-token');
      localStorage.setItem('auth_mock', 'true');

      // Store user info for components that read it directly
      localStorage.setItem('user_info', JSON.stringify({
        username: user.username,
        persona: user.persona,
        roles: user.persona === 'admin' ? ['admin'] : user.persona === 'developer' ? ['developer'] : ['user'],
        email: `${user.username}@example.com`,
        authenticated: true,
      }));

      // Skip onboarding modal for e2e tests
      localStorage.setItem('langgraph_onboarding_completed', 'true');
    },
    { user }
  );
}

/**
 * Extended test fixture with authenticated pages for each persona.
 * Also overrides the base `page` fixture to skip onboarding for all tests.
 */
export const test = base.extend<AuthFixtures & { page: Page }>({
  // Override the base page fixture to skip onboarding for ALL tests
  page: async ({ page }, use) => {
    await skipOnboarding(page);
    await use(page);
  },

  // Generic authenticated page (uses admin by default)
  authenticatedPage: async ({ page }, use) => {
    await setupAuthenticatedPage(page, 'admin');
    await use(page);
  },

  // Admin-authenticated page
  adminPage: async ({ browser }, use) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await skipOnboarding(page);
    await setupAuthenticatedPage(page, 'admin');
    await use(page);
    await context.close();
  },

  // Alice (power user) authenticated page
  alicePage: async ({ browser }, use) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await skipOnboarding(page);
    await setupAuthenticatedPage(page, 'alice');
    await use(page);
    await context.close();
  },

  // Bob (standard user) authenticated page
  bobPage: async ({ browser }, use) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await skipOnboarding(page);
    await setupAuthenticatedPage(page, 'bob');
    await use(page);
    await context.close();
  },
});

export { expect } from '@playwright/test';
export type { TestUser };
