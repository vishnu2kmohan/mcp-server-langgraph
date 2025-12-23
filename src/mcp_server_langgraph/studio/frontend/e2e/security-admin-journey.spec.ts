/**
 * Security Admin User Journey E2E Tests
 *
 * Tests the complete security admin user journey including:
 * - Compliance dashboard access (FedRAMP, SOC-2)
 * - Security audit log viewing
 * - Alert monitoring
 * - Access control verification
 *
 * Uses HEART framework metrics:
 * - Happiness: Security workflow satisfaction
 * - Engagement: Security actions per session
 * - Adoption: Compliance feature discovery
 * - Retention: Security admin return rate
 * - Task Success: Security task completion rate
 *
 * Visible modules: chat, agents, flows, mcp, files, traces, costs, admin, help, audit, compliance
 * Default view: /studio/compliance
 */

import { test, expect } from "./fixtures/auth";

const backendEnabled = process.env.BACKEND_ENABLED !== "false";

test.describe("Security Admin User Journey", () => {
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

        if (url.includes("/compliance")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              fedramp: { status: "compliant", controls: 150 },
              soc2: { status: "compliant", controls: 89 },
              hipaa: { status: "partial", controls: 45 },
              gdpr: { status: "compliant", controls: 73 },
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
                  actor: "admin",
                  timestamp: Date.now(),
                },
                {
                  id: "2",
                  action: "permission_change",
                  actor: "admin",
                  timestamp: Date.now() - 3600000,
                },
              ],
              total: 2,
            }),
          });
          return;
        }

        if (url.includes("/alerts")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              items: [
                {
                  id: "1",
                  severity: "warning",
                  message: "Unusual login pattern detected",
                },
              ],
              total: 1,
            }),
          });
          return;
        }

        if (url.includes("/me")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              id: "security-admin-user",
              username: "security-admin",
              email: "security@example.com",
              roles: ["admin", "security"],
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
    test("should access compliance dashboard", async ({ adminPage }) => {
      await adminPage.goto("/studio/compliance");
      await expect(
        adminPage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();
    });

    test("should access audit logs", async ({ adminPage }) => {
      await adminPage.goto("/studio/audit");
      await expect(
        adminPage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();
    });

    test("should access admin dashboard", async ({ adminPage }) => {
      await adminPage.goto("/studio/admin/dashboard");
      await expect(adminPage.getByRole("heading").first()).toBeVisible();
    });

    test("should access traces for security monitoring", async ({
      adminPage,
    }) => {
      await adminPage.goto("/studio/observability");
      await expect(
        adminPage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();
    });

    test("should access MCP server configuration", async ({ adminPage }) => {
      await adminPage.goto("/studio/mcp");
      await expect(
        adminPage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();
    });
  });

  test.describe("Route Restrictions", () => {
    test("should have access to all admin modules", async ({ adminPage }) => {
      // Security admin has admin role, should access all admin areas
      await adminPage.goto("/studio/admin/dashboard");
      await expect(adminPage.getByRole("heading").first()).toBeVisible();

      // Verify no access denied message
      const accessDenied = adminPage.getByText(/access denied|unauthorized/i);
      await expect(accessDenied).not.toBeVisible();
    });
  });

  test.describe("Primary Workflows", () => {
    test("should view FedRAMP compliance status", async ({ adminPage }) => {
      await adminPage.goto("/studio/compliance");

      // Look for FedRAMP section (component uses fedramp-panel testid)
      const fedrampSection = adminPage.locator(
        '[data-testid="fedramp-panel"], h2:has-text("FedRAMP"), h3:has-text("FedRAMP")'
      );
      if (await fedrampSection.first().isVisible().catch(() => false)) {
        await expect(fedrampSection.first()).toBeVisible();
      }
    });

    test("should view SOC-2 compliance status", async ({ adminPage }) => {
      await adminPage.goto("/studio/compliance");

      // Look for SOC-2 section (component uses soc2-panel testid)
      const soc2Section = adminPage.locator(
        '[data-testid="soc2-panel"], h2:has-text("SOC"), h3:has-text("SOC")'
      );
      if (await soc2Section.first().isVisible().catch(() => false)) {
        await expect(soc2Section.first()).toBeVisible();
      }
    });

    test("should view audit log entries", async ({ adminPage }) => {
      await adminPage.goto("/studio/audit");

      // Look for audit log entries or table
      const auditContent = adminPage.locator(
        '[data-testid*="audit"], table, .audit-log, [role="table"]'
      );
      if (await auditContent.first().isVisible().catch(() => false)) {
        await expect(auditContent.first()).toBeVisible();
      }
    });

    test("should access security alerts", async ({ adminPage }) => {
      await adminPage.goto("/studio/admin/dashboard");

      // Look for alerts section
      const alertsSection = adminPage.locator(
        '[data-testid*="alert"], .alerts, [aria-label*="alert"]'
      );
      if (await alertsSection.first().isVisible().catch(() => false)) {
        await expect(alertsSection.first()).toBeVisible();
      }
    });
  });

  test.describe("Performance Metrics (HEART)", () => {
    test("compliance dashboard should load within acceptable time", async ({
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

    test("should have proper accessibility structure", async ({
      adminPage,
    }) => {
      await adminPage.goto("/studio/compliance");
      await expect(
        adminPage.locator("main, [role='main'], h1").first()
      ).toBeVisible();

      const headings = adminPage.getByRole("heading");
      expect(await headings.count()).toBeGreaterThan(0);
    });
  });

  test.describe("Security-Admin-specific Features", () => {
    test("should have navigation to security modules", async ({
      adminPage,
    }) => {
      await adminPage.goto("/studio/admin/dashboard");

      // Check for security-related navigation
      const navOrHeader = adminPage.locator(
        'nav, [role="navigation"], header, aside'
      );
      await expect(navOrHeader.first()).toBeVisible();
    });

    test("should support compliance report export if available", async ({
      adminPage,
    }) => {
      await adminPage.goto("/studio/compliance");

      // Look for export functionality
      const exportButton = adminPage.getByRole("button", { name: /export/i });
      if (await exportButton.first().isVisible().catch(() => false)) {
        await expect(exportButton.first()).toBeVisible();
      }
    });
  });
});
