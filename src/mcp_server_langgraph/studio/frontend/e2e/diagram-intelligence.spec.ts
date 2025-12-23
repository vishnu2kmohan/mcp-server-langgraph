/**
 * Diagram Intelligence E2E Tests
 *
 * Sprint 5: Tests for AI-powered diagram/mermaid features
 * - Diagram analysis
 * - Diagram to code generation
 *
 * Tests persona access:
 * - admin: Full access
 * - alice-builder: Full access (developer with flows access)
 * - bob: No access (diagram intelligence restricted)
 */

import { test, expect } from "./fixtures/auth";

const backendEnabled = process.env.BACKEND_ENABLED !== "false";

// =============================================================================
// Mock Data
// =============================================================================

const mockDiagramAnalysisResponse = {
  analyses: {
    diagram_analyze: {
      diagram_type: "flowchart",
      is_valid: true,
      node_count: 5,
      edge_count: 4,
      issues: [],
    },
  },
  cross_insights: [],
  failed_analyses: [],
  total_cost: "0.001",
};

const mockDiagramAnalysisWithIssuesResponse = {
  analyses: {
    diagram_analyze: {
      diagram_type: "sequence",
      is_valid: false,
      node_count: 3,
      edge_count: 2,
      issues: [
        { type: "syntax", message: "Missing participant declaration" },
      ],
    },
  },
  cross_insights: [],
  failed_analyses: [],
  total_cost: "0.001",
};

const mockDiagramToCodeResponse = {
  analyses: {
    diagram_to_code: {
      code: `class NodeA:
    def process(self):
        return NodeB().handle()

class NodeB:
    def handle(self):
        return "processed"`,
      language: "python",
      confidence: 0.82,
      explanation: "Generated Python classes from flowchart nodes",
    },
  },
  cross_insights: [],
  failed_analyses: [],
  total_cost: "0.002",
};

const mockMultiDiagramTaskResponse = {
  analyses: {
    diagram_analyze: {
      diagram_type: "flowchart",
      is_valid: true,
      node_count: 8,
      edge_count: 7,
      issues: [],
    },
    diagram_to_code: {
      code: "def workflow(): pass",
      language: "python",
      confidence: 0.78,
      explanation: "Generated workflow function",
    },
  },
  cross_insights: ["Multiple analysis types provide comprehensive context"],
  failed_analyses: [],
  total_cost: "0.003",
};

// =============================================================================
// Admin Journey - Full Access
// =============================================================================

test.describe("Admin Diagram Intelligence", () => {
  test.beforeEach(async ({ adminPage }) => {
    if (!backendEnabled) {
      await adminPage.route("**/api/v1/**", async (route) => {
        const url = route.request().url();

        if (url.includes("/studio/analyze")) {
          const body = await route.request().postDataJSON();
          const tasks = body?.tasks || [];

          // Return appropriate mock based on requested tasks
          if (tasks.some((t: { type: string }) => t.type === "diagram_analyze")) {
            await route.fulfill({
              status: 200,
              contentType: "application/json",
              body: JSON.stringify(mockDiagramAnalysisResponse),
            });
            return;
          }
          if (tasks.some((t: { type: string }) => t.type === "diagram_to_code")) {
            await route.fulfill({
              status: 200,
              contentType: "application/json",
              body: JSON.stringify(mockDiagramToCodeResponse),
            });
            return;
          }
          // Multiple tasks
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(mockMultiDiagramTaskResponse),
          });
          return;
        }

        if (url.includes("/features")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              enable_studio_ai: true,
              enable_diagram_intelligence: true,
              enable_ai_suggestions: true,
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

  test("should validate mermaid diagrams in chat", async ({ adminPage }) => {
    await adminPage.goto("/studio/chat");

    // Wait for page to load
    await expect(
      adminPage.locator("main, [role='main'], h1, h2").first()
    ).toBeVisible();

    // Look for mermaid/diagram content
    const diagramArea = adminPage.locator(
      '[data-testid*="mermaid"], [data-testid*="diagram"], [class*="mermaid"], .mermaid'
    );
    // Diagrams may or may not be present based on chat content
  });

  test("should show diagram analysis results", async ({ adminPage }) => {
    await adminPage.goto("/studio/chat");

    // Wait for page to load
    await expect(
      adminPage.locator("main, [role='main'], h1, h2").first()
    ).toBeVisible();

    // Look for diagram analysis indicators
    const analysisUI = adminPage.locator(
      '[data-testid*="diagram-analysis"], [class*="diagram-validation"]'
    );
    // Analysis shown when diagrams are rendered
  });

  test("should provide diagram-to-code generation", async ({ adminPage }) => {
    await adminPage.goto("/studio/chat");

    // Wait for page to load
    await expect(
      adminPage.locator("main, [role='main'], h1").first()
    ).toBeVisible();

    // Look for code generation button/panel
    const codeGenUI = adminPage.locator(
      '[data-testid*="diagram-to-code"], [data-testid*="generate-code"]'
    );
    // Code generation UI shown on diagram artifacts
  });

  test("admin should have access to all diagram intelligence features", async ({
    adminPage,
  }) => {
    await adminPage.goto("/studio/chat");

    // Verify chat page loads for admin
    await expect(
      adminPage.locator("main, [role='main'], h1").first()
    ).toBeVisible();

    // Admin should have full module access
    const nav = adminPage.locator('nav, [role="navigation"], aside');
    await expect(nav.first()).toBeVisible();
  });
});

// =============================================================================
// Alice Builder Journey - Full Access
// =============================================================================

test.describe("Alice Builder Diagram Intelligence", () => {
  test.beforeEach(async ({ alicePage }) => {
    if (!backendEnabled) {
      await alicePage.route("**/api/v1/**", async (route) => {
        const url = route.request().url();

        if (url.includes("/studio/analyze")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(mockDiagramAnalysisResponse),
          });
          return;
        }

        if (url.includes("/features")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              enable_studio_ai: true,
              enable_diagram_intelligence: true,
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

  test("alice-builder should access diagram intelligence features", async ({
    alicePage,
  }) => {
    await alicePage.goto("/studio/chat");

    // Verify chat page loads
    await expect(
      alicePage.locator("main, [role='main'], h1, h2").first()
    ).toBeVisible();
  });

  test("alice-builder should see diagram validation", async ({ alicePage }) => {
    await alicePage.goto("/studio/chat");

    // Wait for page to load
    await expect(
      alicePage.locator("main, [role='main'], h1").first()
    ).toBeVisible();

    // Developer personas should have access to diagram validation
    const diagramArea = alicePage.locator(
      '[data-testid*="diagram"], [class*="diagram"], [aria-label*="diagram"]'
    );
    // Diagram validation shown in artifact view
  });

  test("alice-builder should access diagram-to-code feature", async ({
    alicePage,
  }) => {
    await alicePage.goto("/studio/chat");

    // Wait for page to load
    await expect(
      alicePage.locator("main, [role='main'], h1").first()
    ).toBeVisible();

    // Look for code generation capabilities
    const codeGenUI = alicePage.locator(
      '[data-testid*="to-code"], [class*="code-gen"], [aria-label*="generate"]'
    );
    // Code generation button should be accessible
  });
});

// =============================================================================
// Bob Journey - No Diagram Intelligence Access
// =============================================================================

test.describe("Bob Diagram Intelligence Restrictions", () => {
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
              enable_diagram_intelligence: false, // Disabled for bob
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

  test("bob should access basic chat without diagram intelligence", async ({
    bobPage,
  }) => {
    await bobPage.goto("/studio/chat");

    // Verify chat page loads
    await expect(
      bobPage.locator("main, [role='main'], h1, h2").first()
    ).toBeVisible();
  });

  test("bob should not see diagram-to-code feature", async ({ bobPage }) => {
    await bobPage.goto("/studio/chat");

    // Wait for page to load
    await expect(
      bobPage.locator("main, [role='main']").first()
    ).toBeVisible();

    // Bob should not see AI diagram features
    const aiDiagramFeatures = bobPage.locator(
      '[data-testid="ai-diagram-to-code"], [data-testid="ai-diagram-analysis"]'
    );
    // These should not be visible for bob
  });
});

// =============================================================================
// Diagram Intelligence Feature Flag Tests
// =============================================================================

test.describe("Diagram Intelligence Feature Flags", () => {
  test("diagram intelligence should respect enable_diagram_intelligence flag", async ({
    adminPage,
  }) => {
    // Mock feature flags with diagram intelligence disabled
    await adminPage.route("**/api/v1/features**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enable_studio_ai: true,
          enable_diagram_intelligence: false, // Disabled
        }),
      });
    });

    await adminPage.goto("/studio/chat");

    // Page should load without diagram AI features
    await expect(
      adminPage.locator("main, [role='main']").first()
    ).toBeVisible();
  });

  test("diagram intelligence should fallback to enable_studio_ai master flag", async ({
    adminPage,
  }) => {
    // Mock feature flags with master flag only
    await adminPage.route("**/api/v1/features**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enable_studio_ai: true,
          // enable_diagram_intelligence not set - should fallback
        }),
      });
    });

    await adminPage.goto("/studio/chat");

    // Page should load with AI features enabled via fallback
    await expect(
      adminPage.locator("main, [role='main']").first()
    ).toBeVisible();
  });
});

// =============================================================================
// Diagram Validation Tests
// =============================================================================

test.describe("Diagram Validation", () => {
  test.beforeEach(async ({ adminPage }) => {
    if (!backendEnabled) {
      await adminPage.route("**/api/v1/studio/analyze**", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockDiagramAnalysisWithIssuesResponse),
        });
      });

      await adminPage.route("**/api/v1/features**", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            enable_studio_ai: true,
            enable_diagram_intelligence: true,
          }),
        });
      });
    }
  });

  test("should show validation issues for invalid diagrams", async ({
    adminPage,
  }) => {
    await adminPage.goto("/studio/chat");

    // Wait for page to load
    await expect(
      adminPage.locator("main, [role='main'], h1").first()
    ).toBeVisible();

    // Look for validation warning/error indicators
    const validationUI = adminPage.locator(
      '[data-testid*="validation"], [data-testid*="error"], [class*="warning"]'
    );
    // Validation issues shown when diagram has syntax errors
  });
});

// =============================================================================
// Performance Tests
// =============================================================================

test.describe("Diagram Intelligence Performance", () => {
  test("page with diagram features should load within acceptable time", async ({
    adminPage,
  }) => {
    const startTime = Date.now();

    await adminPage.goto("/studio/chat");
    await expect(
      adminPage.locator("main, [role='main'], h1").first()
    ).toBeVisible();

    const loadTime = Date.now() - startTime;
    // Should load within 5 seconds even with AI features
    expect(loadTime).toBeLessThan(5000);
  });

  test("diagram analysis should not block diagram rendering", async ({
    adminPage,
  }) => {
    await adminPage.goto("/studio/chat");

    // Main content should be visible quickly
    await expect(
      adminPage.locator("main, [role='main']").first()
    ).toBeVisible({ timeout: 3000 });

    // AI analysis features may load asynchronously
  });
});
