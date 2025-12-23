/**
 * RootRedirect Tests
 *
 * TDD: Tests written FIRST for feature-flag-aware root redirect.
 *
 * Tests verify:
 * - Redirects to /studio/v2 when canvas_hybrid_shell is enabled
 * - Redirects to /studio when canvas_hybrid_shell is disabled
 * - Shows loading skeleton while feature flags are loading
 * - Fails-open to HybridShell on feature flag API error
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router";
import { RootRedirect } from "./RootRedirect";

// =============================================================================
// Mocks
// =============================================================================

const mockUseFeatureFlags = vi.fn();

vi.mock("../../contexts/FeatureFlagContext", () => ({
  useFeatureFlags: () => mockUseFeatureFlags(),
}));

// =============================================================================
// Test Helpers
// =============================================================================

function renderWithRouter(initialPath: string = "/") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        <Route
          path="/studio/v2"
          element={<div data-testid="hybrid-shell">HybridShell</div>}
        />
        <Route
          path="/studio"
          element={<div data-testid="legacy-studio">Legacy Studio</div>}
        />
      </Routes>
    </MemoryRouter>,
  );
}

// =============================================================================
// Tests
// =============================================================================

describe("RootRedirect", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("loading state", () => {
    it("shows loading skeleton while feature flags are loading", () => {
      mockUseFeatureFlags.mockReturnValue({
        isLoading: true,
        isError: false,
        isEnabled: vi.fn(),
      });

      renderWithRouter();

      expect(screen.getByTestId("root-redirect-loading")).toBeInTheDocument();
      expect(screen.queryByTestId("hybrid-shell")).not.toBeInTheDocument();
      expect(screen.queryByTestId("legacy-studio")).not.toBeInTheDocument();
    });
  });

  describe("feature flag enabled", () => {
    beforeEach(() => {
      mockUseFeatureFlags.mockReturnValue({
        isLoading: false,
        isError: false,
        isEnabled: (flag: string) => flag === "canvas_hybrid_shell",
      });
    });

    it("redirects to /studio/v2 when canvas_hybrid_shell is enabled", () => {
      renderWithRouter();

      expect(screen.getByTestId("hybrid-shell")).toBeInTheDocument();
      expect(screen.queryByTestId("legacy-studio")).not.toBeInTheDocument();
    });
  });

  describe("feature flag disabled", () => {
    beforeEach(() => {
      mockUseFeatureFlags.mockReturnValue({
        isLoading: false,
        isError: false,
        isEnabled: () => false,
      });
    });

    it("redirects to /studio when canvas_hybrid_shell is disabled", () => {
      renderWithRouter();

      expect(screen.getByTestId("legacy-studio")).toBeInTheDocument();
      expect(screen.queryByTestId("hybrid-shell")).not.toBeInTheDocument();
    });
  });

  describe("error handling", () => {
    it("fails-open to HybridShell when feature flag API errors", () => {
      mockUseFeatureFlags.mockReturnValue({
        isLoading: false,
        isError: true,
        isEnabled: vi.fn(),
      });

      renderWithRouter();

      // On error, should fail-open to HybridShell
      expect(screen.getByTestId("hybrid-shell")).toBeInTheDocument();
      expect(screen.queryByTestId("legacy-studio")).not.toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("loading skeleton has proper aria attributes", () => {
      mockUseFeatureFlags.mockReturnValue({
        isLoading: true,
        isError: false,
        isEnabled: vi.fn(),
      });

      renderWithRouter();

      const skeleton = screen.getByTestId("root-redirect-loading");
      expect(skeleton).toHaveAttribute("aria-busy", "true");
      expect(skeleton).toHaveAttribute("aria-label", "Loading...");
    });
  });
});
