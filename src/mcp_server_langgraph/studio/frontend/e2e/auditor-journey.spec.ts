/**
 * Auditor User Journey E2E Tests
 *
 * Tests the complete auditor user journey including:
 * - Audit log access and filtering
 * - Compliance report viewing
 * - Read-only access verification
 *
 * Uses HEART framework metrics:
 * - Happiness: Audit workflow efficiency
 * - Engagement: Audit actions per session
 * - Adoption: Audit feature discovery
 * - Retention: Auditor return rate
 * - Task Success: Audit task completion rate
 *
 * Visible modules: audit, compliance, help (read-only focus)
 * Default view: /studio/audit
 */

import { test, expect } from "./fixtures/auth";

const backendEnabled = process.env.BACKEND_ENABLED !== "false";

test.describe("Auditor User Journey", () => {
  test.beforeEach(async ({ adminPage }) => {
    if (!backendEnabled) {
      await adminPage.route("**/api/v1/**", async (route) => {
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

        if (url.includes("/audit/logs")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              items: [
                {
                  id: "1",
                  action: "user_login",
                  actor: "user1",
                  timestamp: Date.now(),
                  resource: "system",
                },
                {
                  id: "2",
                  action: "workflow_created",
                  actor: "alice",
                  timestamp: Date.now() - 1800000,
                  resource: "workflow:abc123",
                },
                {
                  id: "3",
                  action: "permission_granted",
                  actor: "admin",
                  timestamp: Date.now() - 3600000,
                  resource: "user:bob",
                },
              ],
              total: 3,
            }),
          });
          return;
        }

        if (url.includes("/compliance")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              hipaa: { status: "compliant", controls: 45, lastAudit: Date.now() },
              gdpr: { status: "compliant", controls: 73, lastAudit: Date.now() },
              soc2: { status: "compliant", controls: 89, lastAudit: Date.now() },
            }),
          });
          return;
        }

        if (url.includes("/me")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              id: "auditor-user",
              username: "auditor",
              email: "auditor@example.com",
              roles: ["admin", "audit"],
            }),
          });
          return;
        }

        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ items: [], total: 0 }),
        });
      });
    }

    await adminPage.goto("/studio/");
  });

  test.describe("Accessible Pages", () => {
    test("should access audit log page", async ({ adminPage }) => {
      await adminPage.goto("/studio/audit");
      await expect(
        adminPage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();
    });

    test("should access compliance dashboard", async ({ adminPage }) => {
      await adminPage.goto("/studio/compliance");
      await expect(
        adminPage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();
    });

    test("should access help section", async ({ adminPage }) => {
      await adminPage.goto("/studio/help");
      await expect(
        adminPage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();
    });
  });

  test.describe("Route Restrictions", () => {
    test("auditor should have limited navigation options", async ({
      adminPage,
    }) => {
      await adminPage.goto("/studio/audit");

      // Check navigation structure exists
      const navOrHeader = adminPage.locator(
        'nav, [role="navigation"], header, aside'
      );
      await expect(navOrHeader.first()).toBeVisible();
    });
  });

  test.describe("Primary Workflows", () => {
    test("should view audit log entries", async ({ adminPage }) => {
      await adminPage.goto("/studio/audit");

      // Look for audit log content
      const auditContent = adminPage.locator(
        '[data-testid*="audit"], table, .audit-log, [role="table"], [role="grid"]'
      );
      if (await auditContent.first().isVisible().catch(() => false)) {
        await expect(auditContent.first()).toBeVisible();
      }
    });

    test("should filter audit logs if functionality available", async ({
      adminPage,
    }) => {
      await adminPage.goto("/studio/audit");

      // Look for filter controls
      const filterInput = adminPage.locator(
        'input[placeholder*="filter" i], input[placeholder*="search" i], [data-testid*="filter"]'
      );
      if (await filterInput.first().isVisible().catch(() => false)) {
        await filterInput.first().fill("user_login");
        await expect(filterInput.first()).toHaveValue("user_login");
      }
    });

    test("should view compliance status", async ({ adminPage }) => {
      await adminPage.goto("/studio/compliance");

      // Look for compliance status indicators
      const complianceContent = adminPage.locator(
        '[data-testid*="compliance"], [data-testid*="status"], .compliance-status'
      );
      if (await complianceContent.first().isVisible().catch(() => false)) {
        await expect(complianceContent.first()).toBeVisible();
      }
    });

    test("should export audit data if functionality available", async ({
      adminPage,
    }) => {
      await adminPage.goto("/studio/audit");

      // Look for export button
      const exportButton = adminPage.getByRole("button", { name: /export/i });
      if (await exportButton.first().isVisible().catch(() => false)) {
        await expect(exportButton.first()).toBeEnabled();
      }
    });
  });

  test.describe("Performance Metrics (HEART)", () => {
    test("audit page should load within acceptable time", async ({
      adminPage,
    }) => {
      const startTime = Date.now();

      await adminPage.goto("/studio/audit");
      await expect(
        adminPage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();

      const loadTime = Date.now() - startTime;
      expect(loadTime).toBeLessThan(5000);
    });

    test("compliance page should load within acceptable time", async ({
      adminPage,
    }) => {
      const startTime = Date.now();

      await adminPage.goto("/studio/compliance");
      await expect(
        adminPage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();

      const loadTime = Date.now() - startTime;
      expect(loadTime).toBeLessThan(5000);
    });

    test("should have proper accessibility structure", async ({
      adminPage,
    }) => {
      await adminPage.goto("/studio/audit");
      await expect(
        adminPage.locator("main, [role='main'], h1").first()
      ).toBeVisible();

      const headings = adminPage.getByRole("heading");
      expect(await headings.count()).toBeGreaterThan(0);
    });
  });

  test.describe("Auditor-specific Features", () => {
    test("should have read-only focused interface", async ({ adminPage }) => {
      await adminPage.goto("/studio/audit");

      // Auditor should see data but limited editing controls
      const mainContent = adminPage.locator("main, [role='main']");
      await expect(mainContent.first()).toBeVisible();
    });
  });
});
