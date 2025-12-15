/**
 * ConnectionBulkActions Tests
 *
 * TDD tests for bulk action controls for connections.
 * Supports multi-select delete and test operations.
 *
 * Uses MSW for realistic API mocking at the network level.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { http, HttpResponse, delay } from "msw";
import { server } from "../../mocks/server";
import { ConnectionBulkActions } from "./ConnectionBulkActions";

const mockConnections = [
  { id: "1", name: "Server 1", status: "connected" },
  { id: "2", name: "Server 2", status: "disconnected" },
  { id: "3", name: "Server 3", status: "error" },
];

describe("ConnectionBulkActions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Set up default handlers for bulk operations
    server.use(
      http.post("/api/v1/connections/bulk/delete", () => {
        return HttpResponse.json({ deleted_count: 2, failed_ids: [] });
      }),
      http.post("/api/v1/connections/bulk/test", () => {
        return HttpResponse.json({ results: [], not_found: [] });
      }),
    );
  });

  describe("Component Visibility", () => {
    it("should not render when no items selected", () => {
      const { container } = render(
        <ConnectionBulkActions
          selectedIds={[]}
          connections={mockConnections}
          onActionComplete={vi.fn()}
        />,
      );
      expect(container.firstChild).toBeNull();
    });

    it("should render when items are selected", () => {
      render(
        <ConnectionBulkActions
          selectedIds={["1", "2"]}
          connections={mockConnections}
          onActionComplete={vi.fn()}
        />,
      );
      expect(screen.getByTestId("bulk-actions")).toBeInTheDocument();
    });
  });

  describe("Selection Count", () => {
    it("should display number of selected items", () => {
      render(
        <ConnectionBulkActions
          selectedIds={["1", "2"]}
          connections={mockConnections}
          onActionComplete={vi.fn()}
        />,
      );
      expect(screen.getByText(/2 selected/i)).toBeInTheDocument();
    });

    it("should update count when selection changes", () => {
      const { rerender } = render(
        <ConnectionBulkActions
          selectedIds={["1"]}
          connections={mockConnections}
          onActionComplete={vi.fn()}
        />,
      );
      expect(screen.getByText(/1 selected/i)).toBeInTheDocument();

      rerender(
        <ConnectionBulkActions
          selectedIds={["1", "2", "3"]}
          connections={mockConnections}
          onActionComplete={vi.fn()}
        />,
      );
      expect(screen.getByText(/3 selected/i)).toBeInTheDocument();
    });
  });

  describe("Action Buttons", () => {
    it("should show delete button", () => {
      render(
        <ConnectionBulkActions
          selectedIds={["1"]}
          connections={mockConnections}
          onActionComplete={vi.fn()}
        />,
      );
      expect(
        screen.getByRole("button", { name: /delete/i }),
      ).toBeInTheDocument();
    });

    it("should show test button", () => {
      render(
        <ConnectionBulkActions
          selectedIds={["1"]}
          connections={mockConnections}
          onActionComplete={vi.fn()}
        />,
      );
      expect(screen.getByRole("button", { name: /test/i })).toBeInTheDocument();
    });

    it("should show clear selection button", () => {
      render(
        <ConnectionBulkActions
          selectedIds={["1"]}
          connections={mockConnections}
          onActionComplete={vi.fn()}
        />,
      );
      expect(
        screen.getByRole("button", { name: /clear/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Bulk Delete", () => {
    it("should show confirmation dialog on delete click", () => {
      render(
        <ConnectionBulkActions
          selectedIds={["1", "2"]}
          connections={mockConnections}
          onActionComplete={vi.fn()}
        />,
      );

      fireEvent.click(screen.getByRole("button", { name: /delete/i }));

      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(screen.getByText(/2 connections/i)).toBeInTheDocument();
    });

    it("should call API on confirm delete", async () => {
      const onActionComplete = vi.fn();

      render(
        <ConnectionBulkActions
          selectedIds={["1", "2"]}
          connections={mockConnections}
          onActionComplete={onActionComplete}
        />,
      );

      fireEvent.click(screen.getByRole("button", { name: /delete/i }));
      fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

      await waitFor(() => {
        expect(onActionComplete).toHaveBeenCalled();
      });
    });

    it("should close dialog on cancel", () => {
      render(
        <ConnectionBulkActions
          selectedIds={["1"]}
          connections={mockConnections}
          onActionComplete={vi.fn()}
        />,
      );

      fireEvent.click(screen.getByRole("button", { name: /delete/i }));
      expect(screen.getByRole("dialog")).toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });

  describe("Bulk Test", () => {
    it("should call test API on test button click", async () => {
      const onActionComplete = vi.fn();

      render(
        <ConnectionBulkActions
          selectedIds={["1", "2"]}
          connections={mockConnections}
          onActionComplete={onActionComplete}
        />,
      );

      fireEvent.click(screen.getByRole("button", { name: /test/i }));

      // Wait for loading state to appear and then complete
      await waitFor(() => {
        // After the API call completes, the loading state should end
        expect(screen.queryByText(/testing/i)).not.toBeInTheDocument();
      });
    });

    it("should show loading state during test", async () => {
      server.use(
        http.post("/api/v1/connections/bulk/test", async () => {
          await delay(100);
          return HttpResponse.json({ results: [], not_found: [] });
        }),
      );

      render(
        <ConnectionBulkActions
          selectedIds={["1"]}
          connections={mockConnections}
          onActionComplete={vi.fn()}
        />,
      );

      fireEvent.click(screen.getByRole("button", { name: /test/i }));

      expect(screen.getByText(/testing/i)).toBeInTheDocument();

      // Wait for the loading state to complete
      await waitFor(() => {
        expect(screen.queryByText(/testing/i)).not.toBeInTheDocument();
      });
    });
  });

  describe("Clear Selection", () => {
    it("should call onClearSelection when clear clicked", () => {
      const onClearSelection = vi.fn();
      render(
        <ConnectionBulkActions
          selectedIds={["1", "2"]}
          connections={mockConnections}
          onActionComplete={vi.fn()}
          onClearSelection={onClearSelection}
        />,
      );

      fireEvent.click(screen.getByRole("button", { name: /clear/i }));

      expect(onClearSelection).toHaveBeenCalled();
    });
  });

  describe("Error Handling", () => {
    it("should show error message on delete failure", async () => {
      server.use(
        http.post("/api/v1/connections/bulk/delete", () => {
          return HttpResponse.error();
        }),
      );

      render(
        <ConnectionBulkActions
          selectedIds={["1"]}
          connections={mockConnections}
          onActionComplete={vi.fn()}
        />,
      );

      fireEvent.click(screen.getByRole("button", { name: /delete/i }));
      fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

      await waitFor(() => {
        expect(screen.getByText(/error/i)).toBeInTheDocument();
      });
    });

    it("should show partial failure message", async () => {
      server.use(
        http.post("/api/v1/connections/bulk/delete", () => {
          return HttpResponse.json({ deleted_count: 1, failed_ids: ["2"] });
        }),
      );

      render(
        <ConnectionBulkActions
          selectedIds={["1", "2"]}
          connections={mockConnections}
          onActionComplete={vi.fn()}
        />,
      );

      fireEvent.click(screen.getByRole("button", { name: /delete/i }));
      fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

      await waitFor(() => {
        expect(screen.getByText(/1.*deleted/i)).toBeInTheDocument();
        expect(screen.getByText(/1.*failed/i)).toBeInTheDocument();
      });
    });
  });
});
