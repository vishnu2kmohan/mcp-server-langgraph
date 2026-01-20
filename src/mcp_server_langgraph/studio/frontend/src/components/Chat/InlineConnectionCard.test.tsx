/**
 * InlineConnectionCard Tests
 *
 * Tests for the in-chat connection setup card component.
 * This component appears when auth_required events are received from the SSE stream.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { InlineConnectionCard } from "./InlineConnectionCard";
import chatConnectionReducer from "../../store/slices/chatConnectionSlice";

// Mock RTK Query hooks - return objects with unwrap() method
const createUnwrappable = <T,>(value: T) => ({
  unwrap: () => Promise.resolve(value),
});

const createPendingUnwrappable = () => ({
  unwrap: () => new Promise(() => { /* never resolves */ }),
});

const mockCreateConnection = vi.fn(() =>
  createUnwrappable({ id: "new-conn-123", name: "GitHub Connection" }),
);
const mockTestConnection = vi.fn(() => createUnwrappable({ success: true }));
const mockStartOAuth = vi.fn(() =>
  createUnwrappable({ authorization_url: "https://github.com/oauth" }),
);

vi.mock("../../api", () => ({
  useCreateConnectionMutation: () => [
    mockCreateConnection,
    { isLoading: false },
  ],
  useTestConnectionMutation: () => [mockTestConnection, { isLoading: false }],
  useStartOAuth2FlowMutation: () => [mockStartOAuth, { isLoading: false }],
  useListConnectionTemplatesQuery: () => ({
    data: {
      templates: [
        {
          id: "github",
          name: "GitHub",
          description: "Access GitHub repositories",
          icon: "github",
          auth_type: "oauth2",
          default_url: "https://api.github.com",
          category: "development",
          oauth2_scopes: ["repo", "user"],
          config_fields: [],
          keywords: ["github", "pr"],
          popularity: 95,
          documentation_url: "https://docs.github.com/",
        },
        {
          id: "slack",
          name: "Slack",
          description: "Access Slack channels",
          icon: "slack",
          auth_type: "oauth2",
          default_url: "https://slack.com/api",
          category: "communication",
          oauth2_scopes: ["chat:write"],
          config_fields: [],
          keywords: ["slack", "message"],
          popularity: 90,
          documentation_url: "https://api.slack.com/",
        },
      ],
    },
    isLoading: false,
  }),
}));

// Mock useMotionSafeVariants hook
vi.mock("../../hooks/useMotionSafe", () => ({
  useMotionSafeVariants: (variants: Record<string, unknown>) => variants,
}));

// Note: motion/react is globally mocked in src/test/setup.ts with proper prop filtering

const createTestStore = () =>
  configureStore({
    reducer: {
      chatConnection: chatConnectionReducer,
    },
  });

const defaultProps = {
  templateId: "github",
  toolName: "github:list_prs",
  message: "Authentication required to access GitHub",
  connectionId: null,
  retryMessageId: null,
  onDismiss: vi.fn(),
  onRetry: vi.fn(),
};

const renderWithProviders = (
  component: React.ReactElement,
  store = createTestStore(),
) => {
  return render(<Provider store={store}>{component}</Provider>);
};

describe("InlineConnectionCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render with template name and message", () => {
      renderWithProviders(<InlineConnectionCard {...defaultProps} />);

      // Check for template name in the header - use getAllByText since there may be multiple
      const githubElements = screen.getAllByText(/github/i);
      expect(githubElements.length).toBeGreaterThan(0);
      expect(
        screen.getByText(/authentication required to access github/i),
      ).toBeInTheDocument();
    });

    it("should render expand/collapse button", () => {
      renderWithProviders(<InlineConnectionCard {...defaultProps} />);

      expect(
        screen.getByRole("button", { name: /configure|connect/i }),
      ).toBeInTheDocument();
    });

    it("should render dismiss button", () => {
      renderWithProviders(<InlineConnectionCard {...defaultProps} />);

      expect(
        screen.getByRole("button", { name: /dismiss|close|skip/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Expansion", () => {
    it("should expand when configure button is clicked", async () => {
      renderWithProviders(<InlineConnectionCard {...defaultProps} />);

      const configureButton = screen.getByRole("button", {
        name: /configure|connect/i,
      });
      fireEvent.click(configureButton);

      await waitFor(() => {
        // Should show auth method options after expansion - use getAllByText for multiple matches
        const authElements = screen.getAllByText(/oauth|sign in|api key/i);
        expect(authElements.length).toBeGreaterThan(0);
      });
    });

    it("should collapse when collapse button is clicked", async () => {
      renderWithProviders(<InlineConnectionCard {...defaultProps} />);

      // Expand first
      const configureButton = screen.getByRole("button", {
        name: /configure|connect/i,
      });
      fireEvent.click(configureButton);

      await waitFor(() => {
        expect(screen.getByText(/oauth|sign in/i)).toBeInTheDocument();
      });

      // Find and click collapse button
      const collapseButton = screen.getByRole("button", {
        name: /collapse|cancel|back/i,
      });
      fireEvent.click(collapseButton);

      // Form should be hidden
      await waitFor(() => {
        expect(screen.queryByLabelText(/api key/i)).not.toBeInTheDocument();
      });
    });
  });

  describe("OAuth2 Flow", () => {
    it("should show OAuth2 option for oauth2 templates", async () => {
      renderWithProviders(<InlineConnectionCard {...defaultProps} />);

      const configureButton = screen.getByRole("button", {
        name: /configure|connect/i,
      });
      fireEvent.click(configureButton);

      await waitFor(() => {
        expect(screen.getByText(/sign in with github/i)).toBeInTheDocument();
      });
    });
  });

  describe("Dismiss", () => {
    it("should call onDismiss when dismiss button is clicked", () => {
      const onDismiss = vi.fn();
      renderWithProviders(
        <InlineConnectionCard {...defaultProps} onDismiss={onDismiss} />,
      );

      const dismissButton = screen.getByRole("button", {
        name: /dismiss|close|skip/i,
      });
      fireEvent.click(dismissButton);

      expect(onDismiss).toHaveBeenCalled();
    });
  });

  describe("Re-authentication", () => {
    it("should show re-auth message when connectionId is provided", () => {
      renderWithProviders(
        <InlineConnectionCard
          {...defaultProps}
          connectionId="conn-123"
          message="Your GitHub connection requires re-authentication"
        />,
      );

      // Use getAllByText since there may be multiple elements matching
      const reconnectElements = screen.getAllByText(/re-authentication|reconnect/i);
      expect(reconnectElements.length).toBeGreaterThan(0);
    });
  });

  describe("States", () => {
    it("should show loading state during authentication", async () => {
      // Mock window.open to return a fake popup
      const mockPopup = { closed: false, close: vi.fn() };
      vi.spyOn(window, "open").mockReturnValue(mockPopup as unknown as Window);

      // Setup mock to return pending promise so component stays in loading state
      mockStartOAuth.mockImplementation(() => createPendingUnwrappable());

      renderWithProviders(<InlineConnectionCard {...defaultProps} />);

      const configureButton = screen.getByRole("button", {
        name: /configure|connect/i,
      });
      fireEvent.click(configureButton);

      await waitFor(() => {
        expect(screen.getByText(/sign in with github/i)).toBeInTheDocument();
      });

      // Click OAuth button
      const oauthButton = screen.getByRole("button", {
        name: /sign in with github/i,
      });
      fireEvent.click(oauthButton);

      // Should show loading state - "Connecting..." is displayed when status === "authenticating"
      await waitFor(() => {
        expect(screen.getByText(/connecting\.\.\./i)).toBeInTheDocument();
      });
    });
  });
});
