/**
 * ArtifactsPage Tests
 *
 * TDD tests for the artifact browser page.
 * Tests cover:
 * - Rendering artifacts from loader data
 * - Preview modal functionality
 * - Download (blob creation and trigger)
 * - Delete (confirmation, API call, revalidation)
 * - Search filtering
 * - View mode switching (grid/list)
 *
 * Updated: Uses custom test wrapper with Redux provider for AIEmptyState.
 */

import type { ReactNode } from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  within,
  cleanup,
} from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { ArtifactsPage } from "./ArtifactsPage";
import personaReducer from "../store/slices/personaSlice";
import sessionReducer from "../store/slices/sessionSlice";
import type { CanvasArtifact } from "../types/artifacts";
import type { ArtifactsLoaderData } from "../router/loaders";

// Mock useRouteLoaderData and useRevalidator
const mockRevalidate = vi.fn();
vi.mock("react-router", async (importOriginal) => {
  const actual = (await importOriginal()) as object;
  return {
    ...actual,
    useRouteLoaderData: vi.fn(),
    useRevalidator: () => ({
      revalidate: mockRevalidate,
      state: "idle",
    }),
  };
});

// Import the mocked function for manipulation
import { useRouteLoaderData } from "react-router";
const mockUseRouteLoaderData = vi.mocked(useRouteLoaderData);

// Mock getAuthToken
vi.mock("../utils/storage", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../utils/storage")>();
  return {
    ...actual,
    getAuthToken: vi.fn(() => "test-token"),
  };
});

// Mock devLogger
vi.mock("../utils/devLogger", () => ({
  devLogger: {
    withPrefix: () => ({
      debug: vi.fn(),
      warn: vi.fn(),
      error: vi.fn(),
    }),
  },
}));

// Mock sessionTelemetry
vi.mock("../utils/sessionTelemetry", () => ({
  sessionTelemetry: {
    trackArtifactDelete: vi.fn(),
  },
}));

// Mock the API module for RTK Query hooks (used by AIEmptyState)
vi.mock("../api", async () => {
  const actual = await vi.importActual("../api");
  return {
    ...actual,
    useGetEmptyStateSuggestionsMutation: () => [
      vi.fn(),
      { isLoading: false, data: null },
    ],
  };
});
// Sample test artifacts
const createTestArtifact = (
  overrides: Partial<CanvasArtifact> = {},
): CanvasArtifact => ({
  id: "artifact-1",
  sessionId: "session-1",
  title: "test-file",
  contentType: "code",
  content: "console.log('hello');",
  createdAt: "2025-01-01T10:00:00Z",
  updatedAt: "2025-01-01T11:00:00Z",
  version: 1,
  ...overrides,
});

const testArtifacts: CanvasArtifact[] = [
  createTestArtifact({
    id: "art-1",
    title: "main.py",
    contentType: "code",
    editMetadata: { language: "python" },
  }),
  createTestArtifact({
    id: "art-2",
    title: "README",
    contentType: "markdown",
    content: "# Hello",
  }),
  createTestArtifact({
    id: "art-3",
    title: "config",
    contentType: "json",
    content: '{"key": "value"}',
  }),
];

/**
 * Custom test wrapper for ArtifactsPage tests.
 * Provides Redux store with persona state for AIEmptyState.
 */
function ArtifactsPageTestWrapper({ children }: { children: ReactNode }) {
  const store = configureStore({
    reducer: {
      persona: personaReducer,
      session: sessionReducer,
    },
  });

  const router = createMemoryRouter([{ path: "*", element: children }], {
    initialEntries: ["/"],
  });

  return (
    <Provider store={store}>
      <RouterProvider router={router} />
    </Provider>
  );
}

// Helper to render with router and Redux provider
const renderArtifactsPage = () => {
  return render(
    <ArtifactsPageTestWrapper>
      <ArtifactsPage />
    </ArtifactsPageTestWrapper>,
  );
};

describe("ArtifactsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default: return test artifacts
    mockUseRouteLoaderData.mockReturnValue({
      artifacts: testArtifacts,
      total: 3,
    } as ArtifactsLoaderData);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================
  describe("Rendering", () => {
    it("should render the files page with header", () => {
      renderArtifactsPage();

      expect(screen.getByTestId("artifacts-page")).toBeInTheDocument();
      expect(screen.getByText("Artifacts")).toBeInTheDocument();
    });

    it("should display artifact count in header", () => {
      renderArtifactsPage();

      expect(screen.getByText("3 artifacts")).toBeInTheDocument();
    });

    it("should render files from loader data in grid view by default", () => {
      renderArtifactsPage();

      expect(screen.getByTestId("file-card-art-1")).toBeInTheDocument();
      expect(screen.getByTestId("file-card-art-2")).toBeInTheDocument();
      expect(screen.getByTestId("file-card-art-3")).toBeInTheDocument();
    });

    it("should show file names with extensions", () => {
      renderArtifactsPage();

      expect(screen.getByText("main.py")).toBeInTheDocument();
      expect(screen.getByText("README.md")).toBeInTheDocument();
      expect(screen.getByText("config.json")).toBeInTheDocument();
    });

    it("should show empty state when no artifacts", () => {
      mockUseRouteLoaderData.mockReturnValue({
        artifacts: [],
        total: 0,
      } as ArtifactsLoaderData);

      renderArtifactsPage();

      expect(screen.getByText("No artifacts yet")).toBeInTheDocument();
    });

    it("should show error state when loader fails", () => {
      mockUseRouteLoaderData.mockReturnValue({
        artifacts: [],
        total: 0,
        error: "Network connection lost",
      } as ArtifactsLoaderData);

      renderArtifactsPage();

      expect(screen.getByTestId("artifacts-page-error")).toBeInTheDocument();
      expect(screen.getByText("Network connection lost")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // View Mode Tests
  // ===========================================================================
  describe("View Mode", () => {
    it("should switch to list view when list button is clicked", () => {
      renderArtifactsPage();

      fireEvent.click(screen.getByTestId("view-list"));

      // In list view, we use file-row-* instead of file-card-*
      expect(screen.getByTestId("file-row-art-1")).toBeInTheDocument();
    });

    it("should switch back to grid view when grid button is clicked", () => {
      renderArtifactsPage();

      // Switch to list first
      fireEvent.click(screen.getByTestId("view-list"));
      expect(screen.getByTestId("file-row-art-1")).toBeInTheDocument();

      // Switch back to grid
      fireEvent.click(screen.getByTestId("view-grid"));
      expect(screen.getByTestId("file-card-art-1")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Search Tests
  // ===========================================================================
  describe("Search", () => {
    it("should filter files by search query", () => {
      renderArtifactsPage();

      const searchInput = screen.getByTestId("file-search");
      fireEvent.change(searchInput, { target: { value: "main" } });

      expect(screen.getByTestId("file-card-art-1")).toBeInTheDocument();
      expect(screen.queryByTestId("file-card-art-2")).not.toBeInTheDocument();
      expect(screen.queryByTestId("file-card-art-3")).not.toBeInTheDocument();
    });

    it("should show 'No artifacts match' when search has no results", () => {
      renderArtifactsPage();

      const searchInput = screen.getByTestId("file-search");
      fireEvent.change(searchInput, { target: { value: "nonexistent" } });

      // AIEmptyState generates: No {context} matching "{searchQuery}"
      expect(
        screen.getByText('No artifacts matching "nonexistent"'),
      ).toBeInTheDocument();
    });

    it("should update artifact count based on search results", () => {
      renderArtifactsPage();

      const searchInput = screen.getByTestId("file-search");
      fireEvent.change(searchInput, { target: { value: "main" } });

      expect(screen.getByText("1 artifacts")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Preview Tests
  // ===========================================================================
  describe("Preview", () => {
    it("should open preview modal when clicking on a file card", () => {
      renderArtifactsPage();

      fireEvent.click(screen.getByTestId("file-card-art-1"));

      expect(screen.getByTestId("preview-modal")).toBeInTheDocument();
    });

    it("should show file name in preview modal header", () => {
      renderArtifactsPage();

      fireEvent.click(screen.getByTestId("file-card-art-1"));

      // Modal should show the file name
      const modal = screen.getByTestId("preview-modal");
      expect(modal).toHaveTextContent("main.py");
    });

    it("should show file content in preview modal", () => {
      renderArtifactsPage();

      fireEvent.click(screen.getByTestId("file-card-art-1"));

      expect(screen.getByText("console.log('hello');")).toBeInTheDocument();
    });

    it("should close preview modal when clicking the X button", () => {
      renderArtifactsPage();

      // Open preview
      fireEvent.click(screen.getByTestId("file-card-art-1"));
      expect(screen.getByTestId("preview-modal")).toBeInTheDocument();

      // Close preview
      fireEvent.click(screen.getByLabelText("Close preview"));

      expect(screen.queryByTestId("preview-modal")).not.toBeInTheDocument();
    });

    it("should close preview modal when clicking backdrop", () => {
      renderArtifactsPage();

      // Open preview
      fireEvent.click(screen.getByTestId("file-card-art-1"));
      expect(screen.getByTestId("preview-modal")).toBeInTheDocument();

      // Click backdrop
      fireEvent.click(screen.getByTestId("preview-modal"));

      expect(screen.queryByTestId("preview-modal")).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Download Tests
  // ===========================================================================
  describe("Download", () => {
    let mockCreateObjectURL: ReturnType<typeof vi.fn>;
    let mockRevokeObjectURL: ReturnType<typeof vi.fn>;
    let originalCreateObjectURL: typeof URL.createObjectURL;
    let originalRevokeObjectURL: typeof URL.revokeObjectURL;

    beforeEach(() => {
      mockCreateObjectURL = vi.fn(() => "blob:test-url");
      mockRevokeObjectURL = vi.fn();

      originalCreateObjectURL = URL.createObjectURL;
      originalRevokeObjectURL = URL.revokeObjectURL;

      URL.createObjectURL = mockCreateObjectURL;
      URL.revokeObjectURL = mockRevokeObjectURL;
    });

    afterEach(() => {
      URL.createObjectURL = originalCreateObjectURL;
      URL.revokeObjectURL = originalRevokeObjectURL;
    });

    it("should create blob and trigger download when clicking download button", () => {
      renderArtifactsPage();

      // Find and click download button on first file card
      const fileCard = screen.getByTestId("file-card-art-1");
      const downloadButton = fileCard.querySelector(
        'button[aria-label="Download"]',
      );
      expect(downloadButton).toBeInTheDocument();

      // Mock anchor element creation AFTER render but BEFORE click
      const mockClick = vi.fn();
      const mockAnchor = { href: "", download: "", click: mockClick };
      const realCreateElement = document.createElement.bind(document);
      vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
        if (tag === "a") return mockAnchor as unknown as HTMLAnchorElement;
        return realCreateElement(tag);
      });
      vi.spyOn(document.body, "appendChild").mockImplementation((node) => node);
      vi.spyOn(document.body, "removeChild").mockImplementation((node) => node);

      fireEvent.click(downloadButton!);

      expect(mockCreateObjectURL).toHaveBeenCalledWith(expect.any(Blob));
      expect(mockClick).toHaveBeenCalled();
      expect(mockRevokeObjectURL).toHaveBeenCalledWith("blob:test-url");

      vi.restoreAllMocks();
    });

    it("should download with correct filename", () => {
      renderArtifactsPage();

      const fileCard = screen.getByTestId("file-card-art-1");
      const downloadButton = fileCard.querySelector(
        'button[aria-label="Download"]',
      );

      // Mock anchor element creation AFTER render but BEFORE click
      const mockAnchor = { href: "", download: "", click: vi.fn() };
      const realCreateElement = document.createElement.bind(document);
      vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
        if (tag === "a") return mockAnchor as unknown as HTMLAnchorElement;
        return realCreateElement(tag);
      });
      vi.spyOn(document.body, "appendChild").mockImplementation((node) => node);
      vi.spyOn(document.body, "removeChild").mockImplementation((node) => node);

      fireEvent.click(downloadButton!);

      // Check the anchor was configured with correct download filename
      expect(mockAnchor.download).toBe("main.py");

      vi.restoreAllMocks();
    });

    it("should allow download from preview modal", () => {
      renderArtifactsPage();

      // Open preview first (no mock needed for this)
      fireEvent.click(screen.getByTestId("file-card-art-1"));

      // Mock anchor element creation AFTER render but BEFORE download click
      const mockClick = vi.fn();
      const mockAnchor = { href: "", download: "", click: mockClick };
      const realCreateElement = document.createElement.bind(document);
      vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
        if (tag === "a") return mockAnchor as unknown as HTMLAnchorElement;
        return realCreateElement(tag);
      });
      vi.spyOn(document.body, "appendChild").mockImplementation((node) => node);
      vi.spyOn(document.body, "removeChild").mockImplementation((node) => node);

      // Click download in preview modal (find button by text content inside modal)
      const modal = screen.getByTestId("preview-modal");
      const downloadButton = within(modal).getByRole("button", {
        name: /download/i,
      });
      fireEvent.click(downloadButton);

      expect(mockCreateObjectURL).toHaveBeenCalled();
      expect(mockClick).toHaveBeenCalled();

      vi.restoreAllMocks();
    });
  });

  // ===========================================================================
  // Delete Tests
  // ===========================================================================
  describe("Delete", () => {
    let mockFetch: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      mockFetch = vi.fn().mockResolvedValue({ ok: true });
      global.fetch = mockFetch;
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    it("should show delete confirmation modal when clicking delete button", () => {
      renderArtifactsPage();

      const fileCard = screen.getByTestId("file-card-art-1");
      const deleteButton = fileCard.querySelector(
        'button[aria-label="Delete"]',
      );
      fireEvent.click(deleteButton!);

      expect(screen.getByTestId("delete-confirm-modal")).toBeInTheDocument();
      expect(screen.getByText("Delete File")).toBeInTheDocument();
    });

    it("should show file name in delete confirmation", () => {
      renderArtifactsPage();

      const fileCard = screen.getByTestId("file-card-art-1");
      const deleteButton = fileCard.querySelector(
        'button[aria-label="Delete"]',
      );
      fireEvent.click(deleteButton!);

      // The file name appears in the confirmation message
      const modal = screen.getByTestId("delete-confirm-modal");
      expect(modal).toHaveTextContent("main.py");
    });

    it("should close confirmation modal when clicking Cancel", () => {
      renderArtifactsPage();

      const fileCard = screen.getByTestId("file-card-art-1");
      const deleteButton = fileCard.querySelector(
        'button[aria-label="Delete"]',
      );
      fireEvent.click(deleteButton!);

      expect(screen.getByTestId("delete-confirm-modal")).toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

      expect(
        screen.queryByTestId("delete-confirm-modal"),
      ).not.toBeInTheDocument();
    });

    it("should close confirmation modal when clicking backdrop", () => {
      renderArtifactsPage();

      const fileCard = screen.getByTestId("file-card-art-1");
      const deleteButton = fileCard.querySelector(
        'button[aria-label="Delete"]',
      );
      fireEvent.click(deleteButton!);

      fireEvent.click(screen.getByTestId("delete-confirm-modal"));

      expect(
        screen.queryByTestId("delete-confirm-modal"),
      ).not.toBeInTheDocument();
    });

    it("should call DELETE API when confirming delete", async () => {
      renderArtifactsPage();

      const fileCard = screen.getByTestId("file-card-art-1");
      const deleteButton = fileCard.querySelector(
        'button[aria-label="Delete"]',
      );
      fireEvent.click(deleteButton!);

      // Find the confirm delete button in the modal by text
      const modal = screen.getByTestId("delete-confirm-modal");
      const confirmButton = within(modal).getByRole("button", {
        name: "Delete",
      });
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          "/api/v1/artifacts/art-1",
          expect.objectContaining({
            method: "DELETE",
            credentials: "include",
          }),
        );
      });
    });

    it("should include auth token in delete request", async () => {
      renderArtifactsPage();

      const fileCard = screen.getByTestId("file-card-art-1");
      const deleteButton = fileCard.querySelector(
        'button[aria-label="Delete"]',
      );
      fireEvent.click(deleteButton!);

      const modal = screen.getByTestId("delete-confirm-modal");
      const confirmButton = modal.querySelector("button.bg-error-9");
      fireEvent.click(confirmButton!);

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
        // authenticatedFetch passes a Headers object, check via get()
        const callArgs = mockFetch.mock.calls[0] as [string, RequestInit];
        expect(callArgs[0]).toBe("/api/v1/artifacts/art-1");
        const headers = callArgs[1]?.headers as Headers;
        expect(headers.get("Authorization")).toBe("Bearer test-token");
      });
    });

    it("should call revalidator after successful delete", async () => {
      renderArtifactsPage();

      const fileCard = screen.getByTestId("file-card-art-1");
      const deleteButton = fileCard.querySelector(
        'button[aria-label="Delete"]',
      );
      fireEvent.click(deleteButton!);

      const modal = screen.getByTestId("delete-confirm-modal");
      const confirmButton = modal.querySelector("button.bg-error-9");
      fireEvent.click(confirmButton!);

      await waitFor(() => {
        expect(mockRevalidate).toHaveBeenCalled();
      });
    });

    it("should show loading state while deleting", async () => {
      // Make fetch slow
      mockFetch.mockImplementation(
        () =>
          new Promise((resolve) =>
            setTimeout(() => resolve({ ok: true }), 100),
          ),
      );

      renderArtifactsPage();

      const fileCard = screen.getByTestId("file-card-art-1");
      const deleteButton = fileCard.querySelector(
        'button[aria-label="Delete"]',
      );
      fireEvent.click(deleteButton!);

      const modal = screen.getByTestId("delete-confirm-modal");
      const confirmButton = modal.querySelector("button.bg-error-9");
      fireEvent.click(confirmButton!);

      expect(screen.getByText("Deleting...")).toBeInTheDocument();
    });

    it("should close confirmation modal after successful delete", async () => {
      renderArtifactsPage();

      const fileCard = screen.getByTestId("file-card-art-1");
      const deleteButton = fileCard.querySelector(
        'button[aria-label="Delete"]',
      );
      fireEvent.click(deleteButton!);

      const modal = screen.getByTestId("delete-confirm-modal");
      const confirmButton = modal.querySelector("button.bg-error-9");
      fireEvent.click(confirmButton!);

      await waitFor(() => {
        expect(
          screen.queryByTestId("delete-confirm-modal"),
        ).not.toBeInTheDocument();
      });
    });

    it("should close confirmation modal even after failed delete", async () => {
      mockFetch.mockResolvedValue({ ok: false, status: 500 });

      renderArtifactsPage();

      const fileCard = screen.getByTestId("file-card-art-1");
      const deleteButton = fileCard.querySelector(
        'button[aria-label="Delete"]',
      );
      fireEvent.click(deleteButton!);

      const modal = screen.getByTestId("delete-confirm-modal");
      const confirmButton = modal.querySelector("button.bg-error-9");
      fireEvent.click(confirmButton!);

      await waitFor(() => {
        expect(
          screen.queryByTestId("delete-confirm-modal"),
        ).not.toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // List View Tests
  // ===========================================================================
  describe("List View", () => {
    beforeEach(() => {
      renderArtifactsPage();
      fireEvent.click(screen.getByTestId("view-list"));
    });

    it("should show preview button in list view", () => {
      const fileRow = screen.getByTestId("file-row-art-1");
      expect(
        fileRow.querySelector('button[aria-label="Preview"]'),
      ).toBeInTheDocument();
    });

    it("should show download button in list view", () => {
      const fileRow = screen.getByTestId("file-row-art-1");
      expect(
        fileRow.querySelector('button[aria-label="Download"]'),
      ).toBeInTheDocument();
    });

    it("should show delete button in list view", () => {
      const fileRow = screen.getByTestId("file-row-art-1");
      expect(
        fileRow.querySelector('button[aria-label="Delete"]'),
      ).toBeInTheDocument();
    });

    it("should open preview when clicking Preview button in list view", () => {
      const fileRow = screen.getByTestId("file-row-art-1");
      const previewButton = fileRow.querySelector(
        'button[aria-label="Preview"]',
      );
      fireEvent.click(previewButton!);

      expect(screen.getByTestId("preview-modal")).toBeInTheDocument();
    });
  });
});
