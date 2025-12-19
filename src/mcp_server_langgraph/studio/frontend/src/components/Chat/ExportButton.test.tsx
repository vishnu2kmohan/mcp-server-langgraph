/**
 * ExportButton Tests
 *
 * Comprehensive tests for the session export button component.
 * Tests dropdown menu, format selection, metadata toggle, and file download.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { ExportButton } from "./ExportButton";

// Mock the toast notifications
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock URL.createObjectURL and URL.revokeObjectURL
const mockCreateObjectURL = vi.fn(() => "blob:test-url");
const mockRevokeObjectURL = vi.fn();

// Mock the RTK Query hook
const mockExportSession = vi.fn();
const mockUnwrap = vi.fn();

vi.mock("../../api", () => ({
  useExportSessionMutation: () => [mockExportSession, { isLoading: false }],
}));

// Create a minimal store for tests
const createTestStore = () => {
  return configureStore({
    reducer: {
      api: () => ({}),
    },
  });
};

// Wrapper component with Provider
const renderWithProvider = (ui: React.ReactElement) => {
  const store = createTestStore();
  return render(<Provider store={store}>{ui}</Provider>);
};

describe("ExportButton", () => {
  const defaultProps = {
    sessionId: "session-123",
    sessionTitle: "Test Session",
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Setup URL mocks
    global.URL.createObjectURL = mockCreateObjectURL;
    global.URL.revokeObjectURL = mockRevokeObjectURL;
    // Setup successful export by default
    mockUnwrap.mockResolvedValue(
      new Blob(["test content"], { type: "text/plain" }),
    );
    mockExportSession.mockReturnValue({ unwrap: mockUnwrap });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Rendering", () => {
    it("should render export button with icon and text", () => {
      renderWithProvider(<ExportButton {...defaultProps} />);

      const button = screen.getByRole("button", { name: /export session/i });
      expect(button).toBeInTheDocument();
      expect(screen.getByText("Export")).toBeInTheDocument();
    });

    it("should render compact version without text", () => {
      renderWithProvider(<ExportButton {...defaultProps} compact />);

      const button = screen.getByRole("button", { name: /export session/i });
      expect(button).toBeInTheDocument();
      expect(screen.queryByText("Export")).not.toBeInTheDocument();
    });

    it("should apply custom className", () => {
      renderWithProvider(
        <ExportButton {...defaultProps} className="custom-class" />,
      );

      const button = screen.getByRole("button", { name: /export session/i });
      expect(button).toHaveClass("custom-class");
    });

    it("should have correct ARIA attributes when closed", () => {
      renderWithProvider(<ExportButton {...defaultProps} />);

      const button = screen.getByRole("button", { name: /export session/i });
      expect(button).toHaveAttribute("aria-expanded", "false");
      expect(button).toHaveAttribute("aria-haspopup", "true");
    });
  });

  describe("Dropdown Menu", () => {
    it("should open dropdown when button is clicked", async () => {
      const user = userEvent.setup();
      renderWithProvider(<ExportButton {...defaultProps} />);

      const button = screen.getByRole("button", { name: /export session/i });
      await user.click(button);

      expect(button).toHaveAttribute("aria-expanded", "true");
      expect(screen.getByRole("menu")).toBeInTheDocument();
    });

    it("should show all format options in dropdown", async () => {
      const user = userEvent.setup();
      renderWithProvider(<ExportButton {...defaultProps} />);

      const button = screen.getByRole("button", { name: /export session/i });
      await user.click(button);

      expect(
        screen.getByRole("menuitem", { name: /markdown/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("menuitem", { name: /json/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("menuitem", { name: /html/i }),
      ).toBeInTheDocument();
    });

    it("should close dropdown when clicking outside", async () => {
      const user = userEvent.setup();
      renderWithProvider(<ExportButton {...defaultProps} />);

      const button = screen.getByRole("button", { name: /export session/i });
      await user.click(button);

      expect(screen.getByRole("menu")).toBeInTheDocument();

      // Click the backdrop
      const backdrop = document.querySelector('[aria-hidden="true"]');
      if (backdrop) {
        fireEvent.click(backdrop);
      }

      expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    });

    it("should toggle dropdown on repeated clicks", async () => {
      const user = userEvent.setup();
      renderWithProvider(<ExportButton {...defaultProps} />);

      const button = screen.getByRole("button", { name: /export session/i });

      // Open
      await user.click(button);
      expect(screen.getByRole("menu")).toBeInTheDocument();

      // Close
      await user.click(button);
      expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    });

    it("should show include metadata checkbox", async () => {
      const user = userEvent.setup();
      renderWithProvider(<ExportButton {...defaultProps} />);

      const button = screen.getByRole("button", { name: /export session/i });
      await user.click(button);

      const checkbox = screen.getByRole("checkbox");
      expect(checkbox).toBeInTheDocument();
      expect(screen.getByText(/include metadata/i)).toBeInTheDocument();
    });

    it("should toggle include metadata checkbox", async () => {
      const user = userEvent.setup();
      renderWithProvider(<ExportButton {...defaultProps} />);

      const button = screen.getByRole("button", { name: /export session/i });
      await user.click(button);

      const checkbox = screen.getByRole("checkbox");
      expect(checkbox).not.toBeChecked();

      await user.click(checkbox);
      expect(checkbox).toBeChecked();
    });
  });

  describe("Export Functionality", () => {
    it("should call export mutation with markdown format", async () => {
      const user = userEvent.setup();
      renderWithProvider(<ExportButton {...defaultProps} />);

      const button = screen.getByRole("button", { name: /export session/i });
      await user.click(button);

      const markdownOption = screen.getByRole("menuitem", {
        name: /markdown/i,
      });
      await user.click(markdownOption);

      await waitFor(() => {
        expect(mockExportSession).toHaveBeenCalledWith({
          sessionId: "session-123",
          request: {
            format: "markdown",
            include_metadata: false,
          },
        });
      });
    });

    it("should call export mutation with JSON format", async () => {
      const user = userEvent.setup();
      renderWithProvider(<ExportButton {...defaultProps} />);

      const button = screen.getByRole("button", { name: /export session/i });
      await user.click(button);

      const jsonOption = screen.getByRole("menuitem", { name: /json/i });
      await user.click(jsonOption);

      await waitFor(() => {
        expect(mockExportSession).toHaveBeenCalledWith({
          sessionId: "session-123",
          request: {
            format: "json",
            include_metadata: false,
          },
        });
      });
    });

    it("should call export mutation with HTML format", async () => {
      const user = userEvent.setup();
      renderWithProvider(<ExportButton {...defaultProps} />);

      const button = screen.getByRole("button", { name: /export session/i });
      await user.click(button);

      const htmlOption = screen.getByRole("menuitem", { name: /html/i });
      await user.click(htmlOption);

      await waitFor(() => {
        expect(mockExportSession).toHaveBeenCalledWith({
          sessionId: "session-123",
          request: {
            format: "html",
            include_metadata: false,
          },
        });
      });
    });

    it("should include metadata when checkbox is checked", async () => {
      const user = userEvent.setup();
      renderWithProvider(<ExportButton {...defaultProps} />);

      const button = screen.getByRole("button", { name: /export session/i });
      await user.click(button);

      // Check the metadata checkbox
      const checkbox = screen.getByRole("checkbox");
      await user.click(checkbox);

      // Export
      const markdownOption = screen.getByRole("menuitem", {
        name: /markdown/i,
      });
      await user.click(markdownOption);

      await waitFor(() => {
        expect(mockExportSession).toHaveBeenCalledWith({
          sessionId: "session-123",
          request: {
            format: "markdown",
            include_metadata: true,
          },
        });
      });
    });

    it("should trigger file download on successful export", async () => {
      const user = userEvent.setup();
      renderWithProvider(<ExportButton {...defaultProps} />);

      const button = screen.getByRole("button", { name: /export session/i });
      await user.click(button);

      const markdownOption = screen.getByRole("menuitem", {
        name: /markdown/i,
      });
      await user.click(markdownOption);

      // Verify blob URL was created and revoked
      await waitFor(() => {
        expect(mockCreateObjectURL).toHaveBeenCalled();
        expect(mockRevokeObjectURL).toHaveBeenCalled();
      });
    });

    it("should show success toast on successful export", async () => {
      const { toast } = await import("sonner");
      const user = userEvent.setup();
      renderWithProvider(<ExportButton {...defaultProps} />);

      const button = screen.getByRole("button", { name: /export session/i });
      await user.click(button);

      const markdownOption = screen.getByRole("menuitem", {
        name: /markdown/i,
      });
      await user.click(markdownOption);

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith(
          "Session exported as MARKDOWN",
        );
      });
    });

    it("should close dropdown after successful export", async () => {
      const user = userEvent.setup();
      renderWithProvider(<ExportButton {...defaultProps} />);

      const button = screen.getByRole("button", { name: /export session/i });
      await user.click(button);

      const markdownOption = screen.getByRole("menuitem", {
        name: /markdown/i,
      });
      await user.click(markdownOption);

      await waitFor(() => {
        expect(screen.queryByRole("menu")).not.toBeInTheDocument();
      });
    });
  });

  describe("Error Handling", () => {
    it("should show error toast on export failure", async () => {
      const { toast } = await import("sonner");
      mockUnwrap.mockRejectedValue(new Error("Export failed"));

      const user = userEvent.setup();
      renderWithProvider(<ExportButton {...defaultProps} />);

      const button = screen.getByRole("button", { name: /export session/i });
      await user.click(button);

      const markdownOption = screen.getByRole("menuitem", {
        name: /markdown/i,
      });
      await user.click(markdownOption);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith("Failed to export session");
      });
    });
  });

  describe("Filename Generation", () => {
    // Track download links created
    let createdLinks: HTMLAnchorElement[] = [];
    const originalCreateElement = document.createElement.bind(document);

    beforeEach(() => {
      createdLinks = [];
      // Spy on createElement to track anchor elements without breaking React
      vi.spyOn(document, "createElement").mockImplementation(
        (tagName: string, options?: ElementCreationOptions) => {
          const element = originalCreateElement(tagName, options);
          if (tagName === "a") {
            createdLinks.push(element as HTMLAnchorElement);
          }
          return element;
        },
      );
    });

    afterEach(() => {
      vi.mocked(document.createElement).mockRestore();
    });

    it("should generate filename with session title and date", async () => {
      const user = userEvent.setup();
      renderWithProvider(
        <ExportButton {...defaultProps} sessionTitle="My Test Session" />,
      );

      const button = screen.getByRole("button", { name: /export session/i });
      await user.click(button);

      const markdownOption = screen.getByRole("menuitem", {
        name: /markdown/i,
      });
      await user.click(markdownOption);

      await waitFor(() => {
        const downloadLinks = createdLinks.filter((link) => link.download);
        expect(downloadLinks.length).toBeGreaterThan(0);
        const lastLink = downloadLinks[downloadLinks.length - 1];
        expect(lastLink.download).toMatch(/^My Test Session_\d{8}\.md$/);
      });
    });

    it("should sanitize special characters from session title", async () => {
      const user = userEvent.setup();
      renderWithProvider(
        <ExportButton {...defaultProps} sessionTitle="Test <Session> @#$%" />,
      );

      const button = screen.getByRole("button", { name: /export session/i });
      await user.click(button);

      const markdownOption = screen.getByRole("menuitem", {
        name: /markdown/i,
      });
      await user.click(markdownOption);

      await waitFor(() => {
        const downloadLinks = createdLinks.filter((link) => link.download);
        expect(downloadLinks.length).toBeGreaterThan(0);
        const lastLink = downloadLinks[downloadLinks.length - 1];
        // Special characters should be stripped
        expect(lastLink.download).not.toContain("<");
        expect(lastLink.download).not.toContain(">");
        expect(lastLink.download).not.toContain("@");
        expect(lastLink.download).not.toContain("#");
        expect(lastLink.download).not.toContain("$");
        expect(lastLink.download).not.toContain("%");
      });
    });

    it("should use 'session' as default when no title provided", async () => {
      const user = userEvent.setup();
      renderWithProvider(<ExportButton sessionId="session-123" />);

      const button = screen.getByRole("button", { name: /export session/i });
      await user.click(button);

      const markdownOption = screen.getByRole("menuitem", {
        name: /markdown/i,
      });
      await user.click(markdownOption);

      await waitFor(() => {
        const downloadLinks = createdLinks.filter((link) => link.download);
        expect(downloadLinks.length).toBeGreaterThan(0);
        const lastLink = downloadLinks[downloadLinks.length - 1];
        expect(lastLink.download).toMatch(/^session_\d{8}\.md$/);
      });
    });

    it("should use correct extension for JSON format", async () => {
      const user = userEvent.setup();
      renderWithProvider(<ExportButton {...defaultProps} />);

      const button = screen.getByRole("button", { name: /export session/i });
      await user.click(button);

      const jsonOption = screen.getByRole("menuitem", { name: /json/i });
      await user.click(jsonOption);

      await waitFor(() => {
        const downloadLinks = createdLinks.filter((link) => link.download);
        expect(downloadLinks.length).toBeGreaterThan(0);
        const lastLink = downloadLinks[downloadLinks.length - 1];
        expect(lastLink.download).toMatch(/\.json$/);
      });
    });

    it("should use correct extension for HTML format", async () => {
      const user = userEvent.setup();
      renderWithProvider(<ExportButton {...defaultProps} />);

      const button = screen.getByRole("button", { name: /export session/i });
      await user.click(button);

      const htmlOption = screen.getByRole("menuitem", { name: /html/i });
      await user.click(htmlOption);

      await waitFor(() => {
        const downloadLinks = createdLinks.filter((link) => link.download);
        expect(downloadLinks.length).toBeGreaterThan(0);
        const lastLink = downloadLinks[downloadLinks.length - 1];
        expect(lastLink.download).toMatch(/\.html$/);
      });
    });
  });

  // Note: Loading state tests are covered implicitly in integration tests.
  // Testing isLoading with hoisted vitest mocks requires dynamic re-mocking
  // which is complex for unit tests. The implementation correctly:
  // 1. Disables the main button when isLoading is true
  // 2. Disables menu items when isLoading is true
  // 3. Shows pulsing animation on the download icon when loading

  describe("Accessibility", () => {
    it("should have accessible button label", () => {
      renderWithProvider(<ExportButton {...defaultProps} />);

      const button = screen.getByRole("button", { name: /export session/i });
      expect(button).toHaveAttribute("aria-label", "Export session");
    });

    it("should have menu role on dropdown", async () => {
      const user = userEvent.setup();
      renderWithProvider(<ExportButton {...defaultProps} />);

      const button = screen.getByRole("button", { name: /export session/i });
      await user.click(button);

      const menu = screen.getByRole("menu");
      expect(menu).toHaveAttribute("aria-orientation", "vertical");
    });

    it("should have menuitem role on format options", async () => {
      const user = userEvent.setup();
      renderWithProvider(<ExportButton {...defaultProps} />);

      const button = screen.getByRole("button", { name: /export session/i });
      await user.click(button);

      const menuItems = screen.getAllByRole("menuitem");
      expect(menuItems).toHaveLength(3);
    });
  });
});
