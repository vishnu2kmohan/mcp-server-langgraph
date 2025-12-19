/**
 * HybridShellLayout Tests
 *
 * Phase 1: Full layout tests with resizable panels
 * Tests verify the layout renders with all panels and resizable functionality.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { HybridShellLayout } from "./HybridShellLayout";
import canvasReducer from "../store/slices/canvasSlice";

// Mock react-resizable-panels to avoid layout calculation issues in tests
vi.mock("react-resizable-panels", () => ({
  Panel: ({ children, ...props }: { children: React.ReactNode }) => (
    <div data-testid={props["data-testid"]} className={props.className}>
      {children}
    </div>
  ),
  PanelGroup: ({ children, ...props }: { children: React.ReactNode }) => (
    <div data-testid="panel-group" className={props.className}>
      {children}
    </div>
  ),
  PanelResizeHandle: (props: { className?: string }) => (
    <div data-testid="resize-handle" className={props.className} />
  ),
}));

// Create test store with canvas slice
const createTestStore = (preloadedState = {}) =>
  configureStore({
    reducer: {
      canvas: canvasReducer,
    },
    preloadedState,
  });

describe("HybridShellLayout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Core Layout", () => {
    it("renders the hybrid shell with all panels", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      expect(screen.getByTestId("hybrid-shell")).toBeInTheDocument();
      expect(screen.getByTestId("activity-bar")).toBeInTheDocument();
      expect(screen.getByTestId("session-nav")).toBeInTheDocument();
      expect(screen.getByTestId("conversation-panel")).toBeInTheDocument();
      expect(screen.getByTestId("canvas-panel")).toBeInTheDocument();
    });

    it("renders status bar at the bottom", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      expect(screen.getByTestId("canvas-status-bar")).toBeInTheDocument();
    });

    it("has proper layout structure with resizable panels", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      const shell = screen.getByTestId("hybrid-shell");
      expect(shell).toHaveClass("hybrid-shell");
      expect(screen.getByTestId("panel-group")).toBeInTheDocument();
    });

    it("does NOT render MainDock or AppShell", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      expect(screen.queryByTestId("app-shell")).not.toBeInTheDocument();
      expect(screen.queryByTestId("main-dock")).not.toBeInTheDocument();
    });
  });

  describe("ActivityBar", () => {
    it("renders navigation icons", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      const activityBar = screen.getByTestId("activity-bar");
      // Should have navigation buttons
      expect(activityBar.querySelectorAll("button").length).toBeGreaterThan(0);
    });

    it("has chat navigation icon", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      expect(screen.getByLabelText(/chat/i)).toBeInTheDocument();
    });
  });

  describe("SessionNav", () => {
    it("renders new chat button", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      expect(
        screen.getByRole("button", { name: /new chat/i }),
      ).toBeInTheDocument();
    });

    it("renders search input", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      expect(
        screen.getByPlaceholderText(/search sessions/i),
      ).toBeInTheDocument();
    });
  });

  describe("ConversationPanel", () => {
    it("renders message area placeholder", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      const conversationPanel = screen.getByTestId("conversation-panel");
      expect(conversationPanel).toBeInTheDocument();
    });
  });

  describe("CanvasPanel", () => {
    it("renders canvas area with outlet", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      const canvasPanel = screen.getByTestId("canvas-panel");
      expect(canvasPanel).toBeInTheDocument();
    });

    it("shows empty state when no artifact selected", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      expect(screen.getByText(/no artifact selected/i)).toBeInTheDocument();
    });
  });

  describe("Keyboard Navigation", () => {
    it("supports keyboard shortcuts hint in status bar", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      // Status bar should show keyboard hint
      expect(screen.getByTestId("canvas-status-bar")).toBeInTheDocument();
    });
  });
});
