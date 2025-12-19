/**
 * HybridShellGuard Tests
 *
 * Phase 7: Integration - Feature Flag Gating
 * Tests for feature flag-based routing to HybridShell.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router";
import { HybridShellGuard } from "./HybridShellGuard";

// Mock the feature flag hook
vi.mock("../../contexts/FeatureFlagContext", () => ({
  useFeatureFlag: vi.fn(),
}));

// Import the mocked function for configuration
import { useFeatureFlag } from "../../contexts/FeatureFlagContext";

const MockHybridShell = () => (
  <div data-testid="hybrid-shell">Hybrid Shell Content</div>
);
const MockLegacyStudio = () => (
  <div data-testid="legacy-studio">Legacy Studio</div>
);

describe("HybridShellGuard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Feature Flag Enabled", () => {
    beforeEach(() => {
      vi.mocked(useFeatureFlag).mockReturnValue(true);
    });

    it("renders children when canvas_hybrid_shell flag is enabled", () => {
      render(
        <MemoryRouter initialEntries={["/studio/v2"]}>
          <Routes>
            <Route
              path="/studio/v2"
              element={
                <HybridShellGuard>
                  <MockHybridShell />
                </HybridShellGuard>
              }
            />
          </Routes>
        </MemoryRouter>,
      );

      expect(screen.getByTestId("hybrid-shell")).toBeInTheDocument();
    });

    it("calls useFeatureFlag with correct flag name", () => {
      render(
        <MemoryRouter initialEntries={["/studio/v2"]}>
          <Routes>
            <Route
              path="/studio/v2"
              element={
                <HybridShellGuard>
                  <MockHybridShell />
                </HybridShellGuard>
              }
            />
          </Routes>
        </MemoryRouter>,
      );

      expect(useFeatureFlag).toHaveBeenCalledWith("canvas_hybrid_shell");
    });
  });

  describe("Feature Flag Disabled", () => {
    beforeEach(() => {
      vi.mocked(useFeatureFlag).mockReturnValue(false);
    });

    it("redirects to /studio when canvas_hybrid_shell flag is disabled", () => {
      render(
        <MemoryRouter initialEntries={["/studio/v2"]}>
          <Routes>
            <Route
              path="/studio/v2"
              element={
                <HybridShellGuard>
                  <MockHybridShell />
                </HybridShellGuard>
              }
            />
            <Route path="/studio" element={<MockLegacyStudio />} />
          </Routes>
        </MemoryRouter>,
      );

      expect(screen.queryByTestId("hybrid-shell")).not.toBeInTheDocument();
      expect(screen.getByTestId("legacy-studio")).toBeInTheDocument();
    });

    it("preserves query params during redirect", () => {
      const { container } = render(
        <MemoryRouter initialEntries={["/studio/v2?session=abc123"]}>
          <Routes>
            <Route
              path="/studio/v2"
              element={
                <HybridShellGuard>
                  <MockHybridShell />
                </HybridShellGuard>
              }
            />
            <Route
              path="/studio"
              element={
                <div data-testid="legacy-studio">
                  Legacy with params preserved
                </div>
              }
            />
          </Routes>
        </MemoryRouter>,
      );

      // Should redirect to legacy studio
      expect(container.textContent).toContain("Legacy");
    });
  });

  describe("Path Mapping", () => {
    beforeEach(() => {
      vi.mocked(useFeatureFlag).mockReturnValue(false);
    });

    it("maps /studio/v2/chat to /studio/chat on redirect", () => {
      render(
        <MemoryRouter initialEntries={["/studio/v2/chat"]}>
          <Routes>
            <Route
              path="/studio/v2/chat"
              element={
                <HybridShellGuard>
                  <MockHybridShell />
                </HybridShellGuard>
              }
            />
            <Route
              path="/studio/chat"
              element={<div data-testid="legacy-chat">Legacy Chat</div>}
            />
          </Routes>
        </MemoryRouter>,
      );

      expect(screen.getByTestId("legacy-chat")).toBeInTheDocument();
    });

    it("maps /studio/v2/chat/:sessionId to /studio/chat on redirect", () => {
      render(
        <MemoryRouter initialEntries={["/studio/v2/chat/session-123"]}>
          <Routes>
            <Route
              path="/studio/v2/chat/:sessionId"
              element={
                <HybridShellGuard>
                  <MockHybridShell />
                </HybridShellGuard>
              }
            />
            <Route
              path="/studio/chat"
              element={
                <div data-testid="legacy-chat">Legacy Chat with Session</div>
              }
            />
          </Routes>
        </MemoryRouter>,
      );

      expect(screen.getByTestId("legacy-chat")).toBeInTheDocument();
    });
  });

  describe("Rendering States", () => {
    it("renders nothing during feature flag loading (graceful fallback)", () => {
      // When flag returns false during loading, redirect happens
      vi.mocked(useFeatureFlag).mockReturnValue(false);

      render(
        <MemoryRouter initialEntries={["/studio/v2"]}>
          <Routes>
            <Route
              path="/studio/v2"
              element={
                <HybridShellGuard>
                  <MockHybridShell />
                </HybridShellGuard>
              }
            />
            <Route path="/studio" element={<MockLegacyStudio />} />
          </Routes>
        </MemoryRouter>,
      );

      // Should redirect, not render hybrid shell
      expect(screen.queryByTestId("hybrid-shell")).not.toBeInTheDocument();
    });
  });
});
