/**
 * Authentication Fixtures for E2E Tests
 *
 * Provides pre-authenticated browser contexts for different personas:
 * - admin: Full administrative access
 * - alice: Power user (developer)
 * - bob: Standard user (read-only for most resources)
 *
 * Uses OAuth2 Authorization Code + PKCE flow per RFC 9700 (RFC 7636).
 * ROPC (Resource Owner Password Credentials) is NOT used per security best practices.
 */

import { test as base, type Page, type BrowserContext } from '@playwright/test';

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

// Base URL for the application (Traefik gateway)
const APP_BASE_URL = process.env.BASE_URL || 'http://localhost';

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
 * Authenticate via browser PKCE flow.
 *
 * Flow:
 * 1. Navigate to /api/v1/auth/login (initiates PKCE)
 * 2. Get redirected to Keycloak login page
 * 3. Fill in credentials
 * 4. Get redirected to /api/v1/auth/callback (token exchange)
 * 5. Get redirected to /auth/callback#access_token=...
 * 6. AuthCallbackPage stores tokens in localStorage
 * 7. Get redirected to /studio
 */
async function authenticateViaBrowserPKCE(
  page: Page,
  user: { username: string; password: string },
  options: { timeout?: number } = {}
): Promise<boolean> {
  const timeout = options.timeout ?? 30000;

  try {
    // Navigate to login endpoint which redirects to Keycloak
    await page.goto(`${APP_BASE_URL}/api/v1/auth/login`, {
      waitUntil: 'networkidle',
      timeout,
    });

    // Wait for Keycloak login form
    // The page should now be at Keycloak (e.g., http://localhost/authn/realms/default/...)
    const usernameInput = page.locator('#username');
    const passwordInput = page.locator('#password');
    const loginButton = page.locator('#kc-login');

    // Wait for the form to be visible
    await usernameInput.waitFor({ state: 'visible', timeout });

    // Fill in credentials
    await usernameInput.fill(user.username);
    await passwordInput.fill(user.password);

    // Submit login form
    await loginButton.click();

    // Wait for redirect back to application
    // After successful login, we should end up at /studio
    await page.waitForURL(`${APP_BASE_URL}/studio/**`, { timeout });

    // Verify token is stored in localStorage
    // Check for 'access_token' (new OAuth2 PKCE flow) or 'auth_token' (legacy)
    const token = await page.evaluate(() =>
      localStorage.getItem('access_token') || localStorage.getItem('auth_token')
    );
    if (!token) {
      console.warn('Token not found in localStorage after PKCE flow');
      return false;
    }

    return true;
  } catch (error) {
    console.warn(`Browser PKCE authentication failed for ${user.username}:`, error);
    return false;
  }
}

/**
 * Set up mock authentication for frontend-only testing.
 * Used when backend is unavailable or BACKEND_ENABLED=false.
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
      localStorage.setItem('access_token', 'mock-access-token');
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
 * Set up authenticated page with browser PKCE flow or mock auth fallback.
 */
async function setupAuthenticatedPage(
  context: BrowserContext,
  user: TestUser
): Promise<Page> {
  const page = await context.newPage();
  await skipOnboarding(page);

  // Check if backend is enabled
  const backendEnabled = process.env.BACKEND_ENABLED !== 'false';
  const userInfo = TEST_USERS[user];

  if (backendEnabled) {
    // Try browser-based PKCE authentication
    const success = await authenticateViaBrowserPKCE(page, userInfo);

    if (!success) {
      console.warn(`PKCE auth failed for ${user}, falling back to mock auth`);
      // Close the failed page and create a new one with mock auth
      await page.close();
      const newPage = await context.newPage();
      await skipOnboarding(newPage);
      await setupMockAuth(newPage, userInfo);
      await newPage.goto(`${APP_BASE_URL}/studio`, { waitUntil: 'networkidle' });
      return newPage;
    }
  } else {
    // Mock authentication for frontend-only testing
    await setupMockAuth(page, userInfo);
    await page.goto(`${APP_BASE_URL}/studio`, { waitUntil: 'networkidle' });
  }

  return page;
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
  authenticatedPage: async ({ browser }, use) => {
    const context = await browser.newContext();
    const page = await setupAuthenticatedPage(context, 'admin');
    await use(page);
    await context.close();
  },

  // Admin-authenticated page
  adminPage: async ({ browser }, use) => {
    const context = await browser.newContext();
    const page = await setupAuthenticatedPage(context, 'admin');
    await use(page);
    await context.close();
  },

  // Alice (power user) authenticated page
  alicePage: async ({ browser }, use) => {
    const context = await browser.newContext();
    const page = await setupAuthenticatedPage(context, 'alice');
    await use(page);
    await context.close();
  },

  // Bob (standard user) authenticated page
  bobPage: async ({ browser }, use) => {
    const context = await browser.newContext();
    const page = await setupAuthenticatedPage(context, 'bob');
    await use(page);
    await context.close();
  },
});

export { expect } from '@playwright/test';
export type { TestUser };
