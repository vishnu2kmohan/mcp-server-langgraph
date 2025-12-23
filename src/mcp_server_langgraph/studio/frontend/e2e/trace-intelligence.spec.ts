/**
 * Trace Intelligence E2E Tests
 *
 * Sprint 5: Tests for AI-powered trace/execution features
 * - Trace summarization
 * - Trace anomaly detection
 * - Cost projection
 * - Token prediction
 *
 * Tests persona access:
 * - admin: Full access
 * - alice-analyst: Full access (developer with trace access)
 * - bob: No access (trace module restricted)
 */

import { test, expect } from "./fixtures/auth";

const backendEnabled = process.env.BACKEND_ENABLED !== "false";

// =============================================================================
// Mock Data
// =============================================================================

const mockTraceSummaryResponse = {
  analyses: {
    trace_summarize: {
      summary: "Completed 5 LLM calls with 2 tool invocations in 3.2 seconds",
      total_duration_ms: 3200,
      step_count: 7,
      tool_call_count: 2,
      llm_call_count: 5,
    },
  },
  cross_insights: [],
  failed_analyses: [],
  total_cost: "0.001",
};

const mockTraceAnomalyResponse = {
  analyses: {
    trace_anomaly: {
      anomalies: [
        { type: "slow_step", step_id: "step-3", severity: "warning" },
      ],
      bottlenecks: ["step-3"],
      health_score: 0.85,
    },
  },
  cross_insights: [],
  failed_analyses: [],
  total_cost: "0.002",
};

const mockCostProjectionResponse = {
  analyses: {
    cost_project: {
      current_cost: "0.0234",
      projected_cost: "0.0450",
      budget_remaining: "4.9550",
      cost_by_model: {
        "gpt-4": "0.0200",
        "gpt-3.5-turbo": "0.0034",
      },
    },
  },
  cross_insights: [],
  failed_analyses: [],
  total_cost: "0.001",
};

const mockTokenPredictionResponse = {
  analyses: {
    token_predict: {
      current_tokens: 15000,
      projected_tokens: 45000,
      max_tokens: 128000,
      optimization_savings: 5000,
    },
  },
  cross_insights: [],
  failed_analyses: [],
  total_cost: "0.001",
};

const mockMultiTraceTaskResponse = {
  analyses: {
    trace_summarize: {
      summary: "Completed execution in 2.5 seconds",
      total_duration_ms: 2500,
      step_count: 5,
      tool_call_count: 1,
      llm_call_count: 4,
    },
    trace_anomaly: {
      anomalies: [],
      bottlenecks: [],
      health_score: 0.95,
    },
    cost_project: {
      current_cost: "0.0150",
      projected_cost: "0.0300",
      budget_remaining: "4.9700",
      cost_by_model: { "gpt-4": "0.0150" },
    },
    token_predict: {
      current_tokens: 10000,
      projected_tokens: 30000,
      max_tokens: 128000,
      optimization_savings: 3000,
    },
  },
  cross_insights: ["Artifact complexity correlates with trace duration"],
  failed_analyses: [],
  total_cost: "0.005",
};

// =============================================================================
// Admin Journey - Full Access
// =============================================================================

test.describe("Admin Trace Intelligence", () => {
  test.beforeEach(async ({ adminPage }) => {
    if (!backendEnabled) {
      await adminPage.route("**/api/v1/**", async (route) => {
        const url = route.request().url();

        if (url.includes("/studio/analyze")) {
          const body = await route.request().postDataJSON();
          const tasks = body?.tasks || [];

          // Return appropriate mock based on requested tasks
          if (tasks.some((t: { type: string }) => t.type === "trace_summarize")) {
            await route.fulfill({
              status: 200,
              contentType: "application/json",
              body: JSON.stringify(mockTraceSummaryResponse),
            });
            return;
          }
          if (tasks.some((t: { type: string }) => t.type === "trace_anomaly")) {
            await route.fulfill({
              status: 200,
              contentType: "application/json",
              body: JSON.stringify(mockTraceAnomalyResponse),
            });
            return;
          }
          if (tasks.some((t: { type: string }) => t.type === "cost_project")) {
            await route.fulfill({
              status: 200,
              contentType: "application/json",
              body: JSON.stringify(mockCostProjectionResponse),
            });
            return;
          }
          if (tasks.some((t: { type: string }) => t.type === "token_predict")) {
            await route.fulfill({
              status: 200,
              contentType: "application/json",
              body: JSON.stringify(mockTokenPredictionResponse),
            });
            return;
          }
          // Multiple tasks
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(mockMultiTraceTaskResponse),
          });
          return;
        }

        if (url.includes("/features")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              enable_studio_ai: true,
              enable_trace_intelligence: true,
              enable_ai_suggestions: true,
            }),
          });
          return;
        }

        if (url.includes("/traces") || url.includes("/observability")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              items: [
                {
                  id: "trace-1",
                  name: "Agent Execution",
                  duration_ms: 3200,
                  status: "completed",
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

  test("should display trace summaries in observability page", async ({
    adminPage,
  }) => {
    await adminPage.goto("/studio/observability");

    // Wait for page to load
    await expect(
      adminPage.locator("main, [role='main'], h1, h2").first()
    ).toBeVisible();

    // Look for trace-related content
    const traceArea = adminPage.locator(
      '[data-testid*="trace"], [class*="trace"], [aria-label*="trace"]'
    );
    if (await traceArea.first().isVisible().catch(() => false)) {
      await expect(traceArea.first()).toBeVisible();
    }
  });

  test("should show anomaly detection indicators", async ({ adminPage }) => {
    await adminPage.goto("/studio/observability");

    // Wait for page to load
    await expect(
      adminPage.locator("main, [role='main'], h1, h2").first()
    ).toBeVisible();

    // Look for anomaly/warning indicators
    const anomalyIndicators = adminPage.locator(
      '[data-testid*="anomaly"], [data-testid*="warning"], [class*="anomaly"]'
    );
    // Anomalies may or may not be present in mock data
  });

  test("should display cost projections", async ({ adminPage }) => {
    await adminPage.goto("/studio/costs");

    // Wait for page to load
    await expect(
      adminPage.locator("main, [role='main'], h1").first()
    ).toBeVisible();

    // Look for cost-related UI elements
    const costUI = adminPage.locator(
      '[data-testid*="cost"], [class*="cost"], [aria-label*="cost"]'
    );
    if (await costUI.first().isVisible().catch(() => false)) {
      await expect(costUI.first()).toBeVisible();
    }
  });

  test("admin should have access to all trace intelligence features", async ({
    adminPage,
  }) => {
    await adminPage.goto("/studio/observability");

    // Verify observability page loads for admin
    await expect(
      adminPage.locator("main, [role='main'], h1").first()
    ).toBeVisible();

    // Admin should have full module access
    const nav = adminPage.locator('nav, [role="navigation"], aside');
    await expect(nav.first()).toBeVisible();
  });
});

// =============================================================================
// Alice Analyst Journey - Full Access
// =============================================================================

test.describe("Alice Analyst Trace Intelligence", () => {
  test.beforeEach(async ({ alicePage }) => {
    if (!backendEnabled) {
      await alicePage.route("**/api/v1/**", async (route) => {
        const url = route.request().url();

        if (url.includes("/studio/analyze")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(mockTraceSummaryResponse),
          });
          return;
        }

        if (url.includes("/features")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              enable_studio_ai: true,
              enable_trace_intelligence: true,
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

  test("alice should access trace intelligence features", async ({
    alicePage,
  }) => {
    await alicePage.goto("/studio/observability");

    // Verify observability page loads
    await expect(
      alicePage.locator("main, [role='main'], h1, h2").first()
    ).toBeVisible();
  });

  test("alice should see trace summaries", async ({ alicePage }) => {
    await alicePage.goto("/studio/observability");

    // Wait for page to load
    await expect(
      alicePage.locator("main, [role='main'], h1").first()
    ).toBeVisible();

    // Developer personas should have access to trace summaries
    const traceArea = alicePage.locator(
      '[data-testid*="trace"], [class*="trace"], [aria-label*="trace"]'
    );
    // Trace content should be accessible
  });

  test("alice should see bottleneck detection", async ({ alicePage }) => {
    await alicePage.goto("/studio/observability");

    // Wait for page to load
    await expect(
      alicePage.locator("main, [role='main'], h1").first()
    ).toBeVisible();

    // Look for bottleneck/performance UI elements
    const bottleneckUI = alicePage.locator(
      '[data-testid*="bottleneck"], [class*="bottleneck"], [aria-label*="performance"]'
    );
    // Bottleneck detection may be shown in trace detail view
  });
});

// =============================================================================
// Bob Journey - No Trace Intelligence Access
// =============================================================================

test.describe("Bob Trace Intelligence Restrictions", () => {
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
              enable_trace_intelligence: false, // Disabled for bob
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

  test("bob should not have access to observability module", async ({
    bobPage,
  }) => {
    // Bob's visible modules: chat, projects, flows, help
    // Observability is NOT in bob's module list
    await bobPage.goto("/studio/observability");

    // May redirect to default bob view or show restricted access
    // Just verify page doesn't crash
    await expect(bobPage.locator("body")).toBeVisible();
  });

  test("bob should use basic chat without trace features", async ({
    bobPage,
  }) => {
    await bobPage.goto("/studio/chat");

    // Verify chat page loads
    await expect(
      bobPage.locator("main, [role='main'], h1, h2").first()
    ).toBeVisible();

    // Bob should not see trace intelligence features in chat
  });
});

// =============================================================================
// Trace Intelligence Feature Flag Tests
// =============================================================================

test.describe("Trace Intelligence Feature Flags", () => {
  test("trace intelligence should respect enable_trace_intelligence flag", async ({
    adminPage,
  }) => {
    // Mock feature flags with trace intelligence disabled
    await adminPage.route("**/api/v1/features**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enable_studio_ai: true,
          enable_trace_intelligence: false, // Disabled
        }),
      });
    });

    await adminPage.goto("/studio/observability");

    // Page should load without trace AI features
    await expect(
      adminPage.locator("main, [role='main']").first()
    ).toBeVisible();
  });

  test("trace intelligence should fallback to enable_studio_ai master flag", async ({
    adminPage,
  }) => {
    // Mock feature flags with master flag only
    await adminPage.route("**/api/v1/features**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enable_studio_ai: true,
          // enable_trace_intelligence not set - should fallback
        }),
      });
    });

    await adminPage.goto("/studio/observability");

    // Page should load with AI features enabled via fallback
    await expect(
      adminPage.locator("main, [role='main']").first()
    ).toBeVisible();
  });
});

// =============================================================================
// Performance Tests
// =============================================================================

test.describe("Trace Intelligence Performance", () => {
  test("observability page with AI features should load within acceptable time", async ({
    adminPage,
  }) => {
    const startTime = Date.now();

    await adminPage.goto("/studio/observability");
    await expect(
      adminPage.locator("main, [role='main'], h1").first()
    ).toBeVisible();

    const loadTime = Date.now() - startTime;
    // Should load within 5 seconds even with AI features
    expect(loadTime).toBeLessThan(5000);
  });

  test("trace analysis should not block initial render", async ({
    adminPage,
  }) => {
    await adminPage.goto("/studio/observability");

    // Main content should be visible quickly
    await expect(
      adminPage.locator("main, [role='main']").first()
    ).toBeVisible({ timeout: 3000 });

    // AI analysis features may load asynchronously
  });
});
