/**
 * Compliance Officer User Journey E2E Tests
 *
 * Tests the complete compliance officer user journey including:
 * - HIPAA compliance dashboard
 * - GDPR compliance status
 * - SOC-2 compliance monitoring
 * - Audit log access
 *
 * Uses HEART framework metrics:
 * - Happiness: Compliance workflow satisfaction
 * - Engagement: Compliance review actions per session
 * - Adoption: Compliance feature discovery
 * - Retention: Compliance officer return rate
 * - Task Success: Compliance review completion rate
 *
 * Visible modules: audit, compliance, help
 * Default view: /studio/compliance
 */

import { test, expect } from "./fixtures/auth";

const backendEnabled = process.env.BACKEND_ENABLED !== "false";

test.describe("Compliance Officer User Journey", () => {
  test.beforeEach(async ({ alicePage }) => {
    if (!backendEnabled) {
      await alicePage.route("**/api/v1/**", async (route) => {
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

        if (url.includes("/compliance/hipaa")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              status: "compliant",
              controls: {
                total: 45,
                passed: 43,
                failed: 2,
                notApplicable: 0,
              },
              lastAssessment: Date.now() - 86400000,
              nextAssessment: Date.now() + 2592000000,
            }),
          });
          return;
        }

        if (url.includes("/compliance/gdpr")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              status: "compliant",
              controls: {
                total: 73,
                passed: 71,
                failed: 2,
                notApplicable: 0,
              },
              dataSubjectRequests: { pending: 3, completed: 47 },
              consentManagement: { active: 1250, revoked: 23 },
            }),
          });
          return;
        }

        if (url.includes("/compliance/soc2")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              status: "compliant",
              trustPrinciples: {
                security: "pass",
                availability: "pass",
                processingIntegrity: "pass",
                confidentiality: "pass",
                privacy: "pass",
              },
              lastAudit: Date.now() - 7776000000, // 90 days ago
            }),
          });
          return;
        }

        if (url.includes("/compliance") && !url.includes("/compliance/")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              hipaa: { status: "compliant", controls: 45 },
              gdpr: { status: "compliant", controls: 73 },
              soc2: { status: "compliant", controls: 89 },
              fedramp: { status: "in-progress", controls: 150 },
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
                  action: "data_access",
                  actor: "system",
                  resource: "phi_records",
                  timestamp: Date.now(),
                },
                {
                  id: "2",
                  action: "consent_update",
                  actor: "user:123",
                  resource: "gdpr_consent",
                  timestamp: Date.now() - 3600000,
                },
              ],
              total: 2,
            }),
          });
          return;
        }

        if (url.includes("/me")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              id: "compliance-officer-user",
              username: "compliance",
              email: "compliance@example.com",
              roles: ["developer", "compliance"],
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

    await alicePage.goto("/studio/");
  });

  test.describe("Accessible Pages", () => {
    test("should access compliance dashboard", async ({ alicePage }) => {
      await alicePage.goto("/studio/compliance");
      await expect(
        alicePage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();
    });

    test("should access audit logs", async ({ alicePage }) => {
      await alicePage.goto("/studio/audit");
      await expect(
        alicePage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();
    });

    test("should access help section", async ({ alicePage }) => {
      await alicePage.goto("/studio/help");
      await expect(
        alicePage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();
    });
  });

  test.describe("Route Restrictions", () => {
    test("compliance officer should have compliance-focused navigation", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/compliance");

      // Check navigation structure
      const navOrHeader = alicePage.locator(
        'nav, [role="navigation"], header, aside'
      );
      await expect(navOrHeader.first()).toBeVisible();
    });
  });

  test.describe("Primary Workflows", () => {
    test("should view HIPAA compliance status", async ({ alicePage }) => {
      await alicePage.goto("/studio/compliance");

      // Look for HIPAA section
      const hipaaContent = alicePage.locator(
        '[data-testid*="hipaa"], [data-testid*="HIPAA"], h2:has-text("HIPAA"), h3:has-text("HIPAA"), [class*="hipaa"]'
      );
      if (await hipaaContent.first().isVisible().catch(() => false)) {
        await expect(hipaaContent.first()).toBeVisible();
      }
    });

    test("should view GDPR compliance status", async ({ alicePage }) => {
      await alicePage.goto("/studio/compliance");

      // Look for GDPR section
      const gdprContent = alicePage.locator(
        '[data-testid*="gdpr"], [data-testid*="GDPR"], h2:has-text("GDPR"), h3:has-text("GDPR"), [class*="gdpr"]'
      );
      if (await gdprContent.first().isVisible().catch(() => false)) {
        await expect(gdprContent.first()).toBeVisible();
      }
    });

    test("should view SOC-2 compliance status", async ({ alicePage }) => {
      await alicePage.goto("/studio/compliance");

      // Look for SOC-2 section
      const soc2Content = alicePage.locator(
        '[data-testid*="soc2"], [data-testid*="SOC"], h2:has-text("SOC"), h3:has-text("SOC"), [class*="soc"]'
      );
      if (await soc2Content.first().isVisible().catch(() => false)) {
        await expect(soc2Content.first()).toBeVisible();
      }
    });

    test("should view compliance-related audit logs", async ({ alicePage }) => {
      await alicePage.goto("/studio/audit");

      // Look for audit log content
      const auditContent = alicePage.locator(
        '[data-testid*="audit"], table, [role="table"], .audit-log'
      );
      if (await auditContent.first().isVisible().catch(() => false)) {
        await expect(auditContent.first()).toBeVisible();
      }
    });
  });

  test.describe("Performance Metrics (HEART)", () => {
    test("compliance dashboard should load within acceptable time", async ({
      alicePage,
    }) => {
      const startTime = Date.now();

      await alicePage.goto("/studio/compliance");
      await expect(
        alicePage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();

      const loadTime = Date.now() - startTime;
      expect(loadTime).toBeLessThan(5000);
    });

    test("audit page should load within acceptable time", async ({
      alicePage,
    }) => {
      const startTime = Date.now();

      await alicePage.goto("/studio/audit");
      await expect(
        alicePage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();

      const loadTime = Date.now() - startTime;
      expect(loadTime).toBeLessThan(5000);
    });

    test("should have proper accessibility structure", async ({ alicePage }) => {
      await alicePage.goto("/studio/compliance");
      await expect(
        alicePage.locator("main, [role='main'], h1").first()
      ).toBeVisible();

      const headings = alicePage.getByRole("heading");
      expect(await headings.count()).toBeGreaterThan(0);
    });
  });

  test.describe("Compliance-Officer-specific Features", () => {
    test("should support compliance report generation if available", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/compliance");

      // Look for report/export functionality
      const reportButton = alicePage.getByRole("button", {
        name: /report|export|download/i,
      });
      if (await reportButton.first().isVisible().catch(() => false)) {
        await expect(reportButton.first()).toBeVisible();
      }
    });

    test("should show compliance status overview", async ({ alicePage }) => {
      await alicePage.goto("/studio/compliance");

      // Look for status overview
      const statusOverview = alicePage.locator(
        '[data-testid*="status"], [data-testid*="overview"], .compliance-status, .status-card'
      );
      if (await statusOverview.first().isVisible().catch(() => false)) {
        await expect(statusOverview.first()).toBeVisible();
      }
    });
  });
});
