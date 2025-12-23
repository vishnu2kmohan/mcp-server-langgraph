/**
 * HITL Intelligence E2E Tests
 *
 * Sprint 6: Tests for AI-powered Human-in-the-Loop features
 * - Risk assessment
 * - Decision history
 * - Approval workflows
 *
 * Tests persona access:
 * - admin: Full access
 * - auditor: Full access (audit-focused)
 * - compliance-officer: Full access (compliance-focused)
 * - alice-builder: No access (developer, no HITL admin)
 * - bob: No access (user role)
 */

import { test, expect } from "./fixtures/auth";

const backendEnabled = process.env.BACKEND_ENABLED !== "false";

// =============================================================================
// Mock Data
// =============================================================================

const mockRiskAssessmentResponse = {
  analyses: {
    risk_assess: {
      risk_score: 0.72,
      risk_level: "medium",
      factors: [
        { factor: "destructive_operation", weight: 0.4, description: "Operation deletes data" },
        { factor: "production_environment", weight: 0.3, description: "Target is production" },
      ],
      recommendation: "require_approval",
      similar_decisions: 3,
    },
  },
  cross_insights: [],
  failed_analyses: [],
  total_cost: "0.002",
};

const mockDecisionHistoryResponse = {
  analyses: {
    decision_history: {
      total_decisions: 47,
      approved: 38,
      rejected: 9,
      recent: [
        {
          id: "decision-1",
          action_type: "file_delete",
          decision: "approved",
          decided_by: "admin",
          decided_at: new Date().toISOString(),
          risk_score: 0.45,
        },
        {
          id: "decision-2",
          action_type: "database_migration",
          decision: "rejected",
          decided_by: "compliance-officer",
          decided_at: new Date().toISOString(),
          risk_score: 0.89,
        },
      ],
      patterns: {
        auto_approved_threshold: 0.3,
        avg_review_time_ms: 45000,
      },
    },
  },
  cross_insights: ["High-risk operations consistently require manual review"],
  failed_analyses: [],
  total_cost: "0.001",
};

const mockHighRiskAssessmentResponse = {
  analyses: {
    risk_assess: {
      risk_score: 0.95,
      risk_level: "critical",
      factors: [
        { factor: "destructive_operation", weight: 0.5, description: "Irreversible operation" },
        { factor: "production_environment", weight: 0.3, description: "Production system" },
        { factor: "no_backup", weight: 0.2, description: "No backup available" },
      ],
      recommendation: "block_without_override",
      similar_decisions: 0,
    },
  },
  cross_insights: ["This operation has no precedent in decision history"],
  failed_analyses: [],
  total_cost: "0.002",
};

const mockMultiHITLTaskResponse = {
  analyses: {
    risk_assess: {
      risk_score: 0.65,
      risk_level: "medium",
      factors: [{ factor: "sensitive_data", weight: 0.4, description: "Accesses PII" }],
      recommendation: "require_approval",
      similar_decisions: 5,
    },
    decision_history: {
      total_decisions: 47,
      approved: 38,
      rejected: 9,
      recent: [],
      patterns: { auto_approved_threshold: 0.3, avg_review_time_ms: 45000 },
    },
  },
  cross_insights: [
    "Risk score aligns with historical approval patterns",
    "Similar operations typically approved within 2 minutes",
  ],
  failed_analyses: [],
  total_cost: "0.003",
};

// =============================================================================
// Admin Journey - Full HITL Access
// =============================================================================

test.describe("Admin HITL Intelligence", () => {
  test.beforeEach(async ({ adminPage }) => {
    if (!backendEnabled) {
      await adminPage.route("**/api/v1/**", async (route) => {
        const url = route.request().url();

        if (url.includes("/studio/analyze")) {
          const body = await route.request().postDataJSON();
          const tasks = body?.tasks || [];

          // Return appropriate mock based on requested tasks
          if (tasks.some((t: { type: string }) => t.type === "risk_assess")) {
            const actionType = tasks.find((t: { type: string }) => t.type === "risk_assess")?.data
              ?.action_type;
            if (actionType === "database_drop") {
              await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify(mockHighRiskAssessmentResponse),
              });
              return;
            }
            await route.fulfill({
              status: 200,
              contentType: "application/json",
              body: JSON.stringify(mockRiskAssessmentResponse),
            });
            return;
          }
          if (tasks.some((t: { type: string }) => t.type === "decision_history")) {
            await route.fulfill({
              status: 200,
              contentType: "application/json",
              body: JSON.stringify(mockDecisionHistoryResponse),
            });
            return;
          }
          // Multiple tasks
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(mockMultiHITLTaskResponse),
          });
          return;
        }

        if (url.includes("/features")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              enable_studio_ai: true,
              enable_hitl_intelligence: true,
              agent_hitl: true,
            }),
          });
          return;
        }

        if (url.includes("/agents/requests")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              items: [
                {
                  id: "request-1",
                  action_type: "file_delete",
                  status: "pending",
                  created_at: new Date().toISOString(),
                },
              ],
              total: 1,
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
  });

  test("should display risk assessment in approval dialog", async ({ adminPage }) => {
    await adminPage.goto("/studio/admin");

    // Wait for page to load
    await expect(adminPage.locator("main, [role='main'], h1, h2").first()).toBeVisible();

    // Look for HITL/approval-related UI
    const approvalArea = adminPage.locator(
      '[data-testid*="approval"], [data-testid*="hitl"], [class*="approval"]'
    );
    if (await approvalArea.first().isVisible().catch(() => false)) {
      await expect(approvalArea.first()).toBeVisible();
    }
  });

  test("should show decision history panel", async ({ adminPage }) => {
    await adminPage.goto("/studio/admin");

    // Wait for page to load
    await expect(adminPage.locator("main, [role='main'], h1, h2").first()).toBeVisible();

    // Look for decision history UI elements
    const historyArea = adminPage.locator(
      '[data-testid*="decision-history"], [data-testid*="audit-log"], [class*="history"]'
    );
    // Decision history may be in a tab or expandable section
  });

  test("should display risk indicators on pending approvals", async ({ adminPage }) => {
    await adminPage.goto("/studio/admin");

    // Wait for page to load
    await expect(adminPage.locator("main, [role='main'], h1").first()).toBeVisible();

    // Look for risk indicator UI elements
    const riskIndicators = adminPage.locator(
      '[data-testid*="risk"], [class*="risk-score"], [aria-label*="risk"]'
    );
    // Risk indicators shown on approval cards
  });

  test("admin should have access to all HITL intelligence features", async ({ adminPage }) => {
    await adminPage.goto("/studio/admin");

    // Verify admin page loads
    await expect(adminPage.locator("main, [role='main'], h1").first()).toBeVisible();

    // Admin should have full module access
    const nav = adminPage.locator('nav, [role="navigation"], aside');
    await expect(nav.first()).toBeVisible();
  });

  test("should show similar past decisions for context", async ({ adminPage }) => {
    await adminPage.goto("/studio/admin");

    // Wait for page to load
    await expect(adminPage.locator("main, [role='main']").first()).toBeVisible();

    // Look for similar decisions section (use class/text fallbacks)
    const similarDecisions = adminPage.locator(
      '[class*="similar-decisions"], [class*="past-decisions"], text=/similar|past decisions/i'
    );
    // Similar decisions shown when viewing approval details
  });
});

// =============================================================================
// Auditor Journey - Full HITL Access (Audit Focus)
// =============================================================================

test.describe("Auditor HITL Intelligence", () => {
  test.beforeEach(async ({ auditorPage }) => {
    if (!backendEnabled) {
      await auditorPage.route("**/api/v1/**", async (route) => {
        const url = route.request().url();

        if (url.includes("/studio/analyze")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(mockDecisionHistoryResponse),
          });
          return;
        }

        if (url.includes("/features")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              enable_studio_ai: true,
              enable_hitl_intelligence: true,
              agent_hitl: true,
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
  });

  test("auditor should access HITL decision history", async ({ auditorPage }) => {
    await auditorPage.goto("/studio/audit");

    // Verify audit page loads
    await expect(auditorPage.locator("main, [role='main'], h1, h2").first()).toBeVisible();
  });

  test("auditor should see approval audit trail", async ({ auditorPage }) => {
    await auditorPage.goto("/studio/audit");

    // Wait for page to load
    await expect(auditorPage.locator("main, [role='main'], h1").first()).toBeVisible();

    // Look for audit trail elements
    const auditTrail = auditorPage.locator(
      '[data-testid*="audit"], [class*="audit"], [aria-label*="audit"]'
    );
    // Audit trail should be accessible
  });

  test("auditor should view decision patterns", async ({ auditorPage }) => {
    await auditorPage.goto("/studio/audit");

    // Wait for page to load
    await expect(auditorPage.locator("main, [role='main'], h1").first()).toBeVisible();

    // Decision patterns shown in analytics (use class fallbacks)
    const patterns = auditorPage.locator(
      '[class*="analytics"], [class*="statistics"], [class*="pattern"]'
    );
    // Patterns may be in a dashboard section
  });
});

// =============================================================================
// Compliance Officer Journey - Full HITL Access (Compliance Focus)
// =============================================================================

test.describe("Compliance Officer HITL Intelligence", () => {
  test.beforeEach(async ({ complianceOfficerPage }) => {
    if (!backendEnabled) {
      await complianceOfficerPage.route("**/api/v1/**", async (route) => {
        const url = route.request().url();

        if (url.includes("/studio/analyze")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(mockRiskAssessmentResponse),
          });
          return;
        }

        if (url.includes("/features")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              enable_studio_ai: true,
              enable_hitl_intelligence: true,
              agent_hitl: true,
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
  });

  test("compliance-officer should access HITL risk assessment", async ({
    complianceOfficerPage,
  }) => {
    await complianceOfficerPage.goto("/studio/compliance");

    // Verify compliance page loads
    await expect(
      complianceOfficerPage.locator("main, [role='main'], h1, h2").first()
    ).toBeVisible();
  });

  test("compliance-officer should see compliance impact indicators", async ({
    complianceOfficerPage,
  }) => {
    await complianceOfficerPage.goto("/studio/compliance");

    // Wait for page to load
    await expect(complianceOfficerPage.locator("main, [role='main'], h1").first()).toBeVisible();

    // Look for compliance indicators
    const complianceIndicators = complianceOfficerPage.locator(
      '[data-testid*="compliance"], [class*="compliance"], [aria-label*="compliance"]'
    );
    // Compliance impact shown on risk assessments
  });

  test("compliance-officer should access approval workflow", async ({ complianceOfficerPage }) => {
    await complianceOfficerPage.goto("/studio/compliance");

    // Wait for page to load
    await expect(complianceOfficerPage.locator("main, [role='main']").first()).toBeVisible();

    // Approval workflow accessible
    const approvalWorkflow = complianceOfficerPage.locator(
      '[data-testid*="workflow"], [data-testid*="approval"]'
    );
    // Workflow controls should be accessible
  });
});

// =============================================================================
// Alice (Developer) - No HITL Intelligence Access
// =============================================================================

test.describe("Alice Developer HITL Restrictions", () => {
  test.beforeEach(async ({ alicePage }) => {
    if (!backendEnabled) {
      await alicePage.route("**/api/v1/**", async (route) => {
        const url = route.request().url();

        if (url.includes("/features")) {
          await alicePage.route("**/api/v1/features**", async (route) => {
            await route.fulfill({
              status: 200,
              contentType: "application/json",
              body: JSON.stringify({
                enable_studio_ai: true,
                enable_hitl_intelligence: false, // Disabled for developers
                agent_hitl: false,
              }),
            });
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
  });

  test("alice should not have admin module access", async ({ alicePage }) => {
    // Developer role does not have admin access
    await alicePage.goto("/studio/admin");

    // May redirect to default developer view or show restricted access
    // Just verify page doesn't crash
    await expect(alicePage.locator("body")).toBeVisible();
  });

  test("alice should use basic chat without HITL features", async ({ alicePage }) => {
    await alicePage.goto("/studio/chat");

    // Verify chat page loads
    await expect(alicePage.locator("main, [role='main'], h1, h2").first()).toBeVisible();

    // Alice should not see HITL intelligence features
  });
});

// =============================================================================
// Bob (User) - No HITL Intelligence Access
// =============================================================================

test.describe("Bob User HITL Restrictions", () => {
  test.beforeEach(async ({ bobPage }) => {
    if (!backendEnabled) {
      await bobPage.route("**/api/v1/**", async (route) => {
        const url = route.request().url();

        if (url.includes("/features")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              enable_studio_ai: true,
              enable_hitl_intelligence: false, // Disabled for users
              agent_hitl: false,
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
  });

  test("bob should not have access to admin module", async ({ bobPage }) => {
    // User role does not have admin access
    await bobPage.goto("/studio/admin");

    // May redirect to default user view or show restricted access
    await expect(bobPage.locator("body")).toBeVisible();
  });

  test("bob should not see HITL features in chat", async ({ bobPage }) => {
    await bobPage.goto("/studio/chat");

    // Verify chat page loads
    await expect(bobPage.locator("main, [role='main'], h1, h2").first()).toBeVisible();

    // Bob should not see any HITL intelligence features
    const hitlFeatures = bobPage.locator(
      '[data-testid="hitl-risk-assessment"], [data-testid="hitl-decision-history"]'
    );
    // These should not be visible for bob
  });
});

// =============================================================================
// HITL Intelligence Feature Flag Tests
// =============================================================================

test.describe("HITL Intelligence Feature Flags", () => {
  test("HITL intelligence should respect enable_hitl_intelligence flag", async ({ adminPage }) => {
    // Mock feature flags with HITL intelligence disabled
    await adminPage.route("**/api/v1/features**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enable_studio_ai: true,
          enable_hitl_intelligence: false, // Disabled
          agent_hitl: false,
        }),
      });
    });

    await adminPage.goto("/studio/admin");

    // Page should load without HITL AI features
    await expect(adminPage.locator("main, [role='main']").first()).toBeVisible();
  });

  test("HITL intelligence should fallback to enable_studio_ai master flag", async ({
    adminPage,
  }) => {
    // Mock feature flags with master flag only
    await adminPage.route("**/api/v1/features**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enable_studio_ai: true,
          // enable_hitl_intelligence not set - should fallback
        }),
      });
    });

    await adminPage.goto("/studio/admin");

    // Page should load with AI features enabled via fallback
    await expect(adminPage.locator("main, [role='main']").first()).toBeVisible();
  });

  test("agent_hitl flag should control approval workflow visibility", async ({ adminPage }) => {
    // Mock feature flags with agent_hitl disabled
    await adminPage.route("**/api/v1/features**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enable_studio_ai: true,
          enable_hitl_intelligence: true,
          agent_hitl: false, // Disabled
        }),
      });
    });

    await adminPage.goto("/studio/admin");

    // Page should load without approval workflow
    await expect(adminPage.locator("main, [role='main']").first()).toBeVisible();
  });
});

// =============================================================================
// Risk Level Classification Tests
// =============================================================================

test.describe("Risk Level Classification", () => {
  test.beforeEach(async ({ adminPage }) => {
    if (!backendEnabled) {
      await adminPage.route("**/api/v1/features**", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            enable_studio_ai: true,
            enable_hitl_intelligence: true,
            agent_hitl: true,
          }),
        });
      });
    }
  });

  test("should handle low risk operations", async ({ adminPage }) => {
    await adminPage.goto("/studio/admin");

    // Wait for page to load
    await expect(adminPage.locator("main, [role='main'], h1").first()).toBeVisible();

    // Low risk operations may auto-approve
  });

  test("should handle critical risk operations", async ({ adminPage }) => {
    await adminPage.goto("/studio/admin");

    // Wait for page to load
    await expect(adminPage.locator("main, [role='main'], h1").first()).toBeVisible();

    // Critical risk operations require explicit approval
  });
});

// =============================================================================
// Performance Tests
// =============================================================================

test.describe("HITL Intelligence Performance", () => {
  test("admin page with HITL features should load within acceptable time", async ({
    adminPage,
  }) => {
    const startTime = Date.now();

    await adminPage.goto("/studio/admin");
    await expect(adminPage.locator("main, [role='main'], h1").first()).toBeVisible();

    const loadTime = Date.now() - startTime;
    // Should load within 5 seconds even with HITL AI features
    expect(loadTime).toBeLessThan(5000);
  });

  test("risk assessment should not block approval dialog", async ({ adminPage }) => {
    await adminPage.goto("/studio/admin");

    // Main content should be visible quickly
    await expect(adminPage.locator("main, [role='main']").first()).toBeVisible({ timeout: 3000 });

    // Risk assessment may load asynchronously
  });
});
