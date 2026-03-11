/**
 * ShareWorkflowDialog Tests
 *
 * TDD tests for the workflow sharing dialog component.
 * Tests cover:
 * - Dialog visibility
 * - Adding shares with validation
 * - Removing shares
 * - Public/private toggle
 * - Copy link functionality
 * - Error handling
 *
 * Uses mocked RTK Query hooks for reliable testing.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
  cleanup,
} from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { ShareWorkflowDialog } from "./ShareWorkflowDialog";

// Mock navigator.clipboard
const mockClipboard = {
  writeText: vi.fn().mockResolvedValue(undefined),
};
Object.assign(navigator, { clipboard: mockClipboard });

// Mock RTK Query hooks
const mockAddShareUnwrap = vi.fn();
const mockRemoveShareUnwrap = vi.fn();
const mockUpdatePublicUnwrap = vi.fn();

const mockAddShare = vi.fn(() => ({ unwrap: mockAddShareUnwrap }));
const mockRemoveShare = vi.fn(() => ({ unwrap: mockRemoveShareUnwrap }));
const mockUpdatePublic = vi.fn(() => ({ unwrap: mockUpdatePublicUnwrap }));

import * as apiModule from "../../api";

// Mock RTK Query hooks - camelCase per ADR-0091 Phase 6
vi.mock("../../api", async () => {
  const actual = await vi.importActual("../../api");
  return {
    ...actual,
    useGetWorkflowSharesQuery: vi.fn(() => ({
      data: {
        shares: [
          { userId: "user-1", email: "alice@example.com", permission: "edit" },
          { userId: "user-2", email: "bob@example.com", permission: "view" },
        ],
        isPublic: false,
        shareLink: null,
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    })),
    useAddWorkflowShareMutation: vi.fn(() => [
      mockAddShare,
      { isLoading: false },
    ]),
    useRemoveWorkflowShareMutation: vi.fn(() => [
      mockRemoveShare,
      { isLoading: false },
    ]),
    useUpdateWorkflowPublicMutation: vi.fn(() => [
      mockUpdatePublic,
      { isLoading: false },
    ]),
  };
});
const mockedUseGetWorkflowSharesQuery = vi.mocked(
  apiModule.useGetWorkflowSharesQuery,
);
const mockedUseAddWorkflowShareMutation = vi.mocked(
  apiModule.useAddWorkflowShareMutation,
);
const mockedUseRemoveWorkflowShareMutation = vi.mocked(
  apiModule.useRemoveWorkflowShareMutation,
);
const mockedUseUpdateWorkflowPublicMutation = vi.mocked(
  apiModule.useUpdateWorkflowPublicMutation,
);

// Create a minimal store for testing
const createTestStore = () =>
  configureStore({
    reducer: {
      test: (state = {}) => state,
    },
  });

// Helper to render with Redux provider
const renderWithProvider = (component: React.ReactNode) => {
  const store = createTestStore();
  return render(<Provider store={store}>{component}</Provider>);
};

describe("ShareWorkflowDialog", () => {
  const mockWorkflow = {
    id: "wf-1",
    name: "Test Workflow",
  };

  const mockOnClose = vi.fn();

  // camelCase per ADR-0091 Phase 6
  const defaultSharesData = {
    shares: [
      {
        userId: "user-1",
        email: "alice@example.com",
        permission: "edit" as const,
      },
      {
        userId: "user-2",
        email: "bob@example.com",
        permission: "view" as const,
      },
    ],
    isPublic: false,
    shareLink: null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();

    // Reset to default successful mocks
    mockAddShareUnwrap.mockResolvedValue({ success: true });
    mockRemoveShareUnwrap.mockResolvedValue(undefined);
    mockUpdatePublicUnwrap.mockResolvedValue({
      isPublic: true,
      shareLink: "https://example.com/share/abc123",
    });

    mockedUseGetWorkflowSharesQuery.mockReturnValue({
      data: defaultSharesData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof apiModule.useGetWorkflowSharesQuery>);

    mockedUseAddWorkflowShareMutation.mockReturnValue([
      mockAddShare,
      { isLoading: false },
    ] as ReturnType<typeof apiModule.useAddWorkflowShareMutation>);
    mockedUseRemoveWorkflowShareMutation.mockReturnValue([
      mockRemoveShare,
      { isLoading: false },
    ] as ReturnType<typeof apiModule.useRemoveWorkflowShareMutation>);
    mockedUseUpdateWorkflowPublicMutation.mockReturnValue([
      mockUpdatePublic,
      { isLoading: false },
    ] as ReturnType<typeof apiModule.useUpdateWorkflowPublicMutation>);
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  describe("Dialog Visibility", () => {
    it("should not render when open is false", () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={false}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("should render when open is true", async () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });
    });

    it("should display workflow name in title", async () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText(/Share "Test Workflow"/)).toBeInTheDocument();
      });
    });

    it("should call onClose when close button is clicked", async () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByLabelText("Close"));

      expect(mockOnClose).toHaveBeenCalled();
    });

    it("should call onClose when backdrop is clicked", async () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });

      // Click on the backdrop (uses data-testid="dialog-backdrop")
      const backdrop = screen.getByTestId("dialog-backdrop");
      fireEvent.click(backdrop);

      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  describe("Fetching Shares", () => {
    it("should display existing shares", async () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("alice@example.com")).toBeInTheDocument();
        expect(screen.getByText("bob@example.com")).toBeInTheDocument();
      });
    });

    it("should display permission level for each share", async () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        // Permission levels are shown in the share list (not in the dropdown)
        // Use getAllByText since "edit" appears in both dropdown and share list
        const editTexts = screen.getAllByText("edit");
        const viewTexts = screen.getAllByText("view");
        // At least one of each should be in the share list (the other may be in dropdown)
        expect(editTexts.length).toBeGreaterThanOrEqual(1);
        expect(viewTexts.length).toBeGreaterThanOrEqual(1);
      });
    });

    it("should display first letter avatar for each user", async () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("A")).toBeInTheDocument();
        expect(screen.getByText("B")).toBeInTheDocument();
      });
    });

    it("should show loading state when fetching", async () => {
      mockedUseGetWorkflowSharesQuery.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      } as ReturnType<typeof apiModule.useGetWorkflowSharesQuery>);

      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      expect(document.querySelector(".animate-spin")).toBeInTheDocument();
    });

    it("should show error state when fetch fails", async () => {
      mockedUseGetWorkflowSharesQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: { status: 500, data: { detail: "Error" } },
        refetch: vi.fn(),
      } as ReturnType<typeof apiModule.useGetWorkflowSharesQuery>);

      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(
          screen.getByText(/Failed to load sharing settings/),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Adding Shares", () => {
    it("should have email input field", async () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText("Email address"),
        ).toBeInTheDocument();
      });
    });

    it("should have permission dropdown", async () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(screen.getByTestId("permission-select")).toBeInTheDocument();
      });
    });

    it("should have share button", async () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(screen.getByLabelText("Share")).toBeInTheDocument();
      });
    });

    it("should disable share button when email is empty", async () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(screen.getByLabelText("Share")).toBeDisabled();
      });
    });

    it("should enable share button when email is entered", async () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText("Email address"),
        ).toBeInTheDocument();
      });

      fireEvent.change(screen.getByPlaceholderText("Email address"), {
        target: { value: "test@example.com" },
      });

      expect(screen.getByLabelText("Share")).not.toBeDisabled();
    });

    it("should show error for invalid email", async () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText("Email address"),
        ).toBeInTheDocument();
      });

      fireEvent.change(screen.getByPlaceholderText("Email address"), {
        target: { value: "invalid-email" },
      });

      fireEvent.click(screen.getByLabelText("Share"));

      await waitFor(() => {
        expect(
          screen.getByText("Please enter a valid email address"),
        ).toBeInTheDocument();
      });
    });

    it("should clear email error when typing", async () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText("Email address"),
        ).toBeInTheDocument();
      });

      // Enter invalid email and submit
      fireEvent.change(screen.getByPlaceholderText("Email address"), {
        target: { value: "invalid" },
      });
      fireEvent.click(screen.getByLabelText("Share"));

      await waitFor(() => {
        expect(
          screen.getByText("Please enter a valid email address"),
        ).toBeInTheDocument();
      });

      // Type again to clear error
      fireEvent.change(screen.getByPlaceholderText("Email address"), {
        target: { value: "new@example.com" },
      });

      expect(
        screen.queryByText("Please enter a valid email address"),
      ).not.toBeInTheDocument();
    });

    it("should clear email input after successful share", async () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText("Email address"),
        ).toBeInTheDocument();
      });

      fireEvent.change(screen.getByPlaceholderText("Email address"), {
        target: { value: "newuser@example.com" },
      });

      await act(async () => {
        fireEvent.click(screen.getByLabelText("Share"));
      });

      await waitFor(() => {
        expect(screen.getByPlaceholderText("Email address")).toHaveValue("");
      });
    });

    it("should call addShare with correct parameters", async () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText("Email address"),
        ).toBeInTheDocument();
      });

      fireEvent.change(screen.getByPlaceholderText("Email address"), {
        target: { value: "newuser@example.com" },
      });

      fireEvent.change(screen.getByTestId("permission-select"), {
        target: { value: "edit" },
      });

      await act(async () => {
        fireEvent.click(screen.getByLabelText("Share"));
      });

      await waitFor(() => {
        expect(mockAddShare).toHaveBeenCalledWith({
          workflow_id: "wf-1",
          email: "newuser@example.com",
          permission: "edit",
        });
      });
    });

    it("should show error when share API fails", async () => {
      mockAddShareUnwrap.mockRejectedValue({
        data: { detail: "User not found" },
      });

      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText("Email address"),
        ).toBeInTheDocument();
      });

      fireEvent.change(screen.getByPlaceholderText("Email address"), {
        target: { value: "newuser@example.com" },
      });

      await act(async () => {
        fireEvent.click(screen.getByLabelText("Share"));
      });

      await waitFor(() => {
        expect(screen.getByText("User not found")).toBeInTheDocument();
      });
    });
  });

  describe("Removing Shares", () => {
    it("should have remove button for each share", async () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        const removeButtons = screen.getAllByLabelText("Remove");
        expect(removeButtons).toHaveLength(2);
      });
    });

    it("should call removeShare when remove button is clicked", async () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("alice@example.com")).toBeInTheDocument();
      });

      const removeButtons = screen.getAllByLabelText("Remove");

      await act(async () => {
        fireEvent.click(removeButtons[0]);
      });

      await waitFor(() => {
        expect(mockRemoveShare).toHaveBeenCalledWith({
          workflow_id: "wf-1",
          user_id: "user-1",
        });
      });
    });

    it("should show error when remove fails", async () => {
      mockRemoveShareUnwrap.mockRejectedValue({
        data: { detail: "Cannot remove owner" },
      });

      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("alice@example.com")).toBeInTheDocument();
      });

      const removeButtons = screen.getAllByLabelText("Remove");

      await act(async () => {
        fireEvent.click(removeButtons[0]);
      });

      await waitFor(() => {
        expect(screen.getByText("Cannot remove owner")).toBeInTheDocument();
      });
    });
  });

  describe("Public/Private Toggle", () => {
    it("should show private status when not public", async () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("Private")).toBeInTheDocument();
      });
    });

    it("should show public status when public", async () => {
      mockedUseGetWorkflowSharesQuery.mockReturnValue({
        data: {
          shares: [],
          isPublic: true,
          shareLink: "https://example.com/share/abc123",
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as ReturnType<typeof apiModule.useGetWorkflowSharesQuery>);

      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("Public access enabled")).toBeInTheDocument();
      });
    });

    it("should have toggle button for public access", async () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(screen.getByTestId("public-toggle")).toBeInTheDocument();
      });
    });

    it("should call updatePublic when toggle is clicked", async () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(screen.getByTestId("public-toggle")).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId("public-toggle"));
      });

      await waitFor(() => {
        expect(mockUpdatePublic).toHaveBeenCalledWith({
          workflow_id: "wf-1",
          is_public: true, // Toggling from false to true (snake_case for API request)
        });
      });
    });

    it("should show share link when public", async () => {
      mockedUseGetWorkflowSharesQuery.mockReturnValue({
        data: {
          shares: [],
          isPublic: true,
          shareLink: "https://example.com/share/abc123",
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as ReturnType<typeof apiModule.useGetWorkflowSharesQuery>);

      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(
          screen.getByDisplayValue("https://example.com/share/abc123"),
        ).toBeInTheDocument();
      });
    });

    it("should show appropriate description based on public state", async () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(
          screen.getByText(
            "Only people you share with can access this workflow",
          ),
        ).toBeInTheDocument();
      });
    });

    it("should show public description when public", async () => {
      mockedUseGetWorkflowSharesQuery.mockReturnValue({
        data: {
          shares: [],
          isPublic: true,
          shareLink: "https://example.com/share/abc123",
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as ReturnType<typeof apiModule.useGetWorkflowSharesQuery>);

      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(
          screen.getByText("Anyone with the link can view this workflow"),
        ).toBeInTheDocument();
      });
    });

    it("should show error when toggle fails", async () => {
      mockUpdatePublicUnwrap.mockRejectedValue({
        data: { detail: "Permission denied" },
      });

      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(screen.getByTestId("public-toggle")).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId("public-toggle"));
      });

      await waitFor(() => {
        expect(screen.getByText("Permission denied")).toBeInTheDocument();
      });
    });
  });

  describe("Copy Link", () => {
    it("should have copy button when public with link", async () => {
      mockedUseGetWorkflowSharesQuery.mockReturnValue({
        data: {
          shares: [],
          isPublic: true,
          shareLink: "https://example.com/share/abc123",
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as ReturnType<typeof apiModule.useGetWorkflowSharesQuery>);

      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(screen.getByLabelText("Copy link")).toBeInTheDocument();
      });
    });

    it("should copy link to clipboard when copy button is clicked", async () => {
      mockedUseGetWorkflowSharesQuery.mockReturnValue({
        data: {
          shares: [],
          isPublic: true,
          shareLink: "https://example.com/share/abc123",
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as ReturnType<typeof apiModule.useGetWorkflowSharesQuery>);

      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(screen.getByLabelText("Copy link")).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByLabelText("Copy link"));
      });

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        "https://example.com/share/abc123",
      );
    });

    it('should show "Copy" text on button', async () => {
      mockedUseGetWorkflowSharesQuery.mockReturnValue({
        data: {
          shares: [],
          isPublic: true,
          shareLink: "https://example.com/share/abc123",
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as ReturnType<typeof apiModule.useGetWorkflowSharesQuery>);

      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("Copy")).toBeInTheDocument();
      });
    });
  });

  describe("Empty States", () => {
    it("should not show shares section when no shares exist", async () => {
      mockedUseGetWorkflowSharesQuery.mockReturnValue({
        data: {
          shares: [],
          isPublic: false,
          shareLink: null,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as ReturnType<typeof apiModule.useGetWorkflowSharesQuery>);

      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(
          screen.queryByText("People with access"),
        ).not.toBeInTheDocument();
      });
    });

    it("should show shares section when shares exist", async () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("People with access")).toBeInTheDocument();
      });
    });
  });

  describe("Permission Options", () => {
    it("should have view, edit, and execute options", async () => {
      renderWithProvider(
        <ShareWorkflowDialog
          open={true}
          onClose={mockOnClose}
          workflow={mockWorkflow}
        />,
      );

      await waitFor(() => {
        const select = screen.getByTestId("permission-select");
        const options = select.querySelectorAll("option");
        const optionValues = Array.from(options).map((opt) =>
          opt.getAttribute("value"),
        );
        expect(optionValues).toContain("view");
        expect(optionValues).toContain("edit");
        expect(optionValues).toContain("execute");
      });
    });
  });
});
