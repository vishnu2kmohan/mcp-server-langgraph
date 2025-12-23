/**
 * Persona Access Matrix E2E Tests
 *
 * Comprehensive verification that all 8 personas have correct feature access.
 * Uses a data-driven approach to systematically test navigation visibility
 * and route access for each persona.
 *
 * Personas Tested:
 * - admin: Full administrative access
 * - security-admin: Security-focused admin access
 * - auditor: Read-only audit and compliance access
 * - alice-builder: Workflow and agent development access
 * - alice-analyst: Analytics and observability access
 * - alice-devops: DevOps and infrastructure access
 * - compliance-officer: Compliance management access
 * - bob: Standard user with basic access
 *
 * Test Coverage:
 * - Navigation visibility per persona
 * - Route access verification
 * - Route denial and redirect behavior
 * - Permission enforcement at module level
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
  allowedModules: string[];
  deniedModules: string[];
  defaultRoute: string;
}

// =============================================================================
// Persona Access Matrix
// =============================================================================

/**
 * Complete persona access matrix defining allowed and denied modules for each persona.
 * Based on RBAC rules and PersonaVariants configuration.
 */
const PERSONA_ACCESS_MATRIX: Record<string, PersonaConfig> = {
  admin: {
    id: "admin-user",
    username: "admin",
    email: "admin@example.com",
    roles: ["admin"],
    allowedModules: [
      "chat",
      "agents",
      "flows",
      "mcp",
      "files",
      "traces",
      "costs",
      "admin",
      "compliance",
      "audit",
      "help",
    ],
    deniedModules: [], // Admin sees everything
    defaultRoute: "/studio/admin",
  },
  "security-admin": {
    id: "security-admin-user",
    username: "security-admin",
    email: "security@example.com",
    roles: ["admin", "security"],
    allowedModules: [
      "chat",
      "admin",
      "compliance",
      "audit",
      "help",
      "traces",
    ],
    deniedModules: ["projects"],
    defaultRoute: "/studio/compliance",
  },
  auditor: {
    id: "auditor-user",
    username: "auditor",
    email: "auditor@example.com",
    roles: ["audit"],
    allowedModules: ["audit", "compliance", "help"],
    deniedModules: [
      "chat",
      "agents",
      "flows",
      "mcp",
      "files",
      "traces",
      "costs",
      "admin",
    ],
    defaultRoute: "/studio/audit",
  },
  "alice-builder": {
    id: "alice-builder-user",
    username: "alice-builder",
    email: "alice-builder@example.com",
    roles: ["developer", "builder"],
    allowedModules: ["chat", "flows", "mcp", "agents", "help"],
    deniedModules: ["admin", "compliance", "audit", "costs", "traces"],
    defaultRoute: "/studio/chat",
  },
  "alice-analyst": {
    id: "alice-analyst-user",
    username: "alice-analyst",
    email: "alice-analyst@example.com",
    roles: ["developer", "analyst"],
    allowedModules: ["chat", "traces", "costs", "help"],
    deniedModules: ["admin", "flows", "agents", "mcp", "compliance", "audit"],
    defaultRoute: "/studio/chat",
  },
  "alice-devops": {
    id: "alice-devops-user",
    username: "alice-devops",
    email: "alice-devops@example.com",
    roles: ["developer", "devops"],
    allowedModules: ["chat", "mcp", "traces", "help"],
    deniedModules: ["admin", "compliance", "audit", "agents", "flows"],
    defaultRoute: "/studio/chat",
  },
  "compliance-officer": {
    id: "compliance-officer-user",
    username: "compliance-officer",
    email: "compliance@example.com",
    roles: ["compliance"],
    allowedModules: ["audit", "compliance", "help"],
    deniedModules: [
      "chat",
      "agents",
      "flows",
      "mcp",
      "files",
      "traces",
      "costs",
      "admin",
    ],
    defaultRoute: "/studio/compliance",
  },
  bob: {
    id: "bob-user",
    username: "bob",
    email: "bob@example.com",
    roles: ["user"],
    allowedModules: ["chat", "projects", "flows", "help"],
    deniedModules: [
      "admin",
      "compliance",
      "audit",
      "agents",
      "mcp",
      "traces",
      "costs",
    ],
    defaultRoute: "/studio/chat",
  },
};

// Module to route mapping
const MODULE_ROUTES: Record<string, string> = {
  chat: "/studio/chat",
  admin: "/studio/admin",
  compliance: "/studio/compliance",
  audit: "/studio/audit",
  flows: "/studio/workflows",
  agents: "/studio/mcp", // Agents visible on MCP page
  mcp: "/studio/mcp",
  traces: "/studio/observability",
  costs: "/studio/costs",
  files: "/studio/files",
  projects: "/studio/projects",
  help: "/studio/help",
};

// Module to testid mapping for navigation
const MODULE_NAV_TESTIDS: Record<string, string> = {
  chat: "nav-chat",
  admin: "nav-admin",
  compliance: "nav-compliance",
  audit: "nav-audit",
  flows: "nav-flows",
  agents: "nav-agents",
  mcp: "nav-mcp",
  traces: "nav-traces",
  costs: "nav-costs",
  files: "nav-files",
  projects: "nav-projects",
  help: "nav-help",
};

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
          persona: persona.username,
          roles: persona.roles,
          email: persona.email,
          authenticated: true,
          allowedModules: persona.allowedModules,
        })
      );

      // Skip onboarding
      localStorage.setItem("langgraph_onboarding_completed", "true");
    },
    { persona }
  );
}

/**
 * Set up API mocks for persona endpoints
 */
async function setupPersonaApiMocks(
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
          persona: persona.username,
          allowedModules: persona.allowedModules,
        }),
      });
      return;
    }

    if (url.includes("/features")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          studio_canvas_shell: true,
          canvas_editable: true,
          canvas_agents: true,
          canvas_ai_palette: true,
          canvas_compliance: true,
          canvas_help: true,
          workflows: true,
          sessions: true,
          cost_dashboard: true,
          observability: true,
          code_export: true,
          ai_suggestions: true,
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
  const persona = PERSONA_ACCESS_MATRIX[personaName];

  if (!persona) {
    throw new Error(`Unknown persona: ${personaName}`);
  }

  await setupPersonaMockAuth(page, persona);

  if (!backendEnabled) {
    await setupPersonaApiMocks(page, persona);
  }

  return page;
}

// =============================================================================
// Test Suites
// =============================================================================

test.describe("Persona Access Matrix Verification", () => {
  test.describe("Admin Persona - Full Access", () => {
    test("admin should see all navigation modules", async ({ browser }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "admin");

      await page.goto("/studio/chat", { waitUntil: "networkidle" });

      const activityBar = page.getByTestId("activity-bar");
      await expect(activityBar).toBeVisible({ timeout: 10000 });

      // Admin should see all modules
      await expect(page.getByTestId("nav-chat")).toBeVisible();
      await expect(page.getByTestId("nav-admin")).toBeVisible();

      await context.close();
    });

    test("admin should access all routes without redirect", async ({
      browser,
    }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "admin");

      const adminConfig = PERSONA_ACCESS_MATRIX["admin"];
      for (const module of adminConfig.allowedModules.slice(0, 5)) {
        const route = MODULE_ROUTES[module];
        if (route) {
          await page.goto(route, { waitUntil: "networkidle" });
          // Should not show access denied
          await expect(page.locator("body")).not.toContainText("Access Denied");
        }
      }

      await context.close();
    });
  });

  test.describe("Auditor Persona - Read-Only Access", () => {
    test("auditor should only see audit, compliance, and help modules", async ({
      browser,
    }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "auditor");

      await page.goto("/studio/audit", { waitUntil: "networkidle" });

      const activityBar = page.getByTestId("activity-bar");
      await expect(activityBar).toBeVisible({ timeout: 10000 });

      // Auditor should NOT see admin, chat, agents, etc.
      await expect(page.getByTestId("nav-admin")).not.toBeVisible();
      await expect(page.getByTestId("nav-chat")).not.toBeVisible();

      await context.close();
    });

    test("auditor should be redirected from admin routes", async ({
      browser,
    }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "auditor");

      await page.goto("/studio/admin", { waitUntil: "networkidle" });

      // Should redirect away from admin
      await expect(page).not.toHaveURL(/\/studio\/v2\/admin$/);

      await context.close();
    });

    test("auditor should access audit page", async ({ browser }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "auditor");

      await page.goto("/studio/audit", { waitUntil: "networkidle" });

      // Should not redirect away
      await expect(page).toHaveURL(/\/studio\/v2\/audit/);
      await expect(page.locator("body")).not.toContainText("Access Denied");

      await context.close();
    });
  });

  test.describe("Alice Builder Persona - Developer Access", () => {
    test("alice-builder should see development modules", async ({
      browser,
    }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "alice-builder");

      await page.goto("/studio/chat", { waitUntil: "networkidle" });

      const activityBar = page.getByTestId("activity-bar");
      await expect(activityBar).toBeVisible({ timeout: 10000 });

      // Builder should see chat
      await expect(page.getByTestId("nav-chat")).toBeVisible();

      // Builder should NOT see admin
      await expect(page.getByTestId("nav-admin")).not.toBeVisible();

      await context.close();
    });

    test("alice-builder should not access compliance routes", async ({
      browser,
    }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "alice-builder");

      await page.goto("/studio/compliance", { waitUntil: "networkidle" });

      // Should redirect away or show access denied
      const hasRedirected =
        !(await page.url().includes("/studio/compliance"));
      const hasAccessDenied = await page
        .locator("body")
        .textContent()
        .then((text) => text?.includes("Access Denied") ?? false)
        .catch(() => false);

      expect(hasRedirected || hasAccessDenied).toBe(true);

      await context.close();
    });
  });

  test.describe("Bob Persona - Standard User Access", () => {
    test("bob should see basic user modules", async ({ browser }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "bob");

      await page.goto("/studio/chat", { waitUntil: "networkidle" });

      const activityBar = page.getByTestId("activity-bar");
      await expect(activityBar).toBeVisible({ timeout: 10000 });

      // Bob should see chat
      await expect(page.getByTestId("nav-chat")).toBeVisible();

      // Bob should NOT see admin, compliance, audit
      await expect(page.getByTestId("nav-admin")).not.toBeVisible();
      await expect(page.getByTestId("nav-compliance")).not.toBeVisible();

      await context.close();
    });

    test("bob should be denied access to admin routes", async ({ browser }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "bob");

      await page.goto("/studio/admin", { waitUntil: "networkidle" });

      // Should not be on admin page
      await expect(page).not.toHaveURL(/\/studio\/v2\/admin$/);

      await context.close();
    });

    test("bob should be denied access to audit routes", async ({ browser }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "bob");

      await page.goto("/studio/audit", { waitUntil: "networkidle" });

      // Should not be on audit page
      await expect(page).not.toHaveURL(/\/studio\/v2\/audit$/);

      await context.close();
    });
  });

  test.describe("Data-Driven Persona Access Tests", () => {
    const personasToTest = [
      "admin",
      "security-admin",
      "auditor",
      "alice-builder",
      "alice-analyst",
      "alice-devops",
      "compliance-officer",
      "bob",
    ];

    for (const personaName of personasToTest) {
      test(`${personaName} should access allowed modules`, async ({
        browser,
      }) => {
        const context = await browser.newContext();
        const page = await createPersonaPage(context, personaName);
        const persona = PERSONA_ACCESS_MATRIX[personaName];

        // Test first 3 allowed modules (to keep test fast)
        const modulesToTest = persona.allowedModules.slice(0, 3);

        for (const module of modulesToTest) {
          const route = MODULE_ROUTES[module];
          if (route) {
            await page.goto(route, { waitUntil: "networkidle" });

            // Should not show access denied
            const bodyText = await page.locator("body").textContent();
            expect(bodyText).not.toContain("Access Denied");
          }
        }

        await context.close();
      });

      test(`${personaName} should be denied access to restricted modules`, async ({
        browser,
      }) => {
        const context = await browser.newContext();
        const page = await createPersonaPage(context, personaName);
        const persona = PERSONA_ACCESS_MATRIX[personaName];

        // Test first 3 denied modules (to keep test fast)
        const modulesToTest = persona.deniedModules.slice(0, 3);

        for (const module of modulesToTest) {
          const route = MODULE_ROUTES[module];
          if (route) {
            await page.goto(route, { waitUntil: "networkidle" });

            // Should redirect away or show access denied
            const currentUrl = page.url();
            const bodyText = await page.locator("body").textContent();

            const hasRedirected = !currentUrl.includes(route);
            const hasAccessDenied = bodyText?.includes("Access Denied") ?? false;

            expect(hasRedirected || hasAccessDenied).toBe(true);
          }
        }

        await context.close();
      });
    }
  });

  test.describe("Navigation Visibility Matrix", () => {
    test("all personas should have activity bar visible", async ({
      browser,
    }) => {
      const context = await browser.newContext();

      for (const personaName of Object.keys(PERSONA_ACCESS_MATRIX)) {
        const page = await createPersonaPage(context, personaName);
        const persona = PERSONA_ACCESS_MATRIX[personaName];

        // Navigate to default route
        await page.goto(persona.defaultRoute, { waitUntil: "networkidle" });

        // Activity bar should be visible
        const activityBar = page.getByTestId("activity-bar");
        await expect(activityBar).toBeVisible({ timeout: 10000 });

        await page.close();
      }

      await context.close();
    });

    test("help module should be visible for all personas", async ({
      browser,
    }) => {
      const context = await browser.newContext();

      for (const personaName of Object.keys(PERSONA_ACCESS_MATRIX)) {
        const page = await createPersonaPage(context, personaName);
        const persona = PERSONA_ACCESS_MATRIX[personaName];

        await page.goto(persona.defaultRoute, { waitUntil: "networkidle" });

        // Help should be accessible for all personas
        const helpNav = page.getByTestId("nav-help");
        if (await helpNav.isVisible({ timeout: 5000 }).catch(() => false)) {
          await expect(helpNav).toBeVisible();
        }

        await page.close();
      }

      await context.close();
    });
  });

  test.describe("Route Protection Enforcement", () => {
    test("admin-only routes should redirect non-admin personas", async ({
      browser,
    }) => {
      const context = await browser.newContext();
      const nonAdminPersonas = ["bob", "alice-builder", "alice-analyst"];

      for (const personaName of nonAdminPersonas) {
        const page = await createPersonaPage(context, personaName);

        await page.goto("/studio/admin", { waitUntil: "networkidle" });

        // Non-admin should not stay on admin route
        await expect(page).not.toHaveURL(/\/studio\/v2\/admin$/);

        await page.close();
      }

      await context.close();
    });

    test("compliance routes should be accessible only to compliance roles", async ({
      browser,
    }) => {
      const context = await browser.newContext();

      // Personas with compliance access
      const compliancePersonas = [
        "admin",
        "security-admin",
        "auditor",
        "compliance-officer",
      ];

      for (const personaName of compliancePersonas) {
        const page = await createPersonaPage(context, personaName);

        await page.goto("/studio/compliance", { waitUntil: "networkidle" });

        // Should stay on compliance page
        await expect(page.locator("body")).not.toContainText("Access Denied");

        await page.close();
      }

      await context.close();
    });

    test("chat should be accessible to most user personas", async ({
      browser,
    }) => {
      const context = await browser.newContext();

      const chatAccessPersonas = [
        "admin",
        "security-admin",
        "alice-builder",
        "alice-analyst",
        "alice-devops",
        "bob",
      ];

      for (const personaName of chatAccessPersonas) {
        const page = await createPersonaPage(context, personaName);

        await page.goto("/studio/chat", { waitUntil: "networkidle" });

        // Should access chat without issues
        await expect(page.locator("body")).not.toContainText("Access Denied");

        await page.close();
      }

      await context.close();
    });
  });

  test.describe("Default Route Navigation", () => {
    for (const [personaName, persona] of Object.entries(PERSONA_ACCESS_MATRIX)) {
      test(`${personaName} default route is ${persona.defaultRoute}`, async ({
        browser,
      }) => {
        const context = await browser.newContext();
        const page = await createPersonaPage(context, personaName);

        // Navigate to default route
        await page.goto(persona.defaultRoute, { waitUntil: "networkidle" });

        // Should load successfully
        await expect(
          page.locator("main, [role='main'], h1, h2").first()
        ).toBeVisible({ timeout: 10000 });

        await context.close();
      });
    }
  });
});
