/**
 * AuditLogFilters Component Tests
 *
 * TDD tests for audit log filtering component.
 * Tests cover:
 * - Date range picker
 * - Action type filter
 * - User search
 * - Export functionality
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuditLogFilters } from "./AuditLogFilters";

import { TestProvider } from "@/test-utils";

describe("AuditLogFilters", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  const defaultProps = {
    onDateRangeChange: vi.fn(),
    onActionTypeChange: vi.fn(),
    onUserSearch: vi.fn(),
    onExport: vi.fn(),
  };

  describe("Rendering", () => {
    it("should render date range picker", () => {
      render(
        <TestProvider>
          <AuditLogFilters {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByLabelText(/start date/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/end date/i)).toBeInTheDocument();
    });

    it("should render action type filter", () => {
      render(
        <TestProvider>
          <AuditLogFilters {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByLabelText(/action type/i)).toBeInTheDocument();
    });

    it("should render user search input", () => {
      render(
        <TestProvider>
          <AuditLogFilters {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByPlaceholderText(/search user/i)).toBeInTheDocument();
    });

    it("should render export button", () => {
      render(
        <TestProvider>
          <AuditLogFilters {...defaultProps} />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /export/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Date Range", () => {
    it("should call onDateRangeChange when start date changes", async () => {
      const onDateRangeChange = vi.fn();
      render(
        <TestProvider>
          <AuditLogFilters
            {...defaultProps}
            onDateRangeChange={onDateRangeChange}
          />
        </TestProvider>,
      );

      const startDateInput = screen.getByLabelText(/start date/i);
      await userEvent.type(startDateInput, "2025-01-01");

      expect(onDateRangeChange).toHaveBeenCalled();
    });

    it("should call onDateRangeChange when end date changes", async () => {
      const onDateRangeChange = vi.fn();
      render(
        <TestProvider>
          <AuditLogFilters
            {...defaultProps}
            onDateRangeChange={onDateRangeChange}
          />
        </TestProvider>,
      );

      const endDateInput = screen.getByLabelText(/end date/i);
      await userEvent.type(endDateInput, "2025-01-31");

      expect(onDateRangeChange).toHaveBeenCalled();
    });
  });

  describe("Action Type Filter", () => {
    it("should show action type options", async () => {
      render(
        <TestProvider>
          <AuditLogFilters {...defaultProps} />
        </TestProvider>,
      );

      const select = screen.getByLabelText(/action type/i);
      fireEvent.click(select);

      expect(screen.getByText("All Actions")).toBeInTheDocument();
      expect(screen.getByText("User Created")).toBeInTheDocument();
      expect(screen.getByText("User Updated")).toBeInTheDocument();
      expect(screen.getByText("User Deleted")).toBeInTheDocument();
      expect(screen.getByText("Role Changed")).toBeInTheDocument();
      expect(screen.getByText("Login")).toBeInTheDocument();
      expect(screen.getByText("Logout")).toBeInTheDocument();
    });

    it("should call onActionTypeChange when action type is selected", async () => {
      const onActionTypeChange = vi.fn();
      render(
        <TestProvider>
          <AuditLogFilters
            {...defaultProps}
            onActionTypeChange={onActionTypeChange}
          />
        </TestProvider>,
      );

      const select = screen.getByLabelText(/action type/i);
      await userEvent.selectOptions(select, "user_created");

      expect(onActionTypeChange).toHaveBeenCalledWith("user_created");
    });
  });

  describe("User Search", () => {
    it("should call onUserSearch when typing in search", async () => {
      const onUserSearch = vi.fn();
      render(
        <TestProvider>
          <AuditLogFilters {...defaultProps} onUserSearch={onUserSearch} />
        </TestProvider>,
      );

      const searchInput = screen.getByPlaceholderText(/search user/i);
      await userEvent.type(searchInput, "alice");

      expect(onUserSearch).toHaveBeenCalledWith("alice");
    });

    it("should call onUserSearch for each character typed", async () => {
      const onUserSearch = vi.fn();
      render(
        <TestProvider>
          <AuditLogFilters {...defaultProps} onUserSearch={onUserSearch} />
        </TestProvider>,
      );

      const searchInput = screen.getByPlaceholderText(/search user/i);
      fireEvent.change(searchInput, { target: { value: "alice" } });

      expect(onUserSearch).toHaveBeenCalledWith("alice");
    });
  });

  describe("Export", () => {
    it("should call onExport when export button is clicked", () => {
      const onExport = vi.fn();
      render(
        <TestProvider>
          <AuditLogFilters {...defaultProps} onExport={onExport} />
        </TestProvider>,
      );

      const exportButton = screen.getByRole("button", { name: /export csv/i });
      fireEvent.click(exportButton);

      expect(onExport).toHaveBeenCalled();
    });

    it("should show export format options", () => {
      render(
        <TestProvider>
          <AuditLogFilters {...defaultProps} />
        </TestProvider>,
      );

      // Export button should indicate CSV format
      expect(
        screen.getByRole("button", { name: /export csv/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Reset Filters", () => {
    it("should show reset button", () => {
      render(
        <TestProvider>
          <AuditLogFilters {...defaultProps} />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /reset/i }),
      ).toBeInTheDocument();
    });

    it("should call onReset when reset button is clicked", () => {
      const onReset = vi.fn();
      render(
        <TestProvider>
          <AuditLogFilters {...defaultProps} onReset={onReset} />
        </TestProvider>,
      );

      const resetButton = screen.getByRole("button", {
        name: /reset filters/i,
      });
      fireEvent.click(resetButton);

      expect(onReset).toHaveBeenCalled();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible labels for all inputs", () => {
      render(
        <TestProvider>
          <AuditLogFilters {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByLabelText(/start date/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/end date/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/action type/i)).toBeInTheDocument();
    });
  });
});
