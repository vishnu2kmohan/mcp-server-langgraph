/**
 * ArtifactInteractionWrapper Tests
 *
 * Tests for the wrapper component that enables on-demand canvas launch
 * via popout icon or double-click on inline artifacts.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { MemoryRouter } from "react-router";
import canvasReducer from "../store/slices/canvasSlice";
import { ArtifactInteractionWrapper } from "./ArtifactInteractionWrapper";
import type { CanvasArtifact } from "../types/artifacts";

// =============================================================================
// Test Fixtures
// =============================================================================

const mockArtifact: CanvasArtifact = {
  id: "test-artifact-1",
  type: "code",
  sessionId: "session-1",
  version: 1,
  content: 'console.log("Hello");',
  contentType: "code",
  title: "Test Code",
  createdAt: "2024-01-01T00:00:00Z",
  updatedAt: "2024-01-01T00:00:00Z",
};

function createTestStore(preloadedState = {}) {
  return configureStore({
    reducer: {
      canvas: canvasReducer,
    },
    preloadedState,
  });
}

function renderWithProviders(
  ui: React.ReactElement,
  { store = createTestStore(), ...options } = {},
) {
  return render(
    <Provider store={store}>
      <MemoryRouter>{ui}</MemoryRouter>
    </Provider>,
    options,
  );
}

// =============================================================================
// Tests
// =============================================================================

describe("ArtifactInteractionWrapper", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe("Rendering", () => {
    it("should render children", () => {
      renderWithProviders(
        <ArtifactInteractionWrapper artifact={mockArtifact}>
          <div data-testid="child-content">Artifact Content</div>
        </ArtifactInteractionWrapper>,
      );

      expect(screen.getByTestId("child-content")).toBeInTheDocument();
    });

    it("should have data-testid", () => {
      renderWithProviders(
        <ArtifactInteractionWrapper artifact={mockArtifact}>
          <div>Content</div>
        </ArtifactInteractionWrapper>,
      );

      expect(
        screen.getByTestId("artifact-interaction-wrapper"),
      ).toBeInTheDocument();
    });

    it("should apply custom className", () => {
      renderWithProviders(
        <ArtifactInteractionWrapper
          artifact={mockArtifact}
          className="custom-class"
        >
          <div>Content</div>
        </ArtifactInteractionWrapper>,
      );

      expect(screen.getByTestId("artifact-interaction-wrapper")).toHaveClass(
        "custom-class",
      );
    });
  });

  describe("Popout Button", () => {
    it("should show popout button on hover", async () => {
      const user = userEvent.setup();

      renderWithProviders(
        <ArtifactInteractionWrapper artifact={mockArtifact}>
          <div>Content</div>
        </ArtifactInteractionWrapper>,
      );

      const wrapper = screen.getByTestId("artifact-interaction-wrapper");
      await user.hover(wrapper);

      expect(screen.getByTestId("popout-button")).toBeInTheDocument();
    });

    it("should hide popout button when not hovered", () => {
      renderWithProviders(
        <ArtifactInteractionWrapper artifact={mockArtifact}>
          <div>Content</div>
        </ArtifactInteractionWrapper>,
      );

      // Button should be present but visually hidden (opacity-0)
      const button = screen.getByTestId("popout-button");
      expect(button).toHaveClass("opacity-0");
    });

    it("should have accessible label", () => {
      renderWithProviders(
        <ArtifactInteractionWrapper artifact={mockArtifact}>
          <div>Content</div>
        </ArtifactInteractionWrapper>,
      );

      const button = screen.getByTestId("popout-button");
      expect(button).toHaveAttribute("aria-label", "Open in canvas");
    });
  });

  describe("Canvas Launch via Popout", () => {
    it("should expand canvas when popout button clicked", async () => {
      const user = userEvent.setup();
      const store = createTestStore({
        canvas: {
          canvasCollapsed: true,
          selectedArtifactId: null,
          tabOrder: [],
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          activeNavItem: "chat",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(
        <ArtifactInteractionWrapper artifact={mockArtifact}>
          <div>Content</div>
        </ArtifactInteractionWrapper>,
        { store },
      );

      const button = screen.getByTestId("popout-button");
      await user.click(button);

      expect(store.getState().canvas.canvasCollapsed).toBe(false);
    });

    it("should select artifact when popout button clicked", async () => {
      const user = userEvent.setup();
      const store = createTestStore({
        canvas: {
          canvasCollapsed: true,
          selectedArtifactId: null,
          tabOrder: [],
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          activeNavItem: "chat",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(
        <ArtifactInteractionWrapper artifact={mockArtifact}>
          <div>Content</div>
        </ArtifactInteractionWrapper>,
        { store },
      );

      const button = screen.getByTestId("popout-button");
      await user.click(button);

      expect(store.getState().canvas.selectedArtifactId).toBe(
        "test-artifact-1",
      );
    });

    it("should add artifact to tab order when popout clicked", async () => {
      const user = userEvent.setup();
      const store = createTestStore({
        canvas: {
          canvasCollapsed: true,
          selectedArtifactId: null,
          tabOrder: [],
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          activeNavItem: "chat",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(
        <ArtifactInteractionWrapper artifact={mockArtifact}>
          <div>Content</div>
        </ArtifactInteractionWrapper>,
        { store },
      );

      const button = screen.getByTestId("popout-button");
      await user.click(button);

      expect(store.getState().canvas.tabOrder).toContain("test-artifact-1");
    });
  });

  describe("Canvas Launch via Double-Click", () => {
    it("should expand canvas on double-click", async () => {
      const store = createTestStore({
        canvas: {
          canvasCollapsed: true,
          selectedArtifactId: null,
          tabOrder: [],
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          activeNavItem: "chat",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(
        <ArtifactInteractionWrapper artifact={mockArtifact}>
          <div>Content</div>
        </ArtifactInteractionWrapper>,
        { store },
      );

      const wrapper = screen.getByTestId("artifact-interaction-wrapper");
      fireEvent.dblClick(wrapper);

      expect(store.getState().canvas.canvasCollapsed).toBe(false);
    });

    it("should select artifact on double-click", async () => {
      const store = createTestStore({
        canvas: {
          canvasCollapsed: true,
          selectedArtifactId: null,
          tabOrder: [],
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          activeNavItem: "chat",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(
        <ArtifactInteractionWrapper artifact={mockArtifact}>
          <div>Content</div>
        </ArtifactInteractionWrapper>,
        { store },
      );

      const wrapper = screen.getByTestId("artifact-interaction-wrapper");
      fireEvent.dblClick(wrapper);

      expect(store.getState().canvas.selectedArtifactId).toBe(
        "test-artifact-1",
      );
    });
  });

  describe("Custom Callback", () => {
    it("should call onOpenInCanvas callback when provided", async () => {
      const user = userEvent.setup();
      const onOpenInCanvas = vi.fn();

      renderWithProviders(
        <ArtifactInteractionWrapper
          artifact={mockArtifact}
          onOpenInCanvas={onOpenInCanvas}
        >
          <div>Content</div>
        </ArtifactInteractionWrapper>,
      );

      const button = screen.getByTestId("popout-button");
      await user.click(button);

      expect(onOpenInCanvas).toHaveBeenCalledWith(mockArtifact);
    });
  });

  describe("Disabled State", () => {
    it("should not show popout button when disabled", () => {
      renderWithProviders(
        <ArtifactInteractionWrapper artifact={mockArtifact} disabled>
          <div>Content</div>
        </ArtifactInteractionWrapper>,
      );

      expect(screen.queryByTestId("popout-button")).not.toBeInTheDocument();
    });

    it("should not respond to double-click when disabled", async () => {
      const store = createTestStore({
        canvas: {
          canvasCollapsed: true,
          selectedArtifactId: null,
          tabOrder: [],
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          activeNavItem: "chat",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(
        <ArtifactInteractionWrapper artifact={mockArtifact} disabled>
          <div>Content</div>
        </ArtifactInteractionWrapper>,
        { store },
      );

      const wrapper = screen.getByTestId("artifact-interaction-wrapper");
      fireEvent.dblClick(wrapper);

      expect(store.getState().canvas.canvasCollapsed).toBe(true);
    });
  });
});
