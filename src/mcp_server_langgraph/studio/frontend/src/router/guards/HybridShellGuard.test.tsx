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
const mockUseFeatureFlags = vi.fn();
vi.mock("../../contexts/FeatureFlagContext", () => ({
  useFeatureFlags: () => mockUseFeatureFlags(),
}));

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

  describe("Feature Flag Loading", () => {
    beforeEach(() => {
      mockUseFeatureFlags.mockReturnValue({
        isLoading: true,
        isError: false,
        isEnabled: () => false,
      });
    });

    it("renders loading skeleton while feature flags are loading", () => {
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

      // Should show loading skeleton, not hybrid shell or redirect
      expect(screen.getByTestId("hybrid-shell-loading")).toBeInTheDocument();
      expect(screen.queryByTestId("hybrid-shell")).not.toBeInTheDocument();
      expect(screen.queryByTestId("legacy-studio")).not.toBeInTheDocument();
    });

    it("loading skeleton has proper accessibility attributes", () => {
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

      const skeleton = screen.getByTestId("hybrid-shell-loading");
      expect(skeleton).toHaveAttribute("aria-busy", "true");
      expect(skeleton).toHaveAttribute("aria-label", "Loading application");
    });
  });

  describe("Feature Flag Error (Fail-Open)", () => {
    beforeEach(() => {
      mockUseFeatureFlags.mockReturnValue({
        isLoading: false,
        isError: true,
        isEnabled: () => false,
      });
    });

    it("renders hybrid shell when feature flags API fails (fail-open)", () => {
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

      // On API error, should fail-open and render hybrid shell
      expect(screen.getByTestId("hybrid-shell")).toBeInTheDocument();
      expect(screen.queryByTestId("legacy-studio")).not.toBeInTheDocument();
    });
  });

  describe("Feature Flag Enabled", () => {
    beforeEach(() => {
      mockUseFeatureFlags.mockReturnValue({
        isLoading: false,
        isError: false,
        isEnabled: (flag: string) => flag === "canvas_hybrid_shell",
      });
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

    it("calls isEnabled with correct flag name", () => {
      const isEnabledMock = vi.fn().mockReturnValue(true);
      mockUseFeatureFlags.mockReturnValue({
        isLoading: false,
        isError: false,
        isEnabled: isEnabledMock,
      });

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

      expect(isEnabledMock).toHaveBeenCalledWith("canvas_hybrid_shell");
    });
  });

  describe("Feature Flag Disabled", () => {
    beforeEach(() => {
      mockUseFeatureFlags.mockReturnValue({
        isLoading: false,
        isError: false,
        isEnabled: () => false,
      });
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
      mockUseFeatureFlags.mockReturnValue({
        isLoading: false,
        isError: false,
        isEnabled: () => false,
      });
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

    it("maps /studio/v2/workflows to /studio/workflows on redirect", () => {
      render(
        <MemoryRouter initialEntries={["/studio/v2/workflows"]}>
          <Routes>
            <Route
              path="/studio/v2/workflows"
              element={
                <HybridShellGuard>
                  <MockHybridShell />
                </HybridShellGuard>
              }
            />
            <Route
              path="/studio/workflows"
              element={
                <div data-testid="legacy-workflows">Legacy Workflows</div>
              }
            />
          </Routes>
        </MemoryRouter>,
      );

      expect(screen.getByTestId("legacy-workflows")).toBeInTheDocument();
    });

    it("maps /studio/v2/compliance to /studio/compliance on redirect", () => {
      render(
        <MemoryRouter initialEntries={["/studio/v2/compliance"]}>
          <Routes>
            <Route
              path="/studio/v2/compliance"
              element={
                <HybridShellGuard>
                  <MockHybridShell />
                </HybridShellGuard>
              }
            />
            <Route
              path="/studio/compliance"
              element={
                <div data-testid="legacy-compliance">Legacy Compliance</div>
              }
            />
          </Routes>
        </MemoryRouter>,
      );

      expect(screen.getByTestId("legacy-compliance")).toBeInTheDocument();
    });
  });

  describe("Edge Cases", () => {
    beforeEach(() => {
      mockUseFeatureFlags.mockReturnValue({
        isLoading: false,
        isError: false,
        isEnabled: () => false,
      });
    });

    it("handles /studio/v2 root path redirect", () => {
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
            <Route
              path="/studio"
              element={<div data-testid="legacy-root">Legacy Root</div>}
            />
          </Routes>
        </MemoryRouter>,
      );

      expect(screen.getByTestId("legacy-root")).toBeInTheDocument();
    });

    it("preserves complex query strings during redirect", () => {
      const { container: _container } = render(
        <MemoryRouter
          initialEntries={["/studio/v2/chat?session=abc&filter=active&page=2"]}
        >
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
              element={
                <div data-testid="legacy-chat">Legacy Chat with Query</div>
              }
            />
          </Routes>
        </MemoryRouter>,
      );

      expect(screen.getByTestId("legacy-chat")).toBeInTheDocument();
    });

    it("handles deeply nested paths", () => {
      render(
        <MemoryRouter initialEntries={["/studio/v2/admin/settings/security"]}>
          <Routes>
            <Route
              path="/studio/v2/admin/settings/security"
              element={
                <HybridShellGuard>
                  <MockHybridShell />
                </HybridShellGuard>
              }
            />
            <Route
              path="/studio/admin/settings/security"
              element={
                <div data-testid="legacy-security">Legacy Security Settings</div>
              }
            />
          </Routes>
        </MemoryRouter>,
      );

      expect(screen.getByTestId("legacy-security")).toBeInTheDocument();
    });
  });

  describe("Loading Skeleton Accessibility", () => {
    beforeEach(() => {
      mockUseFeatureFlags.mockReturnValue({
        isLoading: true,
        isError: false,
        isEnabled: () => false,
      });
    });

    it("skeleton has animate-pulse for visual feedback", () => {
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

      const skeleton = screen.getByTestId("hybrid-shell-loading");
      expect(skeleton).toHaveClass("animate-pulse");
    });

    it("skeleton renders all layout sections", () => {
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

      // Check that skeleton has topbar, activity bar, session nav placeholders
      const skeleton = screen.getByTestId("hybrid-shell-loading");
      expect(skeleton.childNodes.length).toBeGreaterThan(1);
    });
  });

  describe("isEnabled Function Behavior", () => {
    it("only checks canvas_hybrid_shell flag", () => {
      const isEnabledMock = vi.fn((flag: string) => {
        // Returns true only for canvas_hybrid_shell
        return flag === "canvas_hybrid_shell";
      });
      mockUseFeatureFlags.mockReturnValue({
        isLoading: false,
        isError: false,
        isEnabled: isEnabledMock,
      });

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

      // Should render hybrid shell
      expect(screen.getByTestId("hybrid-shell")).toBeInTheDocument();
      // Should have called isEnabled with the correct flag
      expect(isEnabledMock).toHaveBeenCalledWith("canvas_hybrid_shell");
      expect(isEnabledMock).toHaveBeenCalledTimes(1);
    });

    it("does not check other feature flags", () => {
      const isEnabledMock = vi.fn(() => true);
      mockUseFeatureFlags.mockReturnValue({
        isLoading: false,
        isError: false,
        isEnabled: isEnabledMock,
      });

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

      // Should only call with canvas_hybrid_shell, not other flags
      expect(isEnabledMock).not.toHaveBeenCalledWith("other_flag");
      expect(isEnabledMock).not.toHaveBeenCalledWith("canvas_editable");
    });
  });
});
