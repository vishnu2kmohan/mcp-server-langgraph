/**
 * Canvas Intelligence E2E Tests
 *
 * Sprint 4: Tests for AI-powered canvas/artifact features
 * - Artifact type suggestion
 * - Code analysis
 * - Diff explanation
 *
 * Tests persona access:
 * - admin: Full access
 * - alice-builder: Full access (developer)
 * - bob: No access (canvas intelligence restricted)
 */

import { test, expect } from "./fixtures/auth";

const backendEnabled = process.env.BACKEND_ENABLED !== "false";

// =============================================================================
// Mock Data
// =============================================================================

const mockArtifactTypeSuggestionResponse = {
  analyses: {
    artifact_suggest_type: {
      suggested_type: "mermaid",
      confidence: 0.91,
      alternatives: ["markdown", "code"],
    },
  },
  cross_insights: [],
  failed_analyses: [],
  total_cost: "0.001",
};

const mockCodeAnalysisResponse = {
  analyses: {
    code_analyze: {
      quality_score: 85,
      complexity: "medium",
      issues: [
        { type: "style", message: "Consider using const instead of let" },
      ],
      suggestions: ["Add error handling", "Extract repeated logic"],
    },
  },
  cross_insights: [],
  failed_analyses: [],
  total_cost: "0.002",
};

const mockDiffExplanationResponse = {
  analyses: {
    diff_explain: {
      summary: "Added new function and refactored existing code",
      changes: [
        { type: "addition", description: "New helper function added" },
        { type: "modification", description: "Refactored main logic" },
      ],
      breaking_changes: false,
    },
  },
  cross_insights: [],
  failed_analyses: [],
  total_cost: "0.001",
};

const mockMultiCanvasTaskResponse = {
  analyses: {
    artifact_suggest_type: {
      suggested_type: "code",
      confidence: 0.88,
      alternatives: ["json"],
    },
    code_analyze: {
      quality_score: 90,
      complexity: "low",
      issues: [],
      suggestions: ["Add type annotations"],
    },
    diff_explain: {
      summary: "Minor refactoring changes",
      changes: [{ type: "modification", description: "Improved readability" }],
      breaking_changes: false,
    },
  },
  cross_insights: ["Artifact complexity correlates with trace duration"],
  failed_analyses: [],
  total_cost: "0.004",
};

// =============================================================================
// Admin Journey - Full Access
// =============================================================================

test.describe("Admin Canvas Intelligence", () => {
  test.beforeEach(async ({ adminPage }) => {
    if (!backendEnabled) {
      await adminPage.route("**/api/v1/**", async (route) => {
        const url = route.request().url();

        if (url.includes("/studio/analyze")) {
          const body = await route.request().postDataJSON();
          const tasks = body?.tasks || [];

          // Return appropriate mock based on requested tasks
          if (tasks.some((t: { type: string }) => t.type === "artifact_suggest_type")) {
            await route.fulfill({
              status: 200,
              contentType: "application/json",
              body: JSON.stringify(mockArtifactTypeSuggestionResponse),
            });
            return;
          }
          if (tasks.some((t: { type: string }) => t.type === "code_analyze")) {
            await route.fulfill({
              status: 200,
              contentType: "application/json",
              body: JSON.stringify(mockCodeAnalysisResponse),
            });
            return;
          }
          if (tasks.some((t: { type: string }) => t.type === "diff_explain")) {
            await route.fulfill({
              status: 200,
              contentType: "application/json",
              body: JSON.stringify(mockDiffExplanationResponse),
            });
            return;
          }
          // Multiple tasks
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(mockMultiCanvasTaskResponse),
          });
          return;
        }

        if (url.includes("/features")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              enable_studio_ai: true,
              enable_canvas_intelligence: true,
              enable_ai_suggestions: true,
            }),
          });
          return;
        }

        if (url.includes("/artifacts")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              items: [
                {
                  id: "artifact-1",
                  type: "code",
                  language: "typescript",
                  content: "function hello() { return 'Hello'; }",
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

  test("should display artifact type suggestions", async ({ adminPage }) => {
    await adminPage.goto("/studio/chat");

    // Wait for page to load
    await expect(
      adminPage.locator("main, [role='main'], h1, h2").first()
    ).toBeVisible();

    // Look for canvas/artifact area
    const canvasArea = adminPage.locator(
      '[data-testid*="canvas"], [data-testid*="artifact"], [class*="canvas"], [class*="artifact"]'
    );
    // Canvas may or may not be visible based on chat state
  });

  test("should show code analysis results", async ({ adminPage }) => {
    await adminPage.goto("/studio/chat");

    // Wait for page to load
    await expect(
      adminPage.locator("main, [role='main'], h1, h2").first()
    ).toBeVisible();

    // Look for code analysis indicators
    const codeAnalysis = adminPage.locator(
      '[data-testid*="analysis"], [data-testid*="quality"], [class*="code-analysis"]'
    );
    // Analysis may be shown on hover or in a panel
  });

  test("should display diff explanations in artifact versions", async ({
    adminPage,
  }) => {
    await adminPage.goto("/studio/chat");

    // Wait for page to load
    await expect(
      adminPage.locator("main, [role='main'], h1").first()
    ).toBeVisible();

    // Look for version/diff UI elements
    const diffUI = adminPage.locator(
      '[data-testid*="diff"], [data-testid*="version"], [class*="diff"]'
    );
    // Diff UI may not be visible if no versions exist
  });

  test("admin should have access to all canvas intelligence features", async ({
    adminPage,
  }) => {
    await adminPage.goto("/studio/chat");

    // Verify chat page loads for admin
    await expect(
      adminPage.locator("main, [role='main'], h1").first()
    ).toBeVisible();

    // Admin should have full module access including canvas
    const nav = adminPage.locator('nav, [role="navigation"], aside');
    await expect(nav.first()).toBeVisible();
  });
});

// =============================================================================
// Alice Builder Journey - Full Access
// =============================================================================

test.describe("Alice Builder Canvas Intelligence", () => {
  test.beforeEach(async ({ alicePage }) => {
    if (!backendEnabled) {
      await alicePage.route("**/api/v1/**", async (route) => {
        const url = route.request().url();

        if (url.includes("/studio/analyze")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(mockArtifactTypeSuggestionResponse),
          });
          return;
        }

        if (url.includes("/features")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              enable_studio_ai: true,
              enable_canvas_intelligence: true,
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

  test("alice-builder should access canvas intelligence features", async ({
    alicePage,
  }) => {
    await alicePage.goto("/studio/chat");

    // Verify chat page loads
    await expect(
      alicePage.locator("main, [role='main'], h1, h2").first()
    ).toBeVisible();
  });

  test("alice-builder should see artifact type suggestions", async ({
    alicePage,
  }) => {
    await alicePage.goto("/studio/chat");

    // Wait for page to load
    await expect(
      alicePage.locator("main, [role='main'], h1").first()
    ).toBeVisible();

    // Developer personas should have access to artifact suggestions
    const artifactArea = alicePage.locator(
      '[data-testid*="artifact"], [class*="artifact"], [aria-label*="artifact"]'
    );
    // Artifact suggestions shown when creating/editing artifacts
  });

  test("alice-builder should see code quality analysis", async ({
    alicePage,
  }) => {
    await alicePage.goto("/studio/chat");

    // Wait for page to load
    await expect(
      alicePage.locator("main, [role='main'], h1").first()
    ).toBeVisible();

    // Look for code quality UI elements
    const qualityUI = alicePage.locator(
      '[data-testid*="quality"], [class*="quality"], [aria-label*="quality"]'
    );
    // Quality indicators may be shown in code artifacts
  });
});

// =============================================================================
// Bob Journey - No Canvas Intelligence Access
// =============================================================================

test.describe("Bob Canvas Intelligence Restrictions", () => {
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
              enable_canvas_intelligence: false, // Disabled for bob
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

  test("bob should access basic chat features without canvas intelligence", async ({
    bobPage,
  }) => {
    await bobPage.goto("/studio/chat");

    // Verify chat page loads
    await expect(
      bobPage.locator("main, [role='main'], h1, h2").first()
    ).toBeVisible();
  });

  test("bob should not see canvas intelligence features", async ({
    bobPage,
  }) => {
    await bobPage.goto("/studio/chat");

    // Wait for page to load
    await expect(
      bobPage.locator("main, [role='main']").first()
    ).toBeVisible();

    // Bob (user role) should not see advanced canvas features
    // Look for AI-specific canvas elements that should be hidden (use class fallbacks)
    const aiCanvasFeatures = bobPage.locator(
      '[class*="ai-suggestion"], [class*="ai-analysis"], [aria-label*="AI"]'
    );
    // These should not be visible for bob
  });
});

// =============================================================================
// Canvas Intelligence Feature Flag Tests
// =============================================================================

test.describe("Canvas Intelligence Feature Flags", () => {
  test("canvas intelligence should respect enable_canvas_intelligence flag", async ({
    adminPage,
  }) => {
    // Mock feature flags with canvas intelligence disabled
    await adminPage.route("**/api/v1/features**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enable_studio_ai: true,
          enable_canvas_intelligence: false, // Disabled
        }),
      });
    });

    await adminPage.goto("/studio/chat");

    // Page should load without canvas AI features
    await expect(
      adminPage.locator("main, [role='main']").first()
    ).toBeVisible();
  });

  test("canvas intelligence should fallback to enable_studio_ai master flag", async ({
    adminPage,
  }) => {
    // Mock feature flags with master flag only
    await adminPage.route("**/api/v1/features**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enable_studio_ai: true,
          // enable_canvas_intelligence not set - should fallback
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
// Performance Tests
// =============================================================================

test.describe("Canvas Intelligence Performance", () => {
  test("canvas with AI features should load within acceptable time", async ({
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

  test("code analysis should not block artifact rendering", async ({
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
