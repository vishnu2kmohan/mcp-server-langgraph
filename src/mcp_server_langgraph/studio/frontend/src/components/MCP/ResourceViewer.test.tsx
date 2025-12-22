/**
 * ResourceViewer Component Tests (TDD)
 *
 * Tests for the resource viewer that allows users to:
 * - View available MCP resources
 * - Read resource content
 * - Display different content types (text, binary)
 *
 * Following TDD: RED phase - write failing tests first
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";

import { api } from "../../api";

// Mock the RTK Query hooks
const mockUseListMcpResourcesQuery = vi.fn();
const mockUseReadMcpResourceMutation = vi.fn();

vi.mock("../../api", async () => {
  const actual = await vi.importActual("../../api");
  return {
    ...actual,
    useListMcpResourcesQuery: () => mockUseListMcpResourcesQuery(),
    useReadMcpResourceMutation: () => mockUseReadMcpResourceMutation(),
  };
});

// Import after mocking
import { ResourceViewer } from "./ResourceViewer";

// =============================================================================
// Mock Data
// =============================================================================

const MOCK_RESOURCES = {
  resources: [
    {
      uri: "file:///project/README.md",
      name: "README.md",
      title: "Project README",
      description: "Main project documentation",
      mime_type: "text/markdown",
    },
    {
      uri: "file:///project/src/main.ts",
      name: "main.ts",
      title: "Main Entry",
      description: "Application entry point",
      mime_type: "text/typescript",
    },
    {
      uri: "file:///project/logo.png",
      name: "logo.png",
      title: "Logo",
      description: "Project logo",
      mime_type: "image/png",
    },
  ],
};

const MOCK_TEXT_CONTENT = {
  contents: [
    {
      uri: "file:///project/README.md",
      mime_type: "text/markdown",
      text: "# Project README\n\nThis is the project documentation.",
      blob: null,
    },
  ],
};

const MOCK_BINARY_CONTENT = {
  contents: [
    {
      uri: "file:///project/logo.png",
      mime_type: "image/png",
      text: null,
      blob: "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    },
  ],
};

// =============================================================================
// Test Store Setup
// =============================================================================

const createTestStore = () =>
  configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });

const renderWithProvider = (ui: React.ReactElement) => {
  return render(<Provider store={createTestStore()}>{ui}</Provider>);
};

// =============================================================================
// Tests
// =============================================================================

describe("ResourceViewer", () => {
  const mockOnClose = vi.fn();
  const mockReadResource = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock implementations
    mockUseListMcpResourcesQuery.mockReturnValue({
      data: MOCK_RESOURCES,
      isLoading: false,
      error: null,
    });

    mockUseReadMcpResourceMutation.mockReturnValue([
      mockReadResource,
      { isLoading: false, error: null },
    ]);
  });

  describe("rendering", () => {
    it("renders viewer when open", () => {
      renderWithProvider(<ResourceViewer open={true} onClose={mockOnClose} />);

      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(screen.getByText("Resource Viewer")).toBeInTheDocument();
    });

    it("does not render when closed", () => {
      renderWithProvider(<ResourceViewer open={false} onClose={mockOnClose} />);

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("shows loading state when fetching resources", () => {
      mockUseListMcpResourcesQuery.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });

      renderWithProvider(<ResourceViewer open={true} onClose={mockOnClose} />);

      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });

    it("shows error state when resources fetch fails", () => {
      mockUseListMcpResourcesQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: { message: "Failed to fetch resources" },
      });

      renderWithProvider(<ResourceViewer open={true} onClose={mockOnClose} />);

      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });

  describe("resource list", () => {
    it("displays list of available resources", () => {
      renderWithProvider(<ResourceViewer open={true} onClose={mockOnClose} />);

      expect(screen.getByText("README.md")).toBeInTheDocument();
      expect(screen.getByText("main.ts")).toBeInTheDocument();
      expect(screen.getByText("logo.png")).toBeInTheDocument();
    });

    it("shows resource description on hover or selection", async () => {
      renderWithProvider(<ResourceViewer open={true} onClose={mockOnClose} />);

      const readmeItem = screen.getByText("README.md");
      await userEvent.click(readmeItem);

      expect(
        screen.getByText("Main project documentation")
      ).toBeInTheDocument();
    });

    it("shows mime type for each resource", () => {
      renderWithProvider(<ResourceViewer open={true} onClose={mockOnClose} />);

      expect(screen.getByText(/text\/markdown/)).toBeInTheDocument();
      expect(screen.getByText(/text\/typescript/)).toBeInTheDocument();
      expect(screen.getByText(/image\/png/)).toBeInTheDocument();
    });
  });

  describe("resource reading", () => {
    it("reads text resource content on selection", async () => {
      mockReadResource.mockReturnValue({
        unwrap: () => Promise.resolve(MOCK_TEXT_CONTENT),
      });

      renderWithProvider(<ResourceViewer open={true} onClose={mockOnClose} />);

      const readmeItem = screen.getByText("README.md");
      await userEvent.click(readmeItem);

      expect(mockReadResource).toHaveBeenCalledWith({
        uri: "file:///project/README.md",
      });
    });

    it("displays text content in a code block", async () => {
      mockReadResource.mockReturnValue({
        unwrap: () => Promise.resolve(MOCK_TEXT_CONTENT),
      });

      renderWithProvider(<ResourceViewer open={true} onClose={mockOnClose} />);

      const readmeItem = screen.getByText("README.md");
      await userEvent.click(readmeItem);

      await waitFor(() => {
        expect(
          screen.getByText(/This is the project documentation/)
        ).toBeInTheDocument();
      });
    });

    it("displays binary content as base64 data", async () => {
      mockReadResource.mockReturnValue({
        unwrap: () => Promise.resolve(MOCK_BINARY_CONTENT),
      });

      renderWithProvider(<ResourceViewer open={true} onClose={mockOnClose} />);

      const logoItem = screen.getByText("logo.png");
      await userEvent.click(logoItem);

      await waitFor(() => {
        // For images, we should show an img tag or a download link
        const img = screen.getByRole("img");
        expect(img).toBeInTheDocument();
      });
    });

    it("shows loading state while reading content", async () => {
      mockReadResource.mockReturnValue({
        unwrap: () =>
          new Promise((resolve) =>
            setTimeout(() => resolve(MOCK_TEXT_CONTENT), 1000)
          ),
      });

      mockUseReadMcpResourceMutation.mockReturnValue([
        mockReadResource,
        { isLoading: true, error: null },
      ]);

      renderWithProvider(<ResourceViewer open={true} onClose={mockOnClose} />);

      const readmeItem = screen.getByText("README.md");
      await userEvent.click(readmeItem);

      expect(screen.getByText(/loading content/i)).toBeInTheDocument();
    });

    it("shows error when reading fails", async () => {
      mockReadResource.mockReturnValue({
        unwrap: () => Promise.reject(new Error("Failed to read resource")),
      });

      renderWithProvider(<ResourceViewer open={true} onClose={mockOnClose} />);

      const readmeItem = screen.getByText("README.md");
      await userEvent.click(readmeItem);

      await waitFor(() => {
        expect(screen.getByText(/failed to read/i)).toBeInTheDocument();
      });
    });
  });

  describe("content display", () => {
    it("formats markdown content properly", async () => {
      mockReadResource.mockReturnValue({
        unwrap: () => Promise.resolve(MOCK_TEXT_CONTENT),
      });

      renderWithProvider(<ResourceViewer open={true} onClose={mockOnClose} />);

      const readmeItem = screen.getByText("README.md");
      await userEvent.click(readmeItem);

      await waitFor(() => {
        // Should display the content text (unique phrase from content)
        expect(
          screen.getByText(/This is the project documentation/)
        ).toBeInTheDocument();
      });
    });

    it("allows copying content to clipboard", async () => {
      const mockWriteText = vi.fn();
      Object.assign(navigator, {
        clipboard: { writeText: mockWriteText },
      });

      mockReadResource.mockReturnValue({
        unwrap: () => Promise.resolve(MOCK_TEXT_CONTENT),
      });

      renderWithProvider(<ResourceViewer open={true} onClose={mockOnClose} />);

      const readmeItem = screen.getByText("README.md");
      await userEvent.click(readmeItem);

      await waitFor(async () => {
        const copyButton = screen.getByRole("button", { name: /copy/i });
        await userEvent.click(copyButton);
        expect(mockWriteText).toHaveBeenCalled();
      });
    });
  });

  describe("dialog actions", () => {
    it("calls onClose when close button clicked", async () => {
      renderWithProvider(<ResourceViewer open={true} onClose={mockOnClose} />);

      const closeButton = screen.getByRole("button", { name: /close/i });
      await userEvent.click(closeButton);

      expect(mockOnClose).toHaveBeenCalled();
    });

    it("resets selection when dialog is reopened", async () => {
      mockReadResource.mockReturnValue({
        unwrap: () => Promise.resolve(MOCK_TEXT_CONTENT),
      });

      const { rerender } = renderWithProvider(
        <ResourceViewer open={true} onClose={mockOnClose} />
      );

      // Select a resource
      const readmeItem = screen.getByText("README.md");
      await userEvent.click(readmeItem);

      await waitFor(() => {
        expect(
          screen.getByText(/This is the project documentation/)
        ).toBeInTheDocument();
      });

      // Close and reopen
      rerender(
        <Provider store={createTestStore()}>
          <ResourceViewer open={false} onClose={mockOnClose} />
        </Provider>
      );

      rerender(
        <Provider store={createTestStore()}>
          <ResourceViewer open={true} onClose={mockOnClose} />
        </Provider>
      );

      // Content should be reset
      expect(
        screen.queryByText(/This is the project documentation/)
      ).not.toBeInTheDocument();
    });
  });

  describe("empty state", () => {
    it("shows empty state when no resources available", () => {
      mockUseListMcpResourcesQuery.mockReturnValue({
        data: { resources: [] },
        isLoading: false,
        error: null,
      });

      renderWithProvider(<ResourceViewer open={true} onClose={mockOnClose} />);

      expect(screen.getByText(/no resources/i)).toBeInTheDocument();
    });
  });
});
