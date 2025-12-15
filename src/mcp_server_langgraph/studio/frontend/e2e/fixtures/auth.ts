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
    password: 'admin-password',
    persona: 'admin',
  },
  alice: {
    username: 'alice',
    password: 'alice-password',
    persona: 'developer',
  },
  bob: {
    username: 'bob',
    password: 'bob-password',
    persona: 'user',
  },
} as const;

type TestUser = keyof typeof TEST_USERS;

// Keycloak endpoints (when backend is enabled)
const KEYCLOAK_BASE = process.env.KEYCLOAK_URL || 'http://localhost:9082';
const KEYCLOAK_REALM = process.env.KEYCLOAK_REALM || 'default';
const KEYCLOAK_TOKEN_URL = `${KEYCLOAK_BASE}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token`;

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
        client_id: 'studio-frontend',
        username,
        password,
      }),
    });

    if (!response.ok) {
      console.warn(`Keycloak token fetch failed: ${response.status}`);
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
      // Inject token into local storage before navigation
      await page.addInitScript(
        ({ token, user }) => {
          localStorage.setItem('auth_token', token);
          localStorage.setItem('user_info', JSON.stringify({
            username: user.username,
            persona: user.persona,
            authenticated: true,
          }));
          // Skip onboarding modal for e2e tests
          localStorage.setItem('langgraph_onboarding_completed', 'true');
        },
        { token, user: userInfo }
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
      // Mock auth state in Redux store (via localStorage)
      localStorage.setItem('auth_mock', 'true');
      localStorage.setItem('user_info', JSON.stringify({
        username: user.username,
        persona: user.persona,
        email: `${user.username}@example.com`,
        authenticated: true,
      }));
      // Mock persona for RBAC
      localStorage.setItem('persona', user.persona);
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
