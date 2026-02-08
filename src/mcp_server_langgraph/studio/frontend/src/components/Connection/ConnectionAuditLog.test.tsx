/**
 * ConnectionAuditLog Tests
 *
 * TDD tests for the connection audit log viewer component.
 * Displays audit trail for connection operations.
 *
 * Uses MSW for realistic API mocking at the network level.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
  act,
} from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "../../mocks/server";
import { ConnectionAuditLog } from "./ConnectionAuditLog";

import { TestProvider } from "@/test-utils";

const mockLogs = [
  {
    id: "1",
    event_type: "connection.created",
    resource_type: "connection",
    resource_id: "conn-123",
    actor_id: "user-456",
    action: "create",
    details: { name: "GitHub MCP", auth_type: "oauth2" },
    ip_address: "192.168.1.100",
    user_agent: "Mozilla/5.0",
    timestamp: "2024-01-15T10:30:00Z",
  },
  {
    id: "2",
    event_type: "connection.tested",
    resource_type: "connection",
    resource_id: "conn-123",
    actor_id: "user-456",
    action: "test",
    details: { success: true, latency_ms: 150 },
    ip_address: "192.168.1.100",
    user_agent: "Mozilla/5.0",
    timestamp: "2024-01-15T11:00:00Z",
  },
  {
    id: "3",
    event_type: "connection.oauth2_authorized",
    resource_type: "connection",
    resource_id: "conn-123",
    actor_id: "user-456",
    action: "authorize",
    details: { provider: "github" },
    ip_address: "192.168.1.100",
    user_agent: "Mozilla/5.0",
    timestamp: "2024-01-15T10:45:00Z",
  },
];

describe("ConnectionAuditLog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Set up default handler for audit logs
    server.use(
      http.get("/api/v1/connections/:id/audit", () => {
        return HttpResponse.json({
          logs: mockLogs,
          total: 3,
          limit: 20,
          offset: 0,
        });
      }),
    );
  });

  afterEach(async () => {
    // Wait for any pending state updates to complete
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    cleanup();
  });

  describe("Component Structure", () => {
    it("should render title", async () => {
      render(
        <TestProvider>
          <ConnectionAuditLog connectionId="conn-123" />
        </TestProvider>,
      );
      await waitFor(() => {
        expect(screen.getByText(/audit log/i)).toBeInTheDocument();
      });
    });

    it("should show loading state initially", () => {
      render(
        <TestProvider>
          <ConnectionAuditLog connectionId="conn-123" />
        </TestProvider>,
      );
      expect(screen.getByTestId("loading-audit-logs")).toBeInTheDocument();
    });

    it("should display audit logs after loading", async () => {
      render(
        <TestProvider>
          <ConnectionAuditLog connectionId="conn-123" />
        </TestProvider>,
      );
      await waitFor(() => {
        expect(screen.getByText("connection.created")).toBeInTheDocument();
        expect(screen.getByText("connection.tested")).toBeInTheDocument();
      });
    });
  });

  describe("Log Entry Display", () => {
    it("should display event type", async () => {
      render(
        <TestProvider>
          <ConnectionAuditLog connectionId="conn-123" />
        </TestProvider>,
      );
      await waitFor(() => {
        expect(screen.getByText("connection.created")).toBeInTheDocument();
      });
    });

    it("should display actor ID", async () => {
      render(
        <TestProvider>
          <ConnectionAuditLog connectionId="conn-123" />
        </TestProvider>,
      );
      await waitFor(() => {
        expect(screen.getAllByText("user-456").length).toBeGreaterThan(0);
      });
    });

    it("should display timestamp", async () => {
      render(
        <TestProvider>
          <ConnectionAuditLog connectionId="conn-123" />
        </TestProvider>,
      );
      await waitFor(() => {
        // Should show formatted date (multiple logs have dates)
        const timestamps = screen.getAllByText(/Jan 15, 2024/);
        expect(timestamps.length).toBeGreaterThan(0);
      });
    });

    it("should show action badge", async () => {
      render(
        <TestProvider>
          <ConnectionAuditLog connectionId="conn-123" />
        </TestProvider>,
      );
      await waitFor(() => {
        expect(screen.getByText("create")).toBeInTheDocument();
        expect(screen.getByText("test")).toBeInTheDocument();
      });
    });
  });

  describe("Log Details", () => {
    it("should expand to show details on click", async () => {
      render(
        <TestProvider>
          <ConnectionAuditLog connectionId="conn-123" />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText("connection.created")).toBeInTheDocument();
      });

      // Click to expand
      const expandButton = screen.getAllByTestId("expand-log")[0];
      fireEvent.click(expandButton);

      await waitFor(() => {
        // Should show details JSON
        expect(screen.getByText(/github mcp/i)).toBeInTheDocument();
      });
    });

    it("should show IP address in details", async () => {
      render(
        <TestProvider>
          <ConnectionAuditLog connectionId="conn-123" />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText("connection.created")).toBeInTheDocument();
      });

      const expandButton = screen.getAllByTestId("expand-log")[0];
      fireEvent.click(expandButton);

      await waitFor(() => {
        expect(screen.getByText("192.168.1.100")).toBeInTheDocument();
      });
    });
  });

  describe("API Calls", () => {
    it("should fetch and display logs for specific connection", async () => {
      render(
        <TestProvider>
          <ConnectionAuditLog connectionId="conn-123" />
        </TestProvider>,
      );

      // Verify logs are displayed (proves fetch happened)
      await waitFor(() => {
        expect(screen.getByText("connection.created")).toBeInTheDocument();
      });
    });

    it("should refresh logs on refresh button click", async () => {
      let fetchCount = 0;
      server.use(
        http.get("/api/v1/connections/:id/audit", () => {
          fetchCount++;
          return HttpResponse.json({
            logs: mockLogs,
            total: 3,
            limit: 20,
            offset: 0,
          });
        }),
      );

      render(
        <TestProvider>
          <ConnectionAuditLog connectionId="conn-123" />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText("connection.created")).toBeInTheDocument();
      });

      const initialFetchCount = fetchCount;
      const refreshButton = screen.getByRole("button", { name: /refresh/i });
      fireEvent.click(refreshButton);

      await waitFor(() => {
        expect(fetchCount).toBeGreaterThan(initialFetchCount);
      });
    });
  });

  describe("Empty State", () => {
    it("should show message when no logs exist", async () => {
      server.use(
        http.get("/api/v1/connections/:id/audit", () => {
          return HttpResponse.json({
            logs: [],
            total: 0,
            limit: 20,
            offset: 0,
          });
        }),
      );

      render(
        <TestProvider>
          <ConnectionAuditLog connectionId="conn-123" />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText(/no audit logs/i)).toBeInTheDocument();
      });
    });
  });

  describe("Error State", () => {
    it("should show error message on fetch failure", async () => {
      server.use(
        http.get("/api/v1/connections/:id/audit", () => {
          return HttpResponse.error();
        }),
      );

      render(
        <TestProvider>
          <ConnectionAuditLog connectionId="conn-123" />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
      });
    });

    it("should show retry button on error", async () => {
      server.use(
        http.get("/api/v1/connections/:id/audit", () => {
          return HttpResponse.error();
        }),
      );

      render(
        <TestProvider>
          <ConnectionAuditLog connectionId="conn-123" />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /retry/i }),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Filtering", () => {
    it("should filter by event type", async () => {
      let lastRequestUrl = "";
      server.use(
        // Handler for initial load (without filter)
        http.get("/api/v1/connections/:id/audit", ({ request }) => {
          lastRequestUrl = request.url;
          return HttpResponse.json({
            logs: mockLogs,
            total: 3,
            limit: 20,
            offset: 0,
          });
        }),
        // Handler for filtered requests (component uses different endpoint when filtering)
        http.get("/api/v1/connections/audit/logs", ({ request }) => {
          lastRequestUrl = request.url;
          return HttpResponse.json({
            logs: mockLogs,
            total: 3,
            limit: 20,
            offset: 0,
          });
        }),
      );

      render(
        <TestProvider>
          <ConnectionAuditLog connectionId="conn-123" />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText("connection.created")).toBeInTheDocument();
      });

      const filterSelect = screen.getByTestId("event-type-filter");
      fireEvent.change(filterSelect, {
        target: { value: "connection.tested" },
      });

      await waitFor(() => {
        expect(lastRequestUrl).toContain("event_type=connection.tested");
      });
    });
  });
});
