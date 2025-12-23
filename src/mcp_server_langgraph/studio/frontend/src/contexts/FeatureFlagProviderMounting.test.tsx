/**
 * FeatureFlagProvider Mounting Test
 *
 * TDD test to ensure FeatureFlagProvider is mounted in main.tsx.
 * This is a critical test because:
 * - StudioShellGuard depends on useFeatureFlag("canvas_studio_shell")
 * - Without FeatureFlagProvider, the guard always returns false
 * - This causes /studio/v2/* routes to redirect to legacy /studio/*
 *
 * Following TDD principles:
 * - RED: Test will fail if FeatureFlagProvider is not in main.tsx
 * - GREEN: Test will pass after adding FeatureFlagProvider
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import * as fs from "fs";
import * as path from "path";

describe("FeatureFlagProvider Mounting", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("should be mounted in main.tsx", () => {
    // Read main.tsx file
    const mainTsxPath = path.resolve(__dirname, "../main.tsx");
    const mainTsxContent = fs.readFileSync(mainTsxPath, "utf-8");

    // Check that FeatureFlagProvider is imported
    const hasImport =
      mainTsxContent.includes("import") &&
      mainTsxContent.includes("FeatureFlagProvider");

    // Check that FeatureFlagProvider is used in the render tree
    const hasUsage = mainTsxContent.includes("<FeatureFlagProvider");

    expect(hasImport).toBe(true);
    expect(hasUsage).toBe(true);
  });

  it("should wrap the Provider (Redux) and RouterProvider", () => {
    const mainTsxPath = path.resolve(__dirname, "../main.tsx");
    const mainTsxContent = fs.readFileSync(mainTsxPath, "utf-8");

    // FeatureFlagProvider needs to be inside Provider (Redux) for RTK Query
    // but outside RouterProvider so route guards can access feature flags
    // Expected hierarchy:
    //   <PreferencesProvider>
    //     <Provider store={store}>
    //       <FeatureFlagProvider>
    //         <RouterProvider router={router} />
    //       </FeatureFlagProvider>
    //     </Provider>
    //   </PreferencesProvider>

    // Check ordering: FeatureFlagProvider should appear before RouterProvider
    const featureFlagIndex = mainTsxContent.indexOf("<FeatureFlagProvider");
    const routerProviderIndex = mainTsxContent.indexOf("<RouterProvider");

    expect(featureFlagIndex).toBeGreaterThan(-1);
    expect(routerProviderIndex).toBeGreaterThan(-1);
    expect(featureFlagIndex).toBeLessThan(routerProviderIndex);
  });
});

describe("studio_shell feature flag", () => {
  it("should be defined in feature flags type", async () => {
    // Read api types file
    const typesPath = path.resolve(__dirname, "../types/api.ts");
    const typesContent = fs.readFileSync(typesPath, "utf-8");

    // Check that studio_shell is defined
    const hasStudioShell = typesContent.includes("studio_shell");

    expect(hasStudioShell).toBe(true);
  });
});
