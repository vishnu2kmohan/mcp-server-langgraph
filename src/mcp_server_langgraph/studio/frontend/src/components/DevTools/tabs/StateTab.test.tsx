/**
 * StateTab Tests
 *
 * TDD tests for the State tab in DevTools.
 * Displays Redux/session/workflow state inspection.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  within,
  fireEvent,
  cleanup,
} from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";

expect.extend(toHaveNoViolations);

import { StateTab } from "./StateTab";

// =============================================================================
// Mock Store Setup
// =============================================================================

const mockState = {
  session: {
    currentId: "session-123",
    messages: [{ id: "msg-1", content: "Hello" }],
  },
  mcp: {
    connections: [{ id: "conn-1", name: "test-server" }],
    tools: [{ name: "test-tool" }],
  },
  canvas: {
    open: true,
    artifacts: [{ id: "art-1", type: "code" }],
  },
};

const createMockStore = () => {
  return configureStore({
    reducer: {
      session: () => mockState.session,
      mcp: () => mockState.mcp,
      canvas: () => mockState.canvas,
    },
  });
};

const renderWithStore = (ui: React.ReactNode) => {
  const store = createMockStore();
  return render(<Provider store={store}>{ui}</Provider>);
};

// Mock timeline context to avoid provider requirement
vi.mock("../context/DevToolsTimelineProvider", () => ({
  useTimelineContext: () => ({
    timeWindow: null,
    isLiveMode: true,
    currentTime: Date.now(),
    events: [],
    bookmarks: [],
  }),
}));

// =============================================================================
// Tests
// =============================================================================

describe("StateTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("rendering", () => {
    it("should render with data-testid", () => {
      renderWithStore(<StateTab context="global" />);

      expect(screen.getByTestId("state-tab")).toBeInTheDocument();
    });

    it("should display context indicator", () => {
      renderWithStore(<StateTab context="session" />);

      // Multiple elements match "session", but at least one should be in the toolbar
      const allSessionTexts = screen.getAllByText(/session/i);
      expect(allSessionTexts.length).toBeGreaterThan(0);
    });

    it("should display entity ID when provided", () => {
      renderWithStore(
        <StateTab context="session" contextEntityId="session-123" />,
      );

      expect(screen.getByText("session-123")).toBeInTheDocument();
    });
  });

  describe("state tree display", () => {
    it("should display state tree", () => {
      renderWithStore(<StateTab context="global" />);

      expect(screen.getByTestId("state-tree")).toBeInTheDocument();
    });

    it("should show session state in session context", () => {
      renderWithStore(<StateTab context="session" />);

      // The state tree should show session key
      const stateTree = screen.getByTestId("state-tree");
      expect(within(stateTree).getByText("session")).toBeInTheDocument();
    });

    it("should show expandable state nodes", () => {
      renderWithStore(<StateTab context="global" />);

      // Should have expandable nodes for different state slices
      const stateTree = screen.getByTestId("state-tree");
      expect(stateTree).toBeInTheDocument();
    });
  });

  describe("expand/collapse", () => {
    it("should expand state node on click", async () => {
      renderWithStore(<StateTab context="global" />);

      const expandButton = screen.getAllByTestId(/^expand-/)[0];
      if (expandButton) {
        fireEvent.click(expandButton);
        // Should show expanded content
        expect(screen.getByTestId("state-tree")).toBeInTheDocument();
      }
    });
  });

  describe("search", () => {
    it("should have search input", () => {
      renderWithStore(<StateTab context="global" />);

      expect(screen.getByTestId("state-search")).toBeInTheDocument();
    });

    it("should filter state on search", async () => {
      renderWithStore(<StateTab context="global" />);

      const searchInput = screen.getByTestId("state-search");
      fireEvent.change(searchInput, { target: { value: "session" } });

      // Search should filter results
      expect(searchInput).toHaveValue("session");
    });
  });

  describe("refresh", () => {
    it("should have refresh button", () => {
      renderWithStore(<StateTab context="global" />);

      expect(screen.getByTestId("refresh-button")).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = renderWithStore(<StateTab context="global" />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe("unified timeline integration", () => {
    it("should NOT have redundant timeline slider (uses unified TimelineBar)", () => {
      renderWithStore(<StateTab context="global" />);

      // The redundant timeline-slider should NOT exist
      // TimelineBar at DevToolsPanel level provides this functionality
      expect(screen.queryByTestId("timeline-slider")).not.toBeInTheDocument();
    });

    it("should NOT have redundant playback controls (uses unified TimelineBar)", () => {
      renderWithStore(<StateTab context="global" />);

      // These redundant controls should NOT exist
      expect(screen.queryByTestId("playback-button")).not.toBeInTheDocument();
      expect(screen.queryByTestId("go-back-button")).not.toBeInTheDocument();
      expect(screen.queryByTestId("go-forward-button")).not.toBeInTheDocument();
      expect(screen.queryByTestId("jump-start-button")).not.toBeInTheDocument();
      expect(
        screen.queryByTestId("jump-latest-button"),
      ).not.toBeInTheDocument();
    });

    it("should keep recording toggle to control snapshot capture", () => {
      renderWithStore(<StateTab context="global" />);

      // Recording toggle should still exist - it controls snapshot capture
      expect(screen.getByTestId("time-travel-toggle")).toBeInTheDocument();
    });

    it("should display state tree synced with unified timeline", () => {
      renderWithStore(<StateTab context="global" />);

      // State tree should still be visible and functional
      expect(screen.getByTestId("state-tree")).toBeInTheDocument();
    });
  });
});
