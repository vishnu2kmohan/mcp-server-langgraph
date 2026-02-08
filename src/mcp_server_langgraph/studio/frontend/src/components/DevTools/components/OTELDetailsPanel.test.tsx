/**
 * OTELDetailsPanel Component Tests
 *
 * TDD: Tests written FIRST, then implementation.
 * Tests expandable panel for JSON attributes, headers, and payloads.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { OTELDetailsPanel } from "./OTELDetailsPanel";

import { TestProvider } from "@/test-utils";

// =============================================================================
// Basic Rendering Tests
// =============================================================================

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("OTELDetailsPanel", () => {
  describe("basic rendering", () => {
    it("should render with data", () => {
      const data = { key: "value", count: 42 };
      render(
        <TestProvider>
          <OTELDetailsPanel data={data} />
        </TestProvider>,
      );
      expect(screen.getByRole("region")).toBeInTheDocument();
    });

    it("should render title when provided", () => {
      render(
        <TestProvider>
          <OTELDetailsPanel data={{ test: true }} title="Attributes" />
        </TestProvider>,
      );
      expect(screen.getByText("Attributes")).toBeInTheDocument();
    });

    it("should render in summary view by default", () => {
      render(
        <TestProvider>
          <OTELDetailsPanel data={{ name: "test" }} />
        </TestProvider>,
      );
      // Summary view shows formatted key-value pairs
      expect(screen.getByText("name")).toBeInTheDocument();
      expect(screen.getByText("test")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Summary View Tests
  // ===========================================================================

  describe("summary view", () => {
    it("should display key-value pairs in human-readable format", () => {
      const data = {
        "service.name": "api-gateway",
        "http.method": "GET",
        "http.status_code": 200,
      };
      render(
        <TestProvider>
          <OTELDetailsPanel data={data} defaultView="summary" />
        </TestProvider>,
      );

      expect(screen.getByText("service.name")).toBeInTheDocument();
      expect(screen.getByText("api-gateway")).toBeInTheDocument();
      expect(screen.getByText("http.method")).toBeInTheDocument();
      expect(screen.getByText("GET")).toBeInTheDocument();
    });

    it("should format timestamps in summary view", () => {
      const data = {
        timestamp: "2026-01-15T14:30:00Z",
      };
      render(
        <TestProvider>
          <OTELDetailsPanel
            data={data}
            defaultView="summary"
            formatHints={{ timestamp: "timestamp" }}
          />
        </TestProvider>,
      );

      // Should show relative time for timestamp
      expect(screen.getByText("timestamp")).toBeInTheDocument();
    });

    it("should format durations in summary view", () => {
      const data = {
        duration_ms: 1234,
      };
      render(
        <TestProvider>
          <OTELDetailsPanel
            data={data}
            defaultView="summary"
            formatHints={{ duration_ms: "duration" }}
          />
        </TestProvider>,
      );

      expect(screen.getByText("duration_ms")).toBeInTheDocument();
      // Duration should be formatted (1.2s)
      expect(screen.getByText("1.2s")).toBeInTheDocument();
    });

    it("should format byte sizes in summary view", () => {
      const data = {
        response_size: 1536,
      };
      render(
        <TestProvider>
          <OTELDetailsPanel
            data={data}
            defaultView="summary"
            formatHints={{ response_size: "bytes" }}
          />
        </TestProvider>,
      );

      expect(screen.getByText("response_size")).toBeInTheDocument();
      expect(screen.getByText("1.5 KB")).toBeInTheDocument();
    });

    it("should handle nested objects in summary view", () => {
      const data = {
        user: {
          id: "123",
          email: "user@example.com",
        },
      };
      render(
        <TestProvider>
          <OTELDetailsPanel data={data} defaultView="summary" />
        </TestProvider>,
      );

      expect(screen.getByText("user")).toBeInTheDocument();
      // Nested object should show summary or be expandable
      expect(screen.getByText(/2 keys/)).toBeInTheDocument();
    });

    it("should handle arrays in summary view", () => {
      const data = {
        tags: ["production", "critical", "monitored"],
      };
      render(
        <TestProvider>
          <OTELDetailsPanel data={data} defaultView="summary" />
        </TestProvider>,
      );

      expect(screen.getByText("tags")).toBeInTheDocument();
      expect(screen.getByText(/3 items/)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Raw View Tests
  // ===========================================================================

  describe("raw view", () => {
    it("should display full JSON with syntax highlighting", () => {
      const data = { key: "value", nested: { inner: true } };
      render(
        <TestProvider>
          <OTELDetailsPanel data={data} defaultView="raw" />
        </TestProvider>,
      );

      // Should contain JSON structure
      const preElement = screen.getByRole("region").querySelector("pre");
      expect(preElement).toBeInTheDocument();
      expect(preElement?.textContent).toContain("key");
      expect(preElement?.textContent).toContain("value");
    });

    it("should format JSON with proper indentation", () => {
      const data = { key: "value" };
      render(
        <TestProvider>
          <OTELDetailsPanel data={data} defaultView="raw" />
        </TestProvider>,
      );

      const preElement = screen.getByRole("region").querySelector("pre");
      // Check for newlines indicating pretty-printed JSON
      expect(preElement?.textContent).toContain("\n");
    });
  });

  // ===========================================================================
  // View Toggle Tests
  // ===========================================================================

  describe("view toggle", () => {
    it("should show toggle button when showViewToggle is true", () => {
      render(
        <TestProvider>
          <OTELDetailsPanel data={{ test: true }} showViewToggle />
        </TestProvider>,
      );
      expect(screen.getByRole("button", { name: /raw/i })).toBeInTheDocument();
    });

    it("should hide toggle button when showViewToggle is false", () => {
      render(
        <TestProvider>
          <OTELDetailsPanel data={{ test: true }} showViewToggle={false} />
        </TestProvider>,
      );
      expect(
        screen.queryByRole("button", { name: /raw/i }),
      ).not.toBeInTheDocument();
    });

    it("should toggle between summary and raw views", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <OTELDetailsPanel data={{ key: "value" }} showViewToggle />
        </TestProvider>,
      );

      // Initially in summary view
      expect(screen.getByText("key")).toBeInTheDocument();

      // Click toggle to switch to raw
      const toggleButton = screen.getByRole("button", { name: /raw/i });
      await user.click(toggleButton);

      // Should now be in raw view with JSON
      const preElement = screen.getByRole("region").querySelector("pre");
      expect(preElement).toBeInTheDocument();
    });

    it("should toggle back to summary from raw", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <OTELDetailsPanel
            data={{ key: "value" }}
            defaultView="raw"
            showViewToggle
          />
        </TestProvider>,
      );

      // Click toggle to switch to summary
      const toggleButton = screen.getByRole("button", { name: /summary/i });
      await user.click(toggleButton);

      // Should show summary view
      expect(screen.getByText("key")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Tabbed Variant Tests
  // ===========================================================================

  describe("tabbed variant", () => {
    it("should render tabs when variant is tabbed", () => {
      const tabs = [
        {
          key: "headers",
          label: "Headers",
          data: { "Content-Type": "application/json" },
        },
        { key: "body", label: "Body", data: { message: "Hello" } },
      ];
      render(
        <TestProvider>
          <OTELDetailsPanel data={{}} variant="tabbed" tabs={tabs} />
        </TestProvider>,
      );

      expect(screen.getByRole("tablist")).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: "Headers" })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: "Body" })).toBeInTheDocument();
    });

    it("should show first tab content by default", () => {
      const tabs = [
        {
          key: "headers",
          label: "Headers",
          data: { "Content-Type": "application/json" },
        },
        { key: "body", label: "Body", data: { message: "Hello" } },
      ];
      render(
        <TestProvider>
          <OTELDetailsPanel data={{}} variant="tabbed" tabs={tabs} />
        </TestProvider>,
      );

      expect(screen.getByText("Content-Type")).toBeInTheDocument();
      expect(screen.getByText("application/json")).toBeInTheDocument();
    });

    it("should switch tab content when clicking tabs", async () => {
      const user = userEvent.setup();
      const tabs = [
        {
          key: "headers",
          label: "Headers",
          data: { "Content-Type": "application/json" },
        },
        { key: "body", label: "Body", data: { message: "Hello" } },
      ];
      render(
        <TestProvider>
          <OTELDetailsPanel data={{}} variant="tabbed" tabs={tabs} />
        </TestProvider>,
      );

      // Click Body tab
      await user.click(screen.getByRole("tab", { name: "Body" }));

      expect(screen.getByText("message")).toBeInTheDocument();
      expect(screen.getByText("Hello")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Copy Functionality Tests
  // ===========================================================================

  describe("copy functionality", () => {
    it("should show copy button", () => {
      render(
        <TestProvider>
          <OTELDetailsPanel data={{ test: true }} />
        </TestProvider>,
      );
      expect(screen.getByRole("button", { name: /copy/i })).toBeInTheDocument();
    });

    it("should call onCopy callback when copy button clicked", async () => {
      const onCopy = vi.fn();
      const user = userEvent.setup();

      // Mock clipboard API
      Object.defineProperty(navigator, "clipboard", {
        value: { writeText: vi.fn().mockResolvedValue(undefined) },
        writable: true,
        configurable: true,
      });

      render(
        <TestProvider>
          <OTELDetailsPanel data={{ test: true }} onCopy={onCopy} />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /copy/i }));

      expect(onCopy).toHaveBeenCalled();
    });

    it("should copy JSON to clipboard", async () => {
      const mockWriteText = vi.fn().mockResolvedValue(undefined);
      Object.defineProperty(navigator, "clipboard", {
        value: { writeText: mockWriteText },
        writable: true,
        configurable: true,
      });

      const data = { key: "value" };
      render(
        <TestProvider>
          <OTELDetailsPanel data={data} />
        </TestProvider>,
      );

      // Use fireEvent for direct event triggering
      fireEvent.click(screen.getByRole("button", { name: /copy/i }));

      // Wait for the async clipboard operation
      await vi.waitFor(() => {
        expect(mockWriteText).toHaveBeenCalledWith(
          JSON.stringify(data, null, 2),
        );
      });
    });
  });

  // ===========================================================================
  // Close Functionality Tests
  // ===========================================================================

  describe("close functionality", () => {
    it("should show close button when onClose is provided", () => {
      const onClose = vi.fn();
      render(
        <TestProvider>
          <OTELDetailsPanel data={{ test: true }} onClose={onClose} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /close/i }),
      ).toBeInTheDocument();
    });

    it("should not show close button when onClose is not provided", () => {
      render(
        <TestProvider>
          <OTELDetailsPanel data={{ test: true }} />
        </TestProvider>,
      );
      expect(
        screen.queryByRole("button", { name: /close/i }),
      ).not.toBeInTheDocument();
    });

    it("should call onClose when close button clicked", async () => {
      const onClose = vi.fn();
      const user = userEvent.setup();

      render(
        <TestProvider>
          <OTELDetailsPanel data={{ test: true }} onClose={onClose} />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /close/i }));

      expect(onClose).toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Empty State Tests
  // ===========================================================================

  describe("empty state", () => {
    it("should handle empty object", () => {
      render(
        <TestProvider>
          <OTELDetailsPanel data={{}} />
        </TestProvider>,
      );
      expect(screen.getByText(/no data/i)).toBeInTheDocument();
    });

    it("should handle null data gracefully", () => {
      render(
        <TestProvider>
          <OTELDetailsPanel data={null as unknown as Record<string, unknown>} />
        </TestProvider>,
      );
      expect(screen.getByText(/no data/i)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Accessibility Tests
  // ===========================================================================

  describe("accessibility", () => {
    it("should have role=region with accessible name", () => {
      render(
        <TestProvider>
          <OTELDetailsPanel data={{ test: true }} title="Details" />
        </TestProvider>,
      );
      const region = screen.getByRole("region");
      expect(region).toHaveAccessibleName("Details");
    });

    it("should have keyboard-navigable tabs in tabbed variant", async () => {
      const user = userEvent.setup();
      const tabs = [
        { key: "a", label: "Tab A", data: { a: 1 } },
        { key: "b", label: "Tab B", data: { b: 2 } },
      ];
      render(
        <TestProvider>
          <OTELDetailsPanel data={{}} variant="tabbed" tabs={tabs} />
        </TestProvider>,
      );

      const tabA = screen.getByRole("tab", { name: "Tab A" });
      tabA.focus();

      // Navigate with arrow key
      await user.keyboard("{ArrowRight}");

      const tabB = screen.getByRole("tab", { name: "Tab B" });
      expect(tabB).toHaveFocus();
    });
  });

  // ===========================================================================
  // Custom className Tests
  // ===========================================================================

  describe("className prop", () => {
    it("should merge custom className", () => {
      render(
        <TestProvider>
          <OTELDetailsPanel data={{ test: true }} className="custom-class" />
        </TestProvider>,
      );
      const region = screen.getByRole("region");
      expect(region).toHaveClass("custom-class");
    });
  });

  // ===========================================================================
  // Headers Variant Tests
  // ===========================================================================

  describe("headers variant", () => {
    it("should render headers in key-value format", () => {
      const data = {
        "Content-Type": "application/json",
        Authorization: "Bearer token123",
        "X-Request-ID": "abc-123",
      };
      render(
        <TestProvider>
          <OTELDetailsPanel data={data} variant="headers" />
        </TestProvider>,
      );

      expect(screen.getByText("Content-Type")).toBeInTheDocument();
      expect(screen.getByText("application/json")).toBeInTheDocument();
    });

    it("should display headers in monospace font", () => {
      const data = { "Content-Type": "application/json" };
      render(
        <TestProvider>
          <OTELDetailsPanel data={data} variant="headers" />
        </TestProvider>,
      );

      // Values should use monospace font
      const valueElement = screen.getByText("application/json");
      expect(valueElement).toHaveClass("font-mono");
    });
  });
});
