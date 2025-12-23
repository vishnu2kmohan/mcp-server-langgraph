/**
 * Permission Denial Flows E2E Tests
 *
 * Tests that verify proper permission denial and redirect behavior:
 * - bob attempts to access /admin → redirects to chat
 * - auditor attempts to create workflow → blocked
 * - compliance-officer attempts chat → blocked
 *
 * These tests verify that the RBAC system correctly denies access
 * to unauthorized resources and provides appropriate user feedback.
 *
 * Phase 4.2: Permission denial flows
 */

import { test, expect, type Page, type BrowserContext } from "@playwright/test";

// Backend integration flag
const backendEnabled = process.env.BACKEND_ENABLED !== "false";

// =============================================================================
// Type Definitions
// =============================================================================

interface PersonaConfig {
  id: string;
  username: string;
  email: string;
  roles: string[];
  persona: string;
  defaultRoute: string;
}

// =============================================================================
// Persona Configurations with Default Routes
// =============================================================================

const PERSONAS: Record<string, PersonaConfig> = {
  admin: {
    id: "admin-user",
    username: "admin",
    email: "admin@example.com",
    roles: ["admin"],
    persona: "admin",
    defaultRoute: "/studio/admin",
  },
  auditor: {
    id: "auditor-user",
    username: "auditor",
    email: "auditor@example.com",
    roles: ["audit"],
    persona: "auditor",
    defaultRoute: "/studio/audit",
  },
  "compliance-officer": {
    id: "compliance-officer-user",
    username: "compliance-officer",
    email: "compliance@example.com",
    roles: ["compliance"],
    persona: "compliance-officer",
    defaultRoute: "/studio/compliance",
  },
  "alice-builder": {
    id: "alice-builder-user",
    username: "alice-builder",
    email: "alice-builder@example.com",
    roles: ["developer", "builder"],
    persona: "alice-builder",
    defaultRoute: "/studio/chat",
  },
  bob: {
    id: "bob-user",
    username: "bob",
    email: "bob@example.com",
    roles: ["user"],
    persona: "bob",
    defaultRoute: "/studio/chat",
  },
};

// =============================================================================
// Permission Denial Matrix
// =============================================================================

interface PermissionDenialScenario {
  persona: string;
  route: string;
  expectedRedirect: RegExp | string;
  description: string;
}

const DENIAL_SCENARIOS: PermissionDenialScenario[] = [
  // Bob denied scenarios
  {
    persona: "bob",
    route: "/studio/admin",
    expectedRedirect: /\/studio\/v2\/chat/,
    description: "bob should be redirected from admin to chat",
  },
  {
    persona: "bob",
    route: "/studio/compliance",
    expectedRedirect: /\/studio\/v2\/chat/,
    description: "bob should be redirected from compliance to chat",
  },
  {
    persona: "bob",
    route: "/studio/audit",
    expectedRedirect: /\/studio\/v2\/chat/,
    description: "bob should be redirected from audit to chat",
  },
  // Auditor denied scenarios
  {
    persona: "auditor",
    route: "/studio/admin",
    expectedRedirect: /\/studio\/v2\/(audit|chat)/,
    description: "auditor should be redirected from admin",
  },
  {
    persona: "auditor",
    route: "/studio/chat",
    expectedRedirect: /\/studio\/v2\/(audit|compliance)/,
    description: "auditor should be redirected from chat",
  },
  {
    persona: "auditor",
    route: "/studio/workflows",
    expectedRedirect: /\/studio\/v2\/(audit|compliance)/,
    description: "auditor should be redirected from workflows",
  },
  // Compliance officer denied scenarios
  {
    persona: "compliance-officer",
    route: "/studio/admin",
    expectedRedirect: /\/studio\/v2\/(compliance|chat)/,
    description: "compliance-officer should be redirected from admin",
  },
  {
    persona: "compliance-officer",
    route: "/studio/chat",
    expectedRedirect: /\/studio\/v2\/(compliance|audit)/,
    description: "compliance-officer should be redirected from chat",
  },
  // Alice-builder denied scenarios
  {
    persona: "alice-builder",
    route: "/studio/admin",
    expectedRedirect: /\/studio\/v2\/chat/,
    description: "alice-builder should be redirected from admin to chat",
  },
  {
    persona: "alice-builder",
    route: "/studio/compliance",
    expectedRedirect: /\/studio\/v2\/chat/,
    description: "alice-builder should be redirected from compliance to chat",
  },
  {
    persona: "alice-builder",
    route: "/studio/audit",
    expectedRedirect: /\/studio\/v2\/chat/,
    description: "alice-builder should be redirected from audit to chat",
  },
];

// =============================================================================
// Test Utilities
// =============================================================================

/**
 * Set up mock authentication for a specific persona
 */
async function setupPersonaMockAuth(
  page: Page,
  persona: PersonaConfig
): Promise<void> {
  await page.addInitScript(
    ({ persona }) => {
      const now = Date.now();
      const tokenExpiry = now + 60 * 60 * 1000;
      const refreshExpiry = now + 30 * 24 * 60 * 60 * 1000;

      // Store auth state
      const authState = {
        state: {
          tokens: {
            accessToken: `mock-token-${persona.id}`,
            refreshToken: `mock-refresh-${persona.id}`,
            expiresAt: tokenExpiry,
            refreshExpiresAt: refreshExpiry,
          },
        },
      };
      localStorage.setItem("studio-auth", JSON.stringify(authState));
      localStorage.setItem("auth_token", `mock-token-${persona.id}`);
      localStorage.setItem("access_token", `mock-token-${persona.id}`);
      localStorage.setItem("auth_mock", "true");

      // Store user info with persona details
      localStorage.setItem(
        "user_info",
        JSON.stringify({
          id: persona.id,
          username: persona.username,
          persona: persona.persona,
          roles: persona.roles,
          email: persona.email,
          authenticated: true,
        })
      );

      // Skip onboarding
      localStorage.setItem("langgraph_onboarding_completed", "true");
    },
    { persona }
  );
}

/**
 * Set up API mocks for permission endpoints
 */
async function setupPermissionApiMocks(
  page: Page,
  persona: PersonaConfig
): Promise<void> {
  await page.route("**/api/v1/**", async (route) => {
    const url = route.request().url();

    if (url.includes("/health")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "healthy",
          uptime_seconds: 86400,
          version: "1.0.0",
        }),
      });
      return;
    }

    if (url.includes("/me") || url.includes("/auth/me")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: persona.id,
          username: persona.username,
          email: persona.email,
          roles: persona.roles,
          persona: persona.persona,
        }),
      });
      return;
    }

    if (url.includes("/features")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          canvas_studio_shell: true,
          canvas_editable: true,
          canvas_agents: true,
          workflows: true,
          sessions: true,
          observability: true,
        }),
      });
      return;
    }

    if (url.includes("/sessions")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [
            {
              id: "session-001",
              name: "Default Session",
              created_at: new Date().toISOString(),
            },
          ],
          total: 1,
        }),
      });
      return;
    }

    // Default response for other endpoints
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], total: 0 }),
    });
  });
}

/**
 * Create an authenticated page for a specific persona
 */
async function createPersonaPage(
  context: BrowserContext,
  personaName: string
): Promise<Page> {
  const page = await context.newPage();
  const persona = PERSONAS[personaName];

  if (!persona) {
    throw new Error(`Unknown persona: ${personaName}`);
  }

  await setupPersonaMockAuth(page, persona);

  if (!backendEnabled) {
    await setupPermissionApiMocks(page, persona);
  }

  return page;
}

// =============================================================================
// Test Suites
// =============================================================================

test.describe("Permission Denial Flows", () => {
  test.describe("Bob - Standard User Permission Denial", () => {
    test("bob attempts to access /admin → redirects to chat", async ({
      browser,
    }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "bob");

      await page.goto("/studio/admin", { waitUntil: "networkidle" });

      // Should not be on admin page
      await expect(page).not.toHaveURL(/\/studio\/v2\/admin$/);

      // Should redirect to allowed route (chat or fallback)
      const currentUrl = page.url();
      expect(currentUrl).not.toContain("/admin");

      await context.close();
    });

    test("bob attempts to access /compliance → blocked", async ({
      browser,
    }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "bob");

      await page.goto("/studio/compliance", { waitUntil: "networkidle" });

      // Should redirect away or show access denied
      const hasRedirected = !(await page
        .url()
        .includes("/studio/compliance"));
      const hasAccessDenied = await page
        .locator("body")
        .textContent()
        .then((text) => text?.includes("Access Denied") ?? false)
        .catch(() => false);

      expect(hasRedirected || hasAccessDenied).toBe(true);

      await context.close();
    });

    test("bob attempts to access /audit → blocked", async ({ browser }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "bob");

      await page.goto("/studio/audit", { waitUntil: "networkidle" });

      // Should redirect away or show access denied
      const hasRedirected = !page.url().includes("/studio/audit");
      const hasAccessDenied = await page
        .locator("body")
        .textContent()
        .then((text) => text?.includes("Access Denied") ?? false)
        .catch(() => false);

      expect(hasRedirected || hasAccessDenied).toBe(true);

      await context.close();
    });
  });

  test.describe("Auditor - Read-Only Permission Denial", () => {
    test("auditor attempts to access /admin → blocked", async ({ browser }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "auditor");

      await page.goto("/studio/admin", { waitUntil: "networkidle" });

      // Should not be on admin page
      await expect(page).not.toHaveURL(/\/studio\/v2\/admin$/);

      await context.close();
    });

    test("auditor attempts to access /chat → blocked", async ({ browser }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "auditor");

      await page.goto("/studio/chat", { waitUntil: "networkidle" });

      // Auditor should be redirected from chat to audit/compliance
      const currentUrl = page.url();
      // Either redirected away from chat or access denied
      const hasRedirected = !currentUrl.includes("/studio/chat");
      const hasAccessDenied = await page
        .locator("body")
        .textContent()
        .then((text) => text?.includes("Access Denied") ?? false)
        .catch(() => false);

      expect(hasRedirected || hasAccessDenied).toBe(true);

      await context.close();
    });

    test("auditor attempts to create workflow → blocked", async ({
      browser,
    }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "auditor");

      await page.goto("/studio/workflows", { waitUntil: "networkidle" });

      // Auditor should not access workflow page
      const hasRedirected = !page.url().includes("/studio/workflows");
      const hasAccessDenied = await page
        .locator("body")
        .textContent()
        .then((text) => text?.includes("Access Denied") ?? false)
        .catch(() => false);

      expect(hasRedirected || hasAccessDenied).toBe(true);

      await context.close();
    });

    test("auditor can access audit page", async ({ browser }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "auditor");

      await page.goto("/studio/audit", { waitUntil: "networkidle" });

      // Should be on audit page
      await expect(page).toHaveURL(/\/studio\/v2\/audit/);
      await expect(page.locator("body")).not.toContainText("Access Denied");

      await context.close();
    });
  });

  test.describe("Compliance Officer - Compliance-Only Permission Denial", () => {
    test("compliance-officer attempts to access /admin → blocked", async ({
      browser,
    }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "compliance-officer");

      await page.goto("/studio/admin", { waitUntil: "networkidle" });

      // Should not be on admin page
      await expect(page).not.toHaveURL(/\/studio\/v2\/admin$/);

      await context.close();
    });

    test("compliance-officer attempts /chat → blocked", async ({ browser }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "compliance-officer");

      await page.goto("/studio/chat", { waitUntil: "networkidle" });

      // Compliance officer should be redirected from chat
      const hasRedirected = !page.url().includes("/studio/chat");
      const hasAccessDenied = await page
        .locator("body")
        .textContent()
        .then((text) => text?.includes("Access Denied") ?? false)
        .catch(() => false);

      expect(hasRedirected || hasAccessDenied).toBe(true);

      await context.close();
    });

    test("compliance-officer can access compliance page", async ({
      browser,
    }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "compliance-officer");

      await page.goto("/studio/compliance", { waitUntil: "networkidle" });

      // Should be on compliance page
      await expect(page).toHaveURL(/\/studio\/v2\/compliance/);
      await expect(page.locator("body")).not.toContainText("Access Denied");

      await context.close();
    });
  });

  test.describe("Alice Builder - Developer Permission Denial", () => {
    test("alice-builder attempts to access /admin → blocked", async ({
      browser,
    }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "alice-builder");

      await page.goto("/studio/admin", { waitUntil: "networkidle" });

      // Should not be on admin page
      await expect(page).not.toHaveURL(/\/studio\/v2\/admin$/);

      await context.close();
    });

    test("alice-builder attempts /compliance → blocked", async ({
      browser,
    }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "alice-builder");

      await page.goto("/studio/compliance", { waitUntil: "networkidle" });

      // Should redirect away or show access denied
      const hasRedirected = !page.url().includes("/studio/compliance");
      const hasAccessDenied = await page
        .locator("body")
        .textContent()
        .then((text) => text?.includes("Access Denied") ?? false)
        .catch(() => false);

      expect(hasRedirected || hasAccessDenied).toBe(true);

      await context.close();
    });

    test("alice-builder attempts /audit → blocked", async ({ browser }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "alice-builder");

      await page.goto("/studio/audit", { waitUntil: "networkidle" });

      // Should redirect away or show access denied
      const hasRedirected = !page.url().includes("/studio/audit");
      const hasAccessDenied = await page
        .locator("body")
        .textContent()
        .then((text) => text?.includes("Access Denied") ?? false)
        .catch(() => false);

      expect(hasRedirected || hasAccessDenied).toBe(true);

      await context.close();
    });

    test("alice-builder can access chat page", async ({ browser }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "alice-builder");

      await page.goto("/studio/chat", { waitUntil: "networkidle" });

      // Should be on chat page
      await expect(page).toHaveURL(/\/studio\/v2\/chat/);
      await expect(page.locator("body")).not.toContainText("Access Denied");

      await context.close();
    });
  });
});

test.describe("Navigation Visibility for Denied Routes", () => {
  test("bob should not see admin navigation item", async ({ browser }) => {
    const context = await browser.newContext();
    const page = await createPersonaPage(context, "bob");

    await page.goto("/studio/chat", { waitUntil: "networkidle" });

    // Wait for activity bar to load
    await page.waitForTimeout(1000);

    // Admin nav should not be visible to bob
    await expect(page.getByTestId("nav-admin")).not.toBeVisible();

    await context.close();
  });

  test("auditor should not see chat navigation item", async ({ browser }) => {
    const context = await browser.newContext();
    const page = await createPersonaPage(context, "auditor");

    await page.goto("/studio/audit", { waitUntil: "networkidle" });

    // Wait for activity bar to load
    await page.waitForTimeout(1000);

    // Chat nav should not be visible to auditor
    await expect(page.getByTestId("nav-chat")).not.toBeVisible();

    await context.close();
  });

  test("compliance-officer should not see workflow navigation item", async ({
    browser,
  }) => {
    const context = await browser.newContext();
    const page = await createPersonaPage(context, "compliance-officer");

    await page.goto("/studio/compliance", { waitUntil: "networkidle" });

    // Wait for activity bar to load
    await page.waitForTimeout(1000);

    // Workflows nav should not be visible to compliance officer
    await expect(page.getByTestId("nav-flows")).not.toBeVisible();

    await context.close();
  });
});

test.describe("Graceful Denial - User Experience", () => {
  test("denied access should not show error page crash", async ({
    browser,
  }) => {
    const context = await browser.newContext();
    const page = await createPersonaPage(context, "bob");

    await page.goto("/studio/admin", { waitUntil: "networkidle" });

    // Should not show error boundary crash
    await expect(page.locator("body")).not.toContainText(
      "Something went wrong"
    );
    await expect(page.locator("body")).not.toContainText("Error boundary");

    await context.close();
  });

  test("denied access should redirect to allowed route", async ({
    browser,
  }) => {
    const context = await browser.newContext();
    const page = await createPersonaPage(context, "bob");

    await page.goto("/studio/admin", { waitUntil: "networkidle" });

    // Should be on an allowed route (not admin)
    const currentUrl = page.url();
    expect(currentUrl).not.toContain("/admin");

    // Page should be functional
    await expect(page.locator("body")).toBeVisible();

    await context.close();
  });
});
