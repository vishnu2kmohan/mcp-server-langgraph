/**
 * Hook + Component Integration Tests
 *
 * Sprint 3-4: Integration tests for hook+component combinations
 *
 * Tests that hooks and their consuming components work together correctly:
 * - useNudges + NudgeTooltip
 * - useOfflineQueue + OfflineBanner
 * - useAIErrorRecovery + ErrorRecoveryPanel
 * - useProgressiveDisclosure + UI controls
 *
 * These tests validate the data flow from hooks to rendered UI.
 */

import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  waitFor,
  fireEvent,
  cleanup,
} from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { MemoryRouter } from "react-router";
import { http, HttpResponse, delay } from "msw";
import { server } from "../mocks/server";

// Hooks
import { useNudges, type Nudge } from "../hooks/useNudges";
import { useProgressiveDisclosure } from "../hooks/useProgressiveDisclosure";

// Components
import { NudgeTooltip } from "../components/Nudge";
import { ErrorRecoveryPanel } from "../components/ErrorRecovery";
import { OfflineBanner } from "../components/OfflineBanner";

// Slices
import disclosureReducer from "../store/slices/disclosureSlice";
import { api } from "../api";

// =============================================================================
// Test Setup
// =============================================================================

const createTestStore = () =>
  configureStore({
    reducer: {
      disclosure: disclosureReducer,
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });

const TestWrapper = ({
  children,
  store = createTestStore(),
}: {
  children: React.ReactNode;
  store?: ReturnType<typeof createTestStore>;
}) => (
  <MemoryRouter>
    <Provider store={store}>{children}</Provider>
  </MemoryRouter>
);

// =============================================================================
// useNudges + NudgeTooltip Integration
// =============================================================================

describe("useNudges + NudgeTooltip Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    cleanup();
    server.resetHandlers();
  });

  it("displays nudge from hook in NudgeTooltip component", async () => {
    // Setup mock nudge recommendation
    const mockNudge: Nudge = {
      id: "keyboard-shortcuts",
      type: "tooltip",
      targetElement: "[data-testid='search']",
      message: "Pro tip: Press Cmd+K for quick search",
      priority: "medium",
      category: "productivity",
      showAfterMs: 0,
    };

    server.use(
      http.post("/api/v1/ai/nudges/recommend", async () => {
        return HttpResponse.json({
          should_show: true,
          nudge: mockNudge,
          confidence: 0.88,
        });
      }),
    );

    // Component that integrates hook with component
    function NudgeIntegration() {
      const { activeNudge, dismiss, trackAcceptance } = useNudges({
        enableAI: true,
        pageContext: "/studio/chat",
      });

      if (!activeNudge) return <div data-testid="no-nudge">No nudge</div>;

      return (
        <NudgeTooltip
          nudge={activeNudge}
          onDismiss={() => dismiss(activeNudge.id)}
          onAccept={() => trackAcceptance(activeNudge.id)}
        />
      );
    }

    render(<NudgeIntegration />, { wrapper: TestWrapper });

    // Wait for nudge to appear
    await waitFor(
      () => {
        expect(screen.getByRole("tooltip")).toBeInTheDocument();
      },
      { timeout: 3000 },
    );

    // Verify nudge content
    expect(screen.getByText(/pro tip/i)).toBeInTheDocument();
  });

  it("removes nudge when dismissed via NudgeTooltip", async () => {
    const mockNudge: Nudge = {
      id: "feature-hint",
      type: "tooltip",
      message: "Try this new feature!",
      priority: "low",
      category: "feature-discovery",
      showAfterMs: 0,
    };

    server.use(
      http.post("/api/v1/ai/nudges/recommend", async () => {
        return HttpResponse.json({
          should_show: true,
          nudge: mockNudge,
          confidence: 0.85,
        });
      }),
    );

    function NudgeIntegration() {
      const { activeNudge, dismiss, trackAcceptance } = useNudges({
        enableAI: true,
        pageContext: "/studio/chat",
      });

      if (!activeNudge) return <div data-testid="no-nudge">No nudge</div>;

      return (
        <NudgeTooltip
          nudge={activeNudge}
          onDismiss={() => dismiss(activeNudge.id)}
          onAccept={() => trackAcceptance(activeNudge.id)}
        />
      );
    }

    render(<NudgeIntegration />, { wrapper: TestWrapper });

    // Wait for nudge
    await waitFor(() => {
      expect(screen.getByRole("tooltip")).toBeInTheDocument();
    });

    // Click dismiss
    const dismissButton = screen.getByRole("button", { name: /dismiss/i });
    fireEvent.click(dismissButton);

    // Nudge should be removed
    await waitFor(() => {
      expect(screen.getByTestId("no-nudge")).toBeInTheDocument();
    });
  });

  it("tracks acceptance when nudge accepted via NudgeTooltip", async () => {
    const mockNudge: Nudge = {
      id: "accept-test",
      type: "tooltip",
      message: "Click to accept",
      priority: "medium",
      category: "test",
      showAfterMs: 0,
    };

    server.use(
      http.post("/api/v1/ai/nudges/recommend", async () => {
        return HttpResponse.json({
          should_show: true,
          nudge: mockNudge,
          confidence: 0.9,
        });
      }),
    );

    function NudgeIntegration() {
      const { activeNudge, dismiss, trackAcceptance, getNudgeHistory } =
        useNudges({
          enableAI: true,
          pageContext: "/studio/chat",
        });

      if (!activeNudge) {
        const history = getNudgeHistory();
        const acceptedCount = history.filter(
          (h) => h.action === "accepted",
        ).length;
        return <div data-testid="accepted-count">{acceptedCount}</div>;
      }

      return (
        <NudgeTooltip
          nudge={activeNudge}
          onDismiss={() => dismiss(activeNudge.id)}
          onAccept={() => trackAcceptance(activeNudge.id)}
        />
      );
    }

    render(<NudgeIntegration />, { wrapper: TestWrapper });

    // Wait for nudge
    await waitFor(() => {
      expect(screen.getByRole("tooltip")).toBeInTheDocument();
    });

    // Click accept
    const acceptButton = screen.getByRole("button", { name: /got it/i });
    fireEvent.click(acceptButton);

    // Check history was updated
    await waitFor(() => {
      expect(screen.getByTestId("accepted-count")).toHaveTextContent("1");
    });
  });
});

// =============================================================================
// useAIErrorRecovery + ErrorRecoveryPanel Integration
// =============================================================================

describe("useAIErrorRecovery + ErrorRecoveryPanel Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    server.resetHandlers();
  });

  it("displays AI-analyzed error in ErrorRecoveryPanel", async () => {
    // Use backend response format (RTK Query endpoint format)
    server.use(
      http.post("/api/v1/ai/errors/analyze", async () => {
        await delay(50);
        return HttpResponse.json({
          error_type: "network",
          recovery_steps: [
            {
              step_number: 1,
              title: "Try again",
              description: "Wait and retry the request",
              action_type: "automatic",
            },
          ],
          auto_recoverable: true,
          suggested_action: "The server took too long to respond",
          confidence: 0.95,
        });
      }),
    );

    const testError = new Error("Request timeout");
    const store = createTestStore();

    render(
      <Provider store={store}>
        <ErrorRecoveryPanel error={testError} testId="error-panel" />
      </Provider>,
    );

    // Wait for analysis
    await waitFor(
      () => {
        expect(screen.queryByText(/analyzing/i)).not.toBeInTheDocument();
      },
      { timeout: 3000 },
    );

    // Verify classification is shown
    expect(screen.getByText(/network/i)).toBeInTheDocument();
    expect(screen.getByText(/too long to respond/i)).toBeInTheDocument();
  });

  it("calls onRetry when retry suggestion clicked", async () => {
    const onRetry = vi.fn();

    // Use backend response format (RTK Query endpoint format)
    server.use(
      http.post("/api/v1/ai/errors/analyze", async () => {
        return HttpResponse.json({
          error_type: "server",
          recovery_steps: [
            {
              step_number: 1,
              title: "Try again",
              description: "Retry the request",
              action_type: "automatic",
            },
          ],
          auto_recoverable: true,
          suggested_action: "Server error occurred",
          confidence: 0.9,
        });
      }),
    );

    const testError = new Error("Server error");
    const store = createTestStore();

    render(
      <Provider store={store}>
        <ErrorRecoveryPanel
          error={testError}
          onRetry={onRetry}
          testId="error-panel"
        />
      </Provider>,
    );

    // Wait for analysis
    await waitFor(() => {
      expect(screen.queryByText(/analyzing/i)).not.toBeInTheDocument();
    });

    // Click retry
    const retryButton = screen.getByRole("button", { name: /try again/i });
    fireEvent.click(retryButton);

    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});

// =============================================================================
// OfflineBanner Component Integration
// =============================================================================

describe("OfflineBanner Component Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows sync button when there are pending actions", async () => {
    const onSync = vi.fn();

    render(
      <OfflineBanner
        isOffline={true}
        pendingCount={5}
        onSync={onSync}
        testId="offline-banner"
      />,
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/5/)).toBeInTheDocument();
    expect(screen.getByText(/pending/i)).toBeInTheDocument();

    const syncButton = screen.getByRole("button", { name: /sync/i });
    expect(syncButton).toBeInTheDocument();

    fireEvent.click(syncButton);
    expect(onSync).toHaveBeenCalledTimes(1);
  });

  it("hides when online with no pending actions", () => {
    render(
      <OfflineBanner
        isOffline={false}
        pendingCount={0}
        testId="offline-banner"
      />,
    );

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("disables sync button when syncing", () => {
    const onSync = vi.fn();

    render(
      <OfflineBanner
        isOffline={true}
        pendingCount={3}
        onSync={onSync}
        isSyncing={true}
        testId="offline-banner"
      />,
    );

    const syncButton = screen.getByRole("button", { name: /syncing/i });
    expect(syncButton).toBeDisabled();
  });
});

// =============================================================================
// useProgressiveDisclosure Integration
// =============================================================================

describe("useProgressiveDisclosure Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("tracks user level and provides level-appropriate features", async () => {
    const store = createTestStore();

    function DisclosureIntegration() {
      const {
        level,
        setLevel,
        shouldShow,
        featureUsageCount,
        trackFeatureUse,
      } = useProgressiveDisclosure();

      return (
        <div>
          <span data-testid="current-level">{level}</span>
          <span data-testid="feature-usage">{String(featureUsageCount)}</span>
          <button onClick={trackFeatureUse}>Track Usage</button>
          <button onClick={() => setLevel("intermediate")}>Level Up</button>
          {shouldShow("advanced") && (
            <div data-testid="advanced-feature">Advanced Feature</div>
          )}
        </div>
      );
    }

    render(
      <TestWrapper store={store}>
        <DisclosureIntegration />
      </TestWrapper>,
    );

    // Initial level is beginner
    await waitFor(() => {
      expect(screen.getByTestId("current-level")).toHaveTextContent("beginner");
    });
    // featureUsageCount is 0 initially - use toString to ensure "0" is displayed
    const usageElement = screen.getByTestId("feature-usage");
    expect(usageElement.textContent).toBe("0");

    // Track feature usage
    fireEvent.click(screen.getByText("Track Usage"));

    await waitFor(() => {
      expect(screen.getByTestId("feature-usage")).toHaveTextContent("1");
    });

    // Level up
    fireEvent.click(screen.getByText("Level Up"));

    await waitFor(() => {
      expect(screen.getByTestId("current-level")).toHaveTextContent(
        "intermediate",
      );
    });
  });
});
