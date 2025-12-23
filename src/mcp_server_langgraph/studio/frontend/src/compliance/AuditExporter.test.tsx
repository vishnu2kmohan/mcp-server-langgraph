/**
 * AuditExporter Tests - Phase 5
 *
 * Tests for compliance audit export functionality.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { AuditExporter, type AuditFilter } from "./AuditExporter";

// =============================================================================
// Test Data
// =============================================================================

const mockAuditLogs = [
  {
    id: "log-1",
    timestamp: "2024-01-15T10:30:00Z",
    userId: "user-123",
    action: "artifact.created",
    resourceType: "artifact",
    resourceId: "artifact-456",
    metadata: { title: "New Artifact" },
    ipAddress: "192.168.1.1",
    userAgent: "Mozilla/5.0",
  },
  {
    id: "log-2",
    timestamp: "2024-01-15T11:00:00Z",
    userId: "user-456",
    action: "session.deleted",
    resourceType: "session",
    resourceId: "session-789",
    metadata: { reason: "user_request" },
    ipAddress: "192.168.1.2",
    userAgent: "Chrome/120.0",
  },
];

const mockFilters: AuditFilter = {
  startDate: "2024-01-01",
  endDate: "2024-01-31",
  userId: undefined,
  action: undefined,
  resourceType: undefined,
};

// =============================================================================
// Tests
// =============================================================================

describe("AuditExporter", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render exporter container", () => {
      render(
        <AuditExporter
          auditLogs={mockAuditLogs}
          filters={mockFilters}
          onExport={() => Promise.resolve()}
        />,
      );
      expect(screen.getByTestId("audit-exporter")).toBeInTheDocument();
    });

    it("should display export format options", () => {
      render(
        <AuditExporter
          auditLogs={mockAuditLogs}
          filters={mockFilters}
          onExport={() => Promise.resolve()}
        />,
      );
      expect(screen.getByText("CSV")).toBeInTheDocument();
      expect(screen.getByText("JSON")).toBeInTheDocument();
      expect(screen.getByText("PDF")).toBeInTheDocument();
    });

    it("should show record count", () => {
      render(
        <AuditExporter
          auditLogs={mockAuditLogs}
          filters={mockFilters}
          onExport={() => Promise.resolve()}
        />,
      );
      expect(screen.getByText(/2 records/i)).toBeInTheDocument();
    });

    it("should display date range", () => {
      render(
        <AuditExporter
          auditLogs={mockAuditLogs}
          filters={mockFilters}
          onExport={() => Promise.resolve()}
        />,
      );
      // Date format depends on locale, just verify the range is shown
      expect(screen.getByText(/from .+ to .+/)).toBeInTheDocument();
    });
  });

  describe("Format Selection", () => {
    it("should have CSV selected by default", () => {
      render(
        <AuditExporter
          auditLogs={mockAuditLogs}
          filters={mockFilters}
          onExport={() => Promise.resolve()}
        />,
      );
      const csvOption = screen.getByTestId("format-csv");
      expect(csvOption).toHaveClass("selected");
    });

    it("should allow selecting JSON format", async () => {
      render(
        <AuditExporter
          auditLogs={mockAuditLogs}
          filters={mockFilters}
          onExport={() => Promise.resolve()}
        />,
      );
      const jsonOption = screen.getByTestId("format-json");
      fireEvent.click(jsonOption);
      expect(jsonOption).toHaveClass("selected");
    });

    it("should allow selecting PDF format", async () => {
      render(
        <AuditExporter
          auditLogs={mockAuditLogs}
          filters={mockFilters}
          onExport={() => Promise.resolve()}
        />,
      );
      const pdfOption = screen.getByTestId("format-pdf");
      fireEvent.click(pdfOption);
      expect(pdfOption).toHaveClass("selected");
    });
  });

  describe("Export Actions", () => {
    it("should call onExport with selected format", async () => {
      const onExport = vi
        .fn()
        .mockResolvedValue({ url: "/download/export.csv" });
      render(
        <AuditExporter
          auditLogs={mockAuditLogs}
          filters={mockFilters}
          onExport={onExport}
        />,
      );

      fireEvent.click(screen.getByTestId("export-button"));

      await waitFor(() => {
        expect(onExport).toHaveBeenCalledWith(
          expect.objectContaining({
            format: "csv",
            filters: mockFilters,
          }),
        );
      });
    });

    it("should show loading state during export", async () => {
      const onExport = vi
        .fn()
        .mockImplementation(
          () =>
            new Promise((resolve) =>
              setTimeout(() => resolve({ url: "/download/export.csv" }), 1000),
            ),
        );

      render(
        <AuditExporter
          auditLogs={mockAuditLogs}
          filters={mockFilters}
          onExport={onExport}
        />,
      );

      fireEvent.click(screen.getByTestId("export-button"));

      await waitFor(() => {
        expect(screen.getByTestId("export-loading")).toBeInTheDocument();
      });
    });

    it("should show success message after export", async () => {
      const onExport = vi
        .fn()
        .mockResolvedValue({ url: "/download/export.csv" });
      render(
        <AuditExporter
          auditLogs={mockAuditLogs}
          filters={mockFilters}
          onExport={onExport}
        />,
      );

      fireEvent.click(screen.getByTestId("export-button"));

      await waitFor(() => {
        expect(screen.getByTestId("export-success")).toBeInTheDocument();
      });
    });

    it("should show error on export failure", async () => {
      const onExport = vi.fn().mockRejectedValue(new Error("Export failed"));
      render(
        <AuditExporter
          auditLogs={mockAuditLogs}
          filters={mockFilters}
          onExport={onExport}
        />,
      );

      fireEvent.click(screen.getByTestId("export-button"));

      await waitFor(() => {
        expect(screen.getByText(/export failed/i)).toBeInTheDocument();
      });
    });
  });

  describe("Rate Limiting", () => {
    it("should show rate limit warning", () => {
      render(
        <AuditExporter
          auditLogs={mockAuditLogs}
          filters={mockFilters}
          onExport={() => Promise.resolve()}
          remainingExports={3}
          maxExports={10}
        />,
      );
      expect(
        screen.getByText(/3 of 10 exports remaining/i),
      ).toBeInTheDocument();
    });

    it("should disable export when rate limited", () => {
      render(
        <AuditExporter
          auditLogs={mockAuditLogs}
          filters={mockFilters}
          onExport={() => Promise.resolve()}
          remainingExports={0}
          maxExports={10}
        />,
      );
      const exportButton = screen.getByTestId("export-button");
      expect(exportButton).toBeDisabled();
    });

    it("should show rate limit exhausted message", () => {
      render(
        <AuditExporter
          auditLogs={mockAuditLogs}
          filters={mockFilters}
          onExport={() => Promise.resolve()}
          remainingExports={0}
          maxExports={10}
        />,
      );
      expect(screen.getByText(/rate limit reached/i)).toBeInTheDocument();
    });
  });

  describe("Field Selection", () => {
    it("should show field selection dropdown", () => {
      render(
        <AuditExporter
          auditLogs={mockAuditLogs}
          filters={mockFilters}
          onExport={() => Promise.resolve()}
          showFieldSelection
        />,
      );
      expect(screen.getByTestId("field-selection")).toBeInTheDocument();
    });

    it("should allow toggling fields", async () => {
      const onExport = vi
        .fn()
        .mockResolvedValue({ url: "/download/export.csv" });
      render(
        <AuditExporter
          auditLogs={mockAuditLogs}
          filters={mockFilters}
          onExport={onExport}
          showFieldSelection
        />,
      );

      // Toggle off userAgent field
      const userAgentCheckbox = screen.getByLabelText(/user agent/i);
      fireEvent.click(userAgentCheckbox);

      fireEvent.click(screen.getByTestId("export-button"));

      await waitFor(() => {
        expect(onExport).toHaveBeenCalledWith(
          expect.objectContaining({
            excludeFields: expect.arrayContaining(["userAgent"]),
          }),
        );
      });
    });
  });

  describe("Watermarking", () => {
    it("should show watermark option for PDF", async () => {
      render(
        <AuditExporter
          auditLogs={mockAuditLogs}
          filters={mockFilters}
          onExport={() => Promise.resolve()}
        />,
      );

      // Select PDF format
      fireEvent.click(screen.getByTestId("format-pdf"));

      expect(screen.getByLabelText(/include watermark/i)).toBeInTheDocument();
    });

    it("should include watermark option in export request", async () => {
      const onExport = vi
        .fn()
        .mockResolvedValue({ url: "/download/export.pdf" });
      render(
        <AuditExporter
          auditLogs={mockAuditLogs}
          filters={mockFilters}
          onExport={onExport}
        />,
      );

      // Select PDF format
      fireEvent.click(screen.getByTestId("format-pdf"));

      // Watermark is on by default
      fireEvent.click(screen.getByTestId("export-button"));

      await waitFor(() => {
        expect(onExport).toHaveBeenCalledWith(
          expect.objectContaining({
            format: "pdf",
            includeWatermark: true,
          }),
        );
      });
    });
  });

  describe("Accessibility", () => {
    it("should have accessible export button", () => {
      render(
        <AuditExporter
          auditLogs={mockAuditLogs}
          filters={mockFilters}
          onExport={() => Promise.resolve()}
        />,
      );
      const exportButton = screen.getByRole("button", { name: /export/i });
      expect(exportButton).toBeInTheDocument();
    });

    it("should have radio buttons for format selection", () => {
      render(
        <AuditExporter
          auditLogs={mockAuditLogs}
          filters={mockFilters}
          onExport={() => Promise.resolve()}
        />,
      );
      expect(screen.getByRole("radiogroup")).toBeInTheDocument();
    });

    it("should announce export status", async () => {
      const onExport = vi
        .fn()
        .mockResolvedValue({ url: "/download/export.csv" });
      render(
        <AuditExporter
          auditLogs={mockAuditLogs}
          filters={mockFilters}
          onExport={onExport}
        />,
      );

      fireEvent.click(screen.getByTestId("export-button"));

      await waitFor(() => {
        const status = screen.getByRole("status");
        expect(status).toHaveTextContent(/export complete/i);
      });
    });
  });

  describe("Empty State", () => {
    it("should show empty state when no logs", () => {
      render(
        <AuditExporter
          auditLogs={[]}
          filters={mockFilters}
          onExport={() => Promise.resolve()}
        />,
      );
      expect(screen.getByText(/no audit logs/i)).toBeInTheDocument();
    });

    it("should disable export when no logs", () => {
      render(
        <AuditExporter
          auditLogs={[]}
          filters={mockFilters}
          onExport={() => Promise.resolve()}
        />,
      );
      const exportButton = screen.getByTestId("export-button");
      expect(exportButton).toBeDisabled();
    });
  });
});
