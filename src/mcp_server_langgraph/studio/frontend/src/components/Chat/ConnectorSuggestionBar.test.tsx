/**
 * ConnectorSuggestionBar Tests
 *
 * Tests for the proactive connector suggestion bar that appears
 * when user input matches connector template keywords.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import chatConnectionReducer from "../../store/slices/chatConnectionSlice";
import { ConnectorSuggestionBar } from "./ConnectorSuggestionBar";
import type { ConnectionTemplate } from "../../types/connectionTemplate";

// Note: motion/react is globally mocked in src/test/setup.ts with proper prop filtering

// Create test store
function createTestStore() {
  return configureStore({
    reducer: {
      chatConnection: chatConnectionReducer,
    },
  });
}

// Helper to render with Redux
function renderWithStore(
  ui: React.ReactElement,
  { store = createTestStore() } = {},
) {
  return {
    store,
    ...render(<Provider store={store}>{ui}</Provider>),
  };
}

// Sample templates for testing
const mockTemplates: ConnectionTemplate[] = [
  {
    id: "github",
    name: "GitHub",
    description: "Access GitHub repositories and pull requests",
    icon: "github",
    authType: "oauth2",
    defaultUrl: "https://api.github.com",
    category: "development",
    oauth2Scopes: ["repo", "user"],
    configFields: [],
    keywords: ["github", "pr", "pull request", "repository", "commit"],
    popularity: 95,
    documentationUrl: "https://docs.github.com/",
  },
  {
    id: "slack",
    name: "Slack",
    description: "Send messages and interact with Slack channels",
    icon: "slack",
    authType: "oauth2",
    defaultUrl: "https://slack.com/api",
    category: "communication",
    oauth2Scopes: ["chat:write"],
    configFields: [],
    keywords: ["slack", "message", "channel"],
    popularity: 90,
    documentationUrl: "https://api.slack.com/",
  },
];

describe("ConnectorSuggestionBar", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should not render when suggestions array is empty", () => {
      renderWithStore(
        <ConnectorSuggestionBar
          suggestions={[]}
          onConnect={vi.fn()}
          onDismiss={vi.fn()}
        />,
      );

      expect(
        screen.queryByTestId("connector-suggestion-bar"),
      ).not.toBeInTheDocument();
    });

    it("should render suggestion bar when suggestions are provided", () => {
      renderWithStore(
        <ConnectorSuggestionBar
          suggestions={[mockTemplates[0]]}
          onConnect={vi.fn()}
          onDismiss={vi.fn()}
        />,
      );

      expect(
        screen.getByTestId("connector-suggestion-bar"),
      ).toBeInTheDocument();
    });

    it("should display the template name in the suggestion message", () => {
      renderWithStore(
        <ConnectorSuggestionBar
          suggestions={[mockTemplates[0]]}
          onConnect={vi.fn()}
          onDismiss={vi.fn()}
        />,
      );

      // Template name appears in multiple places - check at least one exists
      expect(screen.getAllByText(/GitHub/).length).toBeGreaterThan(0);
    });

    it("should show Connect button with template name", () => {
      renderWithStore(
        <ConnectorSuggestionBar
          suggestions={[mockTemplates[0]]}
          onConnect={vi.fn()}
          onDismiss={vi.fn()}
        />,
      );

      expect(
        screen.getByRole("button", { name: /connect github/i }),
      ).toBeInTheDocument();
    });

    it("should show Dismiss button", () => {
      renderWithStore(
        <ConnectorSuggestionBar
          suggestions={[mockTemplates[0]]}
          onConnect={vi.fn()}
          onDismiss={vi.fn()}
        />,
      );

      expect(
        screen.getByRole("button", { name: /dismiss/i }),
      ).toBeInTheDocument();
    });

    it("should display first template when multiple suggestions exist", () => {
      renderWithStore(
        <ConnectorSuggestionBar
          suggestions={mockTemplates}
          onConnect={vi.fn()}
          onDismiss={vi.fn()}
        />,
      );

      // Should show the first template (GitHub)
      expect(
        screen.getByRole("button", { name: /connect github/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Interactions", () => {
    it("should call onConnect with template when Connect button is clicked", () => {
      const onConnect = vi.fn();
      renderWithStore(
        <ConnectorSuggestionBar
          suggestions={[mockTemplates[0]]}
          onConnect={onConnect}
          onDismiss={vi.fn()}
        />,
      );

      fireEvent.click(screen.getByRole("button", { name: /connect github/i }));

      expect(onConnect).toHaveBeenCalledWith(mockTemplates[0]);
    });

    it("should call onDismiss when Dismiss button is clicked", () => {
      const onDismiss = vi.fn();
      renderWithStore(
        <ConnectorSuggestionBar
          suggestions={[mockTemplates[0]]}
          onConnect={vi.fn()}
          onDismiss={onDismiss}
        />,
      );

      fireEvent.click(screen.getByRole("button", { name: /dismiss/i }));

      expect(onDismiss).toHaveBeenCalled();
    });
  });

  describe("Loading State", () => {
    it("should show loading state when isLoading is true", () => {
      renderWithStore(
        <ConnectorSuggestionBar
          suggestions={[]}
          onConnect={vi.fn()}
          onDismiss={vi.fn()}
          isLoading={true}
        />,
      );

      // Should show loading indicator
      expect(screen.getByTestId("suggestion-loading")).toBeInTheDocument();
    });

    it("should not show loading indicator when isLoading is false", () => {
      renderWithStore(
        <ConnectorSuggestionBar
          suggestions={[mockTemplates[0]]}
          onConnect={vi.fn()}
          onDismiss={vi.fn()}
          isLoading={false}
        />,
      );

      expect(
        screen.queryByTestId("suggestion-loading"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible message describing the suggestion", () => {
      renderWithStore(
        <ConnectorSuggestionBar
          suggestions={[mockTemplates[0]]}
          onConnect={vi.fn()}
          onDismiss={vi.fn()}
        />,
      );

      // The suggestion message should be readable
      const suggestionText = screen.getByText(/might need.*access/i);
      expect(suggestionText).toBeInTheDocument();
    });

    it("should have accessible button labels", () => {
      renderWithStore(
        <ConnectorSuggestionBar
          suggestions={[mockTemplates[0]]}
          onConnect={vi.fn()}
          onDismiss={vi.fn()}
        />,
      );

      const connectButton = screen.getByRole("button", {
        name: /connect github/i,
      });
      const dismissButton = screen.getByRole("button", { name: /dismiss/i });

      expect(connectButton).toBeVisible();
      expect(dismissButton).toBeVisible();
    });
  });
});
