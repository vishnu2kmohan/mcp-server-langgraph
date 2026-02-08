/**
 * AuditLogPage Tests
 *
 * TDD tests for the admin-only audit log page.
 * Tests cover:
 * - Header and title rendering
 * - Filter functionality
 * - Log listing and details expansion
 * - Export functionality
 * - Loading and error states
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { AuditLogPage } from "./AuditLogPage";
import { TestRouter } from "../test-utils";

// Mock the RTK Query hook
const mockRefetch = vi.fn();

vi.mock("../api", () => ({
  useListAuditLogsQuery: vi.fn(),
}));

import { useListAuditLogsQuery } from "../api";

import { TestProvider } from "@/test-utils";

// Cast to vi.Mock for type safety
const mockUseListAuditLogsQuery = useListAuditLogsQuery as ReturnType<
  typeof vi.fn
>;

// Mock audit log data
const mockLogs = [
  {
    id: "log-1",
    action: "user.login",
    user_id: "user-123",
    user_email: "alice@example.com",
    resource_type: "session",
    resource_id: "session-abc",
    timestamp: "2024-01-15T10:30:00Z",
    ip_address: "192.168.1.100",
    details: { browser: "Chrome", os: "Linux" },
  },
  {
    id: "log-2",
    action: "workflow.create",
    user_id: "user-456",
    user_email: "bob@example.com",
    resource_type: "workflow",
    resource_id: "workflow-xyz",
    timestamp: "2024-01-15T11:00:00Z",
    ip_address: "192.168.1.101",
    details: { workflow_name: "My Workflow" },
  },
  {
    id: "log-3",
    action: "api_key.delete",
    user_id: "user-789",
    user_email: "admin@example.com",
    resource_type: "api_key",
    resource_id: "key-123",
    timestamp: "2024-01-15T12:00:00Z",
    ip_address: "192.168.1.102",
    details: { key_name: "Production Key" },
  },
];

describe("AuditLogPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock: successful logs response
    mockUseListAuditLogsQuery.mockReturnValue({
      data: { items: mockLogs, total: mockLogs.length, limit: 50 },
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Header", () => {
    it("should render page title", () => {
      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      expect(screen.getByText("Audit Logs")).toBeInTheDocument();
    });

    it("should render page description", () => {
      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      expect(
        screen.getByText(/System activity and security events/i),
      ).toBeInTheDocument();
    });

    it("should render export button", () => {
      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /export/i }),
      ).toBeInTheDocument();
    });

    it("should render refresh button", () => {
      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /refresh/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Filters", () => {
    it("should render action filter input", () => {
      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      expect(
        screen.getByPlaceholderText(/filter by action/i),
      ).toBeInTheDocument();
    });

    it("should render user filter input", () => {
      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      expect(
        screen.getByPlaceholderText(/filter by user/i),
      ).toBeInTheDocument();
    });

    it("should filter logs by action", async () => {
      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      expect(screen.getByText("alice@example.com")).toBeInTheDocument();

      const actionFilter = screen.getByPlaceholderText(/filter by action/i);
      fireEvent.change(actionFilter, { target: { value: "login" } });

      await waitFor(() => {
        expect(screen.getByText("alice@example.com")).toBeInTheDocument();
        expect(screen.queryByText("bob@example.com")).not.toBeInTheDocument();
      });
    });

    it("should filter logs by user", async () => {
      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      expect(screen.getByText("alice@example.com")).toBeInTheDocument();

      const userFilter = screen.getByPlaceholderText(/filter by user/i);
      fireEvent.change(userFilter, { target: { value: "bob" } });

      await waitFor(() => {
        expect(screen.queryByText("alice@example.com")).not.toBeInTheDocument();
        expect(screen.getByText("bob@example.com")).toBeInTheDocument();
      });
    });

    it("should show count of filtered results", async () => {
      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      expect(screen.getByText(/3 of 3 entries/i)).toBeInTheDocument();

      const actionFilter = screen.getByPlaceholderText(/filter by action/i);
      fireEvent.change(actionFilter, { target: { value: "login" } });

      await waitFor(() => {
        expect(screen.getByText(/1 of 3 entries/i)).toBeInTheDocument();
      });
    });
  });

  describe("Log List", () => {
    it("should render log entries after loading", () => {
      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      expect(screen.getByText("alice@example.com")).toBeInTheDocument();
      expect(screen.getByText("bob@example.com")).toBeInTheDocument();
      expect(screen.getByText("admin@example.com")).toBeInTheDocument();
    });

    it("should display action badges", () => {
      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      expect(screen.getByText("user.login")).toBeInTheDocument();
      expect(screen.getByText("workflow.create")).toBeInTheDocument();
      expect(screen.getByText("api_key.delete")).toBeInTheDocument();
    });

    it("should display resource type and ID", () => {
      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      expect(screen.getByText("session/session-abc")).toBeInTheDocument();
      expect(screen.getByText("workflow/workflow-xyz")).toBeInTheDocument();
    });

    it("should display IP addresses", () => {
      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      expect(screen.getByText("192.168.1.100")).toBeInTheDocument();
      expect(screen.getByText("192.168.1.101")).toBeInTheDocument();
    });
  });

  describe("Log Details Expansion", () => {
    it("should expand log details on click", async () => {
      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      // Click on alice's log
      const aliceEmail = screen.getByText("alice@example.com");
      fireEvent.click(aliceEmail);

      await waitFor(() => {
        expect(screen.getByText(/Details/i)).toBeInTheDocument();
        expect(screen.getByText(/"browser"/)).toBeInTheDocument();
      });
    });

    it("should collapse log details on second click", async () => {
      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      const aliceEmail = screen.getByText("alice@example.com");

      // Expand
      fireEvent.click(aliceEmail);
      await waitFor(() => {
        expect(screen.getByText(/Details/i)).toBeInTheDocument();
      });

      // Collapse
      fireEvent.click(aliceEmail);
      await waitFor(() => {
        expect(screen.queryByText(/"browser"/)).not.toBeInTheDocument();
      });
    });
  });

  describe("API Integration", () => {
    it("should call refetch when refresh button is clicked", () => {
      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      const refreshButton = screen.getByRole("button", { name: /refresh/i });
      fireEvent.click(refreshButton);

      expect(mockRefetch).toHaveBeenCalledTimes(1);
    });
  });

  describe("Export", () => {
    it("should export logs as CSV", () => {
      // Mock URL.createObjectURL and revokeObjectURL
      const originalCreateObjectURL = global.URL.createObjectURL;
      const originalRevokeObjectURL = global.URL.revokeObjectURL;
      const mockCreateObjectURL = vi.fn().mockReturnValue("blob:test");
      const mockRevokeObjectURL = vi.fn();
      global.URL.createObjectURL = mockCreateObjectURL;
      global.URL.revokeObjectURL = mockRevokeObjectURL;

      // Track anchor clicks
      const mockClick = vi.fn();
      const originalCreateElement = document.createElement.bind(document);
      let capturedAnchor: HTMLAnchorElement | null = null;

      vi.spyOn(document, "createElement").mockImplementation(
        (tagName: string) => {
          const element = originalCreateElement(tagName);
          if (tagName === "a") {
            capturedAnchor = element as HTMLAnchorElement;
            capturedAnchor.click = mockClick;
          }
          return element;
        },
      );

      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      const exportButton = screen.getByRole("button", { name: /export/i });
      fireEvent.click(exportButton);

      expect(mockClick).toHaveBeenCalled();
      expect(capturedAnchor?.download).toMatch(/audit-logs-.*\.csv/);
      expect(mockRevokeObjectURL).toHaveBeenCalled();

      // Restore mocks
      global.URL.createObjectURL = originalCreateObjectURL;
      global.URL.revokeObjectURL = originalRevokeObjectURL;
      vi.restoreAllMocks();
    });
  });

  describe("Loading State", () => {
    it("should show loading spinner initially", () => {
      mockUseListAuditLogsQuery.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      expect(document.querySelector(".animate-spin")).toBeInTheDocument();
    });
  });

  describe("Error State", () => {
    it("should show error message on fetch failure", () => {
      mockUseListAuditLogsQuery.mockReturnValue({
        data: null,
        isLoading: false,
        error: { status: 500 },
        refetch: mockRefetch,
      });

      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      expect(screen.getByText(/Failed to load/i)).toBeInTheDocument();
    });

    it("should show retry button on error", () => {
      mockUseListAuditLogsQuery.mockReturnValue({
        data: null,
        isLoading: false,
        error: { status: 500 },
        refetch: mockRefetch,
      });

      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /retry/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("should show empty state when no logs", () => {
      mockUseListAuditLogsQuery.mockReturnValue({
        data: { items: [], total: 0, limit: 50 },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      expect(screen.getByText(/no audit logs found/i)).toBeInTheDocument();
    });
  });

  describe("Action Color Coding", () => {
    it("should color delete actions red", () => {
      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      const deleteAction = screen.getByText("api_key.delete");
      expect(deleteAction.className).toMatch(/red/i);
    });

    it("should color create actions green", () => {
      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      const createAction = screen.getByText("workflow.create");
      expect(createAction.className).toMatch(/green/i);
    });

    it("should color login actions blue", () => {
      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      const loginAction = screen.getByText("user.login");
      expect(loginAction.className).toMatch(/blue/i);
    });
  });

  describe("Pagination", () => {
    it("should render pagination component when data is loaded", () => {
      mockUseListAuditLogsQuery.mockReturnValue({
        data: {
          items: mockLogs,
          total: 100,
          limit: 50,
          next_cursor: "cursor-abc",
        },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      expect(screen.getByTestId("cursor-pagination")).toBeInTheDocument();
    });

    it("should enable Next button when next_cursor exists", () => {
      mockUseListAuditLogsQuery.mockReturnValue({
        data: {
          items: mockLogs,
          total: 100,
          limit: 50,
          next_cursor: "cursor-abc",
        },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      const nextButton = screen.getByRole("button", { name: /next page/i });
      expect(nextButton).not.toBeDisabled();
    });

    it("should disable Previous button on first page", () => {
      mockUseListAuditLogsQuery.mockReturnValue({
        data: {
          items: mockLogs,
          total: 100,
          limit: 50,
          next_cursor: "cursor-abc",
        },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      const prevButton = screen.getByRole("button", { name: /previous page/i });
      expect(prevButton).toBeDisabled();
    });

    it("should disable Next button when no next_cursor", () => {
      mockUseListAuditLogsQuery.mockReturnValue({
        data: { items: mockLogs, total: 3, limit: 50, next_cursor: null },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      const nextButton = screen.getByRole("button", { name: /next page/i });
      expect(nextButton).toBeDisabled();
    });

    it("should fetch next page when Next is clicked", async () => {
      mockUseListAuditLogsQuery.mockReturnValue({
        data: {
          items: mockLogs,
          total: 100,
          limit: 50,
          next_cursor: "cursor-abc",
        },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      const nextButton = screen.getByRole("button", { name: /next page/i });
      fireEvent.click(nextButton);

      // After clicking Next, the query should have been called with the cursor
      await waitFor(() => {
        // Check that RTK Query was called with cursor parameter
        expect(mockUseListAuditLogsQuery).toHaveBeenCalledWith(
          expect.objectContaining({ cursor: "cursor-abc" }),
        );
      });
    });

    it("should show item count in pagination", () => {
      mockUseListAuditLogsQuery.mockReturnValue({
        data: {
          items: mockLogs,
          total: 100,
          limit: 50,
          next_cursor: "cursor-abc",
        },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <TestProvider>
          <TestRouter>
            <AuditLogPage />
          </TestRouter>
        </TestProvider>,
      );

      // Pagination component should show item count
      const pagination = screen.getByTestId("cursor-pagination");
      expect(pagination).toHaveTextContent(/3 of 100/i);
    });
  });
});
