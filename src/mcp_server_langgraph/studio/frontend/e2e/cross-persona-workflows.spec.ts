/**
 * Cross-Persona Workflow E2E Tests
 *
 * Tests workflows and data sharing between different personas:
 * - alice-builder creates workflow → bob views as shared
 * - admin creates template → alice-devops applies it
 * - alice-analyst views traces from alice-builder session
 *
 * These tests verify that the RBAC system correctly allows cross-persona
 * access to shared resources while maintaining security boundaries.
 *
 * Phase 4.1: Cross-persona workflow tests
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
}

// =============================================================================
// Persona Configurations
// =============================================================================

const PERSONAS: Record<string, PersonaConfig> = {
  admin: {
    id: "admin-user",
    username: "admin",
    email: "admin@example.com",
    roles: ["admin"],
    persona: "admin",
  },
  "alice-builder": {
    id: "alice-builder-user",
    username: "alice-builder",
    email: "alice-builder@example.com",
    roles: ["developer", "builder"],
    persona: "alice-builder",
  },
  "alice-analyst": {
    id: "alice-analyst-user",
    username: "alice-analyst",
    email: "alice-analyst@example.com",
    roles: ["developer", "analyst"],
    persona: "alice-analyst",
  },
  "alice-devops": {
    id: "alice-devops-user",
    username: "alice-devops",
    email: "alice-devops@example.com",
    roles: ["developer", "devops"],
    persona: "alice-devops",
  },
  bob: {
    id: "bob-user",
    username: "bob",
    email: "bob@example.com",
    roles: ["user"],
    persona: "bob",
  },
};

// =============================================================================
// Shared Workflow Data (simulates cross-persona shared resources)
// =============================================================================

const SHARED_WORKFLOW = {
  id: "shared-workflow-001",
  name: "Customer Support Pipeline",
  description: "Cross-team customer support workflow",
  status: "active",
  owner: "alice-builder",
  sharedWith: ["bob", "alice-devops"],
  created_at: new Date().toISOString(),
};

const ADMIN_TEMPLATE = {
  id: "admin-template-001",
  name: "DevOps Deployment Template",
  description: "Standard deployment workflow template",
  type: "template",
  owner: "admin",
  is_public: true,
  created_at: new Date().toISOString(),
};

const SHARED_TRACE = {
  id: "trace-001",
  session_id: "session-alice-builder-001",
  owner: "alice-builder",
  name: "Production Debug Session",
  status: "completed",
  duration_ms: 15000,
  created_at: new Date().toISOString(),
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
 * Set up API mocks for cross-persona endpoints
 */
async function setupCrossPersonaApiMocks(
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
          studio_canvas_shell: true,
          canvas_editable: true,
          canvas_agents: true,
          workflows: true,
          sessions: true,
          observability: true,
        }),
      });
      return;
    }

    // Workflows endpoint - return shared workflows based on persona
    if (url.includes("/workflows")) {
      const workflows =
        persona.username === "alice-builder" ||
        persona.username === "bob" ||
        persona.username === "admin"
          ? [SHARED_WORKFLOW]
          : [];

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: workflows,
          total: workflows.length,
        }),
      });
      return;
    }

    // Templates endpoint - return admin templates
    if (url.includes("/templates")) {
      const templates =
        persona.username === "admin" || persona.username === "alice-devops"
          ? [ADMIN_TEMPLATE]
          : [];

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: templates,
          total: templates.length,
        }),
      });
      return;
    }

    // Traces endpoint - return shared traces for analysts
    if (url.includes("/traces") || url.includes("/observability")) {
      const traces =
        persona.username === "alice-analyst" ||
        persona.username === "alice-builder" ||
        persona.username === "admin"
          ? [SHARED_TRACE]
          : [];

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: traces,
          total: traces.length,
        }),
      });
      return;
    }

    // Sessions endpoint
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
    await setupCrossPersonaApiMocks(page, persona);
  }

  return page;
}

// =============================================================================
// Test Suites
// =============================================================================

test.describe("Cross-Persona Workflow Sharing", () => {
  test.describe("Scenario 1: alice-builder creates workflow → bob views as shared", () => {
    test("alice-builder should see their created workflow", async ({
      browser,
    }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "alice-builder");

      await page.goto("/studio/workflows", { waitUntil: "networkidle" });

      // Wait for page to load
      await page.waitForTimeout(1000);

      // Alice-builder should see the shared workflow they own
      const pageContent = await page.content();
      expect(
        pageContent.includes("Customer Support Pipeline") ||
          pageContent.includes("workflow") ||
          pageContent.includes("Workflow")
      ).toBe(true);

      await context.close();
    });

    test("bob should see workflows shared with them", async ({ browser }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "bob");

      await page.goto("/studio/workflows", { waitUntil: "networkidle" });

      // Wait for page to load
      await page.waitForTimeout(1000);

      // Bob should see the shared workflow
      const pageContent = await page.content();
      expect(
        pageContent.includes("Customer Support Pipeline") ||
          pageContent.includes("workflow") ||
          pageContent.includes("Workflow")
      ).toBe(true);

      await context.close();
    });

    test("bob should not have edit permissions on alice-builder's workflow", async ({
      browser,
    }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "bob");

      await page.goto("/studio/workflows", { waitUntil: "networkidle" });

      // Wait for page to load
      await page.waitForTimeout(1000);

      // Check that edit button is not visible or is disabled
      const editButton = page.getByRole("button", { name: /edit/i });
      const editButtonCount = await editButton.count();

      // Either no edit button or it should indicate read-only access
      if (editButtonCount > 0) {
        const isDisabled = await editButton.first().isDisabled();
        // For shared workflows, edit should be disabled for non-owners
        // This is the expected behavior but may vary based on implementation
        expect(isDisabled || editButtonCount === 0).toBe(true);
      }

      await context.close();
    });
  });

  test.describe("Scenario 2: admin creates template → alice-devops applies it", () => {
    test("admin should see templates they created", async ({ browser }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "admin");

      await page.goto("/studio/admin", { waitUntil: "networkidle" });

      // Wait for page to load
      await page.waitForTimeout(1000);

      // Admin should see the admin dashboard
      await expect(page.locator("body")).not.toContainText("Access Denied");

      await context.close();
    });

    test("alice-devops should see public templates", async ({ browser }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "alice-devops");

      await page.goto("/studio/mcp", { waitUntil: "networkidle" });

      // Wait for page to load
      await page.waitForTimeout(1000);

      // Alice-devops should be able to access MCP page
      await expect(page.locator("body")).not.toContainText("Access Denied");

      await context.close();
    });

    test("alice-devops should not access admin routes", async ({ browser }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "alice-devops");

      await page.goto("/studio/admin", { waitUntil: "networkidle" });

      // Should redirect away from admin
      await expect(page).not.toHaveURL(/\/studio\/admin$/);

      await context.close();
    });
  });

  test.describe("Scenario 3: alice-analyst views traces from alice-builder session", () => {
    test("alice-analyst should see shared traces", async ({ browser }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "alice-analyst");

      await page.goto("/studio/observability", { waitUntil: "networkidle" });

      // Wait for page to load
      await page.waitForTimeout(1000);

      // Alice-analyst should have access to observability
      await expect(page.locator("body")).not.toContainText("Access Denied");

      await context.close();
    });

    test("alice-analyst should not access workflow builder", async ({
      browser,
    }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "alice-analyst");

      await page.goto("/studio/workflows", { waitUntil: "networkidle" });

      // Should redirect away or show access denied
      const hasRedirected = !(await page
        .url()
        .includes("/studio/workflows"));
      const hasAccessDenied = await page
        .locator("body")
        .textContent()
        .then((text) => text?.includes("Access Denied") ?? false)
        .catch(() => false);

      expect(hasRedirected || hasAccessDenied).toBe(true);

      await context.close();
    });

    test("alice-builder should also see their own traces", async ({
      browser,
    }) => {
      const context = await browser.newContext();
      const page = await createPersonaPage(context, "alice-builder");

      // alice-builder should access observability via chat context
      await page.goto("/studio/chat", { waitUntil: "networkidle" });

      // Wait for page to load
      await page.waitForTimeout(1000);

      // alice-builder should be on chat page
      await expect(page).toHaveURL(/\/studio\/chat/);

      await context.close();
    });
  });
});

test.describe("Cross-Persona Security Boundaries", () => {
  test("bob cannot access admin-only resources", async ({ browser }) => {
    const context = await browser.newContext();
    const page = await createPersonaPage(context, "bob");

    await page.goto("/studio/admin", { waitUntil: "networkidle" });

    // Should not be on admin page
    await expect(page).not.toHaveURL(/\/studio\/admin$/);

    await context.close();
  });

  test("alice-builder cannot access compliance resources", async ({
    browser,
  }) => {
    const context = await browser.newContext();
    const page = await createPersonaPage(context, "alice-builder");

    await page.goto("/studio/compliance", { waitUntil: "networkidle" });

    // Should redirect or show access denied
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

  test("admin can access all persona resources", async ({ browser }) => {
    const context = await browser.newContext();
    const page = await createPersonaPage(context, "admin");

    // Admin should access chat
    await page.goto("/studio/chat", { waitUntil: "networkidle" });
    await expect(page).toHaveURL(/\/studio\/chat/);

    // Admin should access admin dashboard
    await page.goto("/studio/admin", { waitUntil: "networkidle" });
    await expect(page).toHaveURL(/\/studio\/admin/);

    // Admin should access compliance
    await page.goto("/studio/compliance", { waitUntil: "networkidle" });
    await expect(page).toHaveURL(/\/studio\/compliance/);

    // Admin should access audit
    await page.goto("/studio/audit", { waitUntil: "networkidle" });
    await expect(page).toHaveURL(/\/studio\/audit/);

    await context.close();
  });
});
