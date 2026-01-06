/**
 * VectorsPage Tests
 *
 * TDD tests for the Vectors management page using RTK Query.
 * Tests cover:
 * - Page header display
 * - Collections list
 * - Create collection
 * - Delete collection
 * - Search vectors
 * - Upsert vectors
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
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { VectorsPage } from "./VectorsPage";

// Mock data - camelCase per ADR-0091 Phase 6 (RTK Query transforms)
const mockCollections = [
  { name: "documents", vectorsCount: 100 },
  { name: "images", vectorsCount: 50 },
];

const mockSearchResults = [
  { id: "1", score: 0.95, payload: { text: "Document about AI" } },
  { id: "2", score: 0.87, payload: { text: "Machine learning guide" } },
  { id: "3", score: 0.82, payload: { text: "Neural networks tutorial" } },
];

const mockRefetch = vi.fn();

// Mock RTK Query hooks
import * as apiModule from "../api";

vi.mock("../api", () => ({
  useListVectorCollectionsQuery: vi.fn(() => ({
    data: [],
    isLoading: false,
    isFetching: false,
    error: null,
    refetch: vi.fn(),
  })),
  useCreateVectorCollectionMutation: vi.fn(() => [
    vi.fn().mockReturnValue({ unwrap: () => Promise.resolve({}) }),
    { isLoading: false },
  ]),
  useDeleteVectorCollectionMutation: vi.fn(() => [
    vi.fn().mockReturnValue({ unwrap: () => Promise.resolve({}) }),
  ]),
  useSearchVectorsTextMutation: vi.fn(() => [
    vi.fn().mockReturnValue({ unwrap: () => Promise.resolve([]) }),
    { isLoading: false },
  ]),
  useUpsertVectorTextMutation: vi.fn(() => [
    vi.fn().mockReturnValue({ unwrap: () => Promise.resolve({}) }),
    { isLoading: false },
  ]),
}));

const mockedUseListVectorCollectionsQuery = vi.mocked(
  apiModule.useListVectorCollectionsQuery,
);
const mockedUseCreateVectorCollectionMutation = vi.mocked(
  apiModule.useCreateVectorCollectionMutation,
);
const mockedUseDeleteVectorCollectionMutation = vi.mocked(
  apiModule.useDeleteVectorCollectionMutation,
);
const mockedUseSearchVectorsTextMutation = vi.mocked(
  apiModule.useSearchVectorsTextMutation,
);
const mockedUseUpsertVectorTextMutation = vi.mocked(
  apiModule.useUpsertVectorTextMutation,
);

// Create a minimal store for testing
const createTestStore = () =>
  configureStore({
    reducer: {
      test: (state = {}) => state,
    },
  });

const renderWithProviders = (component: React.ReactElement) => {
  const store = createTestStore();
  return render(<Provider store={store}>{component}</Provider>);
};

describe("VectorsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(globalThis, "confirm").mockReturnValue(true);

    // Default mock implementations
    mockedUseListVectorCollectionsQuery.mockReturnValue({
      data: [],
      isLoading: false,
      isFetching: false,
      error: null,
      refetch: mockRefetch,
    } as ReturnType<typeof apiModule.useListVectorCollectionsQuery>);

    mockedUseCreateVectorCollectionMutation.mockReturnValue([
      vi.fn().mockReturnValue({ unwrap: () => Promise.resolve({}) }),
      { isLoading: false },
    ] as unknown as ReturnType<
      typeof apiModule.useCreateVectorCollectionMutation
    >);

    mockedUseDeleteVectorCollectionMutation.mockReturnValue([
      vi.fn().mockReturnValue({ unwrap: () => Promise.resolve({}) }),
    ] as unknown as ReturnType<
      typeof apiModule.useDeleteVectorCollectionMutation
    >);

    mockedUseSearchVectorsTextMutation.mockReturnValue([
      vi.fn().mockReturnValue({ unwrap: () => Promise.resolve([]) }),
      { isLoading: false },
    ] as unknown as ReturnType<typeof apiModule.useSearchVectorsTextMutation>);

    mockedUseUpsertVectorTextMutation.mockReturnValue([
      vi.fn().mockReturnValue({ unwrap: () => Promise.resolve({}) }),
      { isLoading: false },
    ] as unknown as ReturnType<typeof apiModule.useUpsertVectorTextMutation>);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("Header", () => {
    it("should display page title", () => {
      renderWithProviders(<VectorsPage />);
      expect(screen.getByText("Vector Collections")).toBeInTheDocument();
    });

    it("should display page description", () => {
      renderWithProviders(<VectorsPage />);
      expect(
        screen.getByText(/Manage Qdrant vector collections/),
      ).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("should show loading spinner while fetching data", () => {
      mockedUseListVectorCollectionsQuery.mockReturnValue({
        data: undefined,
        isLoading: true,
        isFetching: true,
        error: null,
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useListVectorCollectionsQuery>);

      renderWithProviders(<VectorsPage />);
      expect(document.querySelector(".animate-spin")).toBeInTheDocument();
    });
  });

  describe("Error State", () => {
    it("should display error message when fetch fails", () => {
      mockedUseListVectorCollectionsQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        error: { message: "Failed to load" },
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useListVectorCollectionsQuery>);

      renderWithProviders(<VectorsPage />);
      // ErrorState component has role="alert" for accessibility
      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(
        screen.getByRole("heading", { name: /failed to load collections/i }),
      ).toBeInTheDocument();
    });

    it("should show retry button on error", () => {
      mockedUseListVectorCollectionsQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        error: { message: "Failed to load" },
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useListVectorCollectionsQuery>);

      renderWithProviders(<VectorsPage />);
      // Retry button inside ErrorState
      expect(
        screen.getByRole("button", { name: /retry/i }),
      ).toBeInTheDocument();
    });

    it("should call refetch when retry button clicked", async () => {
      mockedUseListVectorCollectionsQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        error: { message: "Failed to load" },
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useListVectorCollectionsQuery>);

      renderWithProviders(<VectorsPage />);
      fireEvent.click(screen.getByText("Retry"));

      await waitFor(() => {
        expect(mockRefetch).toHaveBeenCalled();
      });
    });
  });

  describe("Collections List", () => {
    it("should display collections", () => {
      mockedUseListVectorCollectionsQuery.mockReturnValue({
        data: mockCollections,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useListVectorCollectionsQuery>);

      renderWithProviders(<VectorsPage />);

      expect(screen.getByText("documents")).toBeInTheDocument();
      expect(screen.getByText("images")).toBeInTheDocument();
    });

    it("should display collection count", () => {
      mockedUseListVectorCollectionsQuery.mockReturnValue({
        data: mockCollections,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useListVectorCollectionsQuery>);

      renderWithProviders(<VectorsPage />);
      expect(screen.getByText(/2 collections/i)).toBeInTheDocument();
    });

    it("should show empty state when no collections", () => {
      mockedUseListVectorCollectionsQuery.mockReturnValue({
        data: [],
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useListVectorCollectionsQuery>);

      renderWithProviders(<VectorsPage />);
      expect(screen.getByText(/No collections/)).toBeInTheDocument();
    });

    it("should display collection details", () => {
      mockedUseListVectorCollectionsQuery.mockReturnValue({
        data: [{ name: "documents", vectorsCount: 100 }],
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useListVectorCollectionsQuery>);

      renderWithProviders(<VectorsPage />);

      expect(screen.getByText("documents")).toBeInTheDocument();
      expect(screen.getByText(/100 points/)).toBeInTheDocument();
    });
  });

  describe("Create Collection", () => {
    it("should have create button", () => {
      renderWithProviders(<VectorsPage />);
      expect(screen.getByText(/Create Collection/)).toBeInTheDocument();
    });

    it("should show create modal when button clicked", async () => {
      renderWithProviders(<VectorsPage />);

      fireEvent.click(screen.getByText(/Create Collection/));

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText(/Collection name/),
        ).toBeInTheDocument();
      });
    });

    it("should have form fields in create modal", async () => {
      renderWithProviders(<VectorsPage />);

      fireEvent.click(screen.getByText(/Create Collection/));

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText(/Collection name/),
        ).toBeInTheDocument();
        expect(screen.getByLabelText(/Vector Size/)).toBeInTheDocument();
        expect(screen.getByLabelText(/Distance Metric/)).toBeInTheDocument();
      });
    });

    it("should create collection when form submitted", async () => {
      const mockCreateFn = vi.fn().mockReturnValue({
        unwrap: () => Promise.resolve({ success: true }),
      });

      mockedUseCreateVectorCollectionMutation.mockReturnValue([
        mockCreateFn,
        { isLoading: false },
      ] as unknown as ReturnType<
        typeof apiModule.useCreateVectorCollectionMutation
      >);

      renderWithProviders(<VectorsPage />);

      fireEvent.click(screen.getByText(/Create Collection/));

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText(/Collection name/),
        ).toBeInTheDocument();
      });

      const nameInput = screen.getByPlaceholderText(/Collection name/);
      const vectorSizeInput = screen.getByLabelText(/Vector Size/);
      const submitButton = screen.getByText("Create");

      fireEvent.change(nameInput, { target: { value: "test-collection" } });
      fireEvent.change(vectorSizeInput, { target: { value: "1536" } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockCreateFn).toHaveBeenCalledWith({
          name: "test-collection",
          vectors: {
            size: 1536,
            distance: "Cosine",
          },
        });
      });
    });
  });

  describe("Delete Collection", () => {
    it("should have delete button for each collection", () => {
      mockedUseListVectorCollectionsQuery.mockReturnValue({
        data: [{ name: "documents", vectorsCount: 100 }],
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useListVectorCollectionsQuery>);

      renderWithProviders(<VectorsPage />);
      expect(screen.getByLabelText(/Delete documents/)).toBeInTheDocument();
    });

    it("should show confirmation dialog before deleting", async () => {
      mockedUseListVectorCollectionsQuery.mockReturnValue({
        data: [{ name: "documents", vectorsCount: 100 }],
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useListVectorCollectionsQuery>);

      renderWithProviders(<VectorsPage />);

      const deleteButton = screen.getByLabelText(/Delete documents/);
      fireEvent.click(deleteButton);

      // Verify confirmation dialog opens
      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
        expect(screen.getByText(/Delete Collection/)).toBeInTheDocument();
      });
    });

    it("should delete collection when confirmed", async () => {
      const mockDeleteFn = vi.fn().mockReturnValue({
        unwrap: () => Promise.resolve({ success: true }),
      });

      mockedUseListVectorCollectionsQuery.mockReturnValue({
        data: [{ name: "documents", vectorsCount: 100 }],
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useListVectorCollectionsQuery>);

      mockedUseDeleteVectorCollectionMutation.mockReturnValue([
        mockDeleteFn,
      ] as unknown as ReturnType<
        typeof apiModule.useDeleteVectorCollectionMutation
      >);

      renderWithProviders(<VectorsPage />);

      // Click delete button to open confirmation dialog
      const deleteButton = screen.getByLabelText(/Delete documents/);
      fireEvent.click(deleteButton);

      // Wait for dialog to appear and click confirm
      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });

      // Click the "Delete" button in the confirmation dialog
      const confirmButton = screen.getByRole("button", { name: /^Delete$/ });
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(mockDeleteFn).toHaveBeenCalledWith("documents");
      });
    });
  });

  describe("Refresh Functionality", () => {
    it("should have refresh button", () => {
      renderWithProviders(<VectorsPage />);
      expect(screen.getByText(/Refresh/)).toBeInTheDocument();
    });

    it("should call refetch when refresh is clicked", async () => {
      mockedUseListVectorCollectionsQuery.mockReturnValue({
        data: [],
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useListVectorCollectionsQuery>);

      renderWithProviders(<VectorsPage />);

      const refreshButton = screen.getByText(/Refresh/);
      fireEvent.click(refreshButton);

      await waitFor(() => {
        expect(mockRefetch).toHaveBeenCalled();
      });
    });
  });

  // =========================================================================
  // Vector Search Tests
  // =========================================================================

  describe("Vector Search", () => {
    beforeEach(() => {
      mockedUseListVectorCollectionsQuery.mockReturnValue({
        data: mockCollections,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useListVectorCollectionsQuery>);
    });

    it("should have Search Vectors button", () => {
      renderWithProviders(<VectorsPage />);
      expect(screen.getByText(/Search Vectors/i)).toBeInTheDocument();
    });

    it("should open search panel when button clicked", async () => {
      renderWithProviders(<VectorsPage />);

      fireEvent.click(screen.getByText(/Search Vectors/i));

      await waitFor(() => {
        expect(screen.getByTestId("vector-search-panel")).toBeInTheDocument();
      });
    });

    it("should have collection dropdown in search panel", async () => {
      renderWithProviders(<VectorsPage />);

      fireEvent.click(screen.getByText(/Search Vectors/i));

      await waitFor(() => {
        expect(screen.getByLabelText(/Select Collection/i)).toBeInTheDocument();
      });
    });

    it("should have search query input", async () => {
      renderWithProviders(<VectorsPage />);

      fireEvent.click(screen.getByText(/Search Vectors/i));

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText(/Enter search query/i),
        ).toBeInTheDocument();
      });
    });

    it("should have limit input", async () => {
      renderWithProviders(<VectorsPage />);

      fireEvent.click(screen.getByText(/Search Vectors/i));

      await waitFor(() => {
        expect(screen.getByLabelText(/Limit/i)).toBeInTheDocument();
      });
    });

    it("should call search API when form submitted", async () => {
      const mockSearchFn = vi.fn().mockReturnValue({
        unwrap: () => Promise.resolve(mockSearchResults),
      });

      mockedUseSearchVectorsTextMutation.mockReturnValue([
        mockSearchFn,
        { isLoading: false },
      ] as unknown as ReturnType<
        typeof apiModule.useSearchVectorsTextMutation
      >);

      renderWithProviders(<VectorsPage />);

      fireEvent.click(screen.getByText(/Search Vectors/i));

      await waitFor(() => {
        expect(screen.getByTestId("vector-search-panel")).toBeInTheDocument();
      });

      // Fill out form
      const collectionSelect = screen.getByLabelText(/Select Collection/i);
      fireEvent.change(collectionSelect, { target: { value: "documents" } });

      const queryInput = screen.getByPlaceholderText(/Enter search query/i);
      fireEvent.change(queryInput, {
        target: { value: "AI and machine learning" },
      });

      // Submit
      fireEvent.click(screen.getByText("Search"));

      await waitFor(() => {
        expect(mockSearchFn).toHaveBeenCalledWith({
          collection_name: "documents",
          query_text: "AI and machine learning",
          limit: 10,
        });
      });
    });

    it("should display search results", async () => {
      const mockSearchFn = vi.fn().mockReturnValue({
        unwrap: () => Promise.resolve(mockSearchResults),
      });

      mockedUseSearchVectorsTextMutation.mockReturnValue([
        mockSearchFn,
        { isLoading: false },
      ] as unknown as ReturnType<
        typeof apiModule.useSearchVectorsTextMutation
      >);

      renderWithProviders(<VectorsPage />);

      fireEvent.click(screen.getByText(/Search Vectors/i));

      await waitFor(() => {
        expect(screen.getByTestId("vector-search-panel")).toBeInTheDocument();
      });

      // Fill and submit
      fireEvent.change(screen.getByLabelText(/Select Collection/i), {
        target: { value: "documents" },
      });
      fireEvent.change(screen.getByPlaceholderText(/Enter search query/i), {
        target: { value: "test" },
      });
      fireEvent.click(screen.getByText("Search"));

      await waitFor(() => {
        expect(screen.getByText(/Document about AI/i)).toBeInTheDocument();
        expect(screen.getByText(/Machine learning guide/i)).toBeInTheDocument();
        expect(
          screen.getByText(/Neural networks tutorial/i),
        ).toBeInTheDocument();
      });
    });

    it("should display similarity scores", async () => {
      const mockSearchFn = vi.fn().mockReturnValue({
        unwrap: () => Promise.resolve(mockSearchResults),
      });

      mockedUseSearchVectorsTextMutation.mockReturnValue([
        mockSearchFn,
        { isLoading: false },
      ] as unknown as ReturnType<
        typeof apiModule.useSearchVectorsTextMutation
      >);

      renderWithProviders(<VectorsPage />);

      fireEvent.click(screen.getByText(/Search Vectors/i));

      await waitFor(() => {
        expect(screen.getByTestId("vector-search-panel")).toBeInTheDocument();
      });

      // Fill and submit
      fireEvent.change(screen.getByLabelText(/Select Collection/i), {
        target: { value: "documents" },
      });
      fireEvent.change(screen.getByPlaceholderText(/Enter search query/i), {
        target: { value: "test" },
      });
      fireEvent.click(screen.getByText("Search"));

      await waitFor(() => {
        expect(screen.getByText(/0\.95/)).toBeInTheDocument();
        expect(screen.getByText(/0\.87/)).toBeInTheDocument();
      });
    });

    it("should show empty state when no results", async () => {
      const mockSearchFn = vi.fn().mockReturnValue({
        unwrap: () => Promise.resolve([]),
      });

      mockedUseSearchVectorsTextMutation.mockReturnValue([
        mockSearchFn,
        { isLoading: false },
      ] as unknown as ReturnType<
        typeof apiModule.useSearchVectorsTextMutation
      >);

      renderWithProviders(<VectorsPage />);

      fireEvent.click(screen.getByText(/Search Vectors/i));

      await waitFor(() => {
        expect(screen.getByTestId("vector-search-panel")).toBeInTheDocument();
      });

      // Fill and submit
      fireEvent.change(screen.getByLabelText(/Select Collection/i), {
        target: { value: "documents" },
      });
      fireEvent.change(screen.getByPlaceholderText(/Enter search query/i), {
        target: { value: "xyz" },
      });
      fireEvent.click(screen.getByText("Search"));

      await waitFor(() => {
        expect(screen.getByText(/No results found/i)).toBeInTheDocument();
      });
    });

    it("should close search panel when close button clicked", async () => {
      renderWithProviders(<VectorsPage />);

      fireEvent.click(screen.getByText(/Search Vectors/i));

      await waitFor(() => {
        expect(screen.getByTestId("vector-search-panel")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByLabelText(/Close search/i));

      await waitFor(() => {
        expect(
          screen.queryByTestId("vector-search-panel"),
        ).not.toBeInTheDocument();
      });
    });
  });

  // =========================================================================
  // Vector Upsert Tests
  // =========================================================================

  describe("Vector Upsert", () => {
    beforeEach(() => {
      mockedUseListVectorCollectionsQuery.mockReturnValue({
        data: mockCollections,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useListVectorCollectionsQuery>);
    });

    it("should have Upsert Points button", () => {
      renderWithProviders(<VectorsPage />);
      expect(screen.getByText(/Upsert Points/i)).toBeInTheDocument();
    });

    it("should open upsert panel when button clicked", async () => {
      renderWithProviders(<VectorsPage />);

      fireEvent.click(screen.getByText(/Upsert Points/i));

      await waitFor(() => {
        expect(screen.getByTestId("vector-upsert-panel")).toBeInTheDocument();
      });
    });

    it("should have collection dropdown in upsert panel", async () => {
      renderWithProviders(<VectorsPage />);

      fireEvent.click(screen.getByText(/Upsert Points/i));

      await waitFor(() => {
        expect(screen.getByLabelText(/Select Collection/i)).toBeInTheDocument();
      });
    });

    it("should have text content input", async () => {
      renderWithProviders(<VectorsPage />);

      fireEvent.click(screen.getByText(/Upsert Points/i));

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText(/Enter text content/i),
        ).toBeInTheDocument();
      });
    });

    it("should have optional metadata input", async () => {
      renderWithProviders(<VectorsPage />);

      fireEvent.click(screen.getByText(/Upsert Points/i));

      await waitFor(() => {
        expect(screen.getByLabelText(/Metadata/i)).toBeInTheDocument();
      });
    });

    it("should call upsert API when form submitted", async () => {
      const mockUpsertFn = vi.fn().mockReturnValue({
        unwrap: () => Promise.resolve({ success: true, pointId: "point-123" }),
      });

      mockedUseUpsertVectorTextMutation.mockReturnValue([
        mockUpsertFn,
        { isLoading: false },
      ] as unknown as ReturnType<typeof apiModule.useUpsertVectorTextMutation>);

      renderWithProviders(<VectorsPage />);

      fireEvent.click(screen.getByText(/Upsert Points/i));

      await waitFor(() => {
        expect(screen.getByTestId("vector-upsert-panel")).toBeInTheDocument();
      });

      // Fill out form
      const collectionSelect = screen.getByLabelText(/Select Collection/i);
      fireEvent.change(collectionSelect, { target: { value: "documents" } });

      const textInput = screen.getByPlaceholderText(/Enter text content/i);
      fireEvent.change(textInput, {
        target: { value: "This is a test document about AI." },
      });

      // Submit
      fireEvent.click(screen.getByText("Upsert"));

      await waitFor(() => {
        expect(mockUpsertFn).toHaveBeenCalledWith({
          collection_name: "documents",
          text: "This is a test document about AI.",
          metadata: {},
        });
      });
    });

    it("should show success message after upsert", async () => {
      const mockUpsertFn = vi.fn().mockReturnValue({
        unwrap: () => Promise.resolve({ success: true, pointId: "point-123" }),
      });

      mockedUseUpsertVectorTextMutation.mockReturnValue([
        mockUpsertFn,
        { isLoading: false },
      ] as unknown as ReturnType<typeof apiModule.useUpsertVectorTextMutation>);

      renderWithProviders(<VectorsPage />);

      fireEvent.click(screen.getByText(/Upsert Points/i));

      await waitFor(() => {
        expect(screen.getByTestId("vector-upsert-panel")).toBeInTheDocument();
      });

      // Fill and submit
      fireEvent.change(screen.getByLabelText(/Select Collection/i), {
        target: { value: "documents" },
      });
      fireEvent.change(screen.getByPlaceholderText(/Enter text content/i), {
        target: { value: "Test content" },
      });
      fireEvent.click(screen.getByText("Upsert"));

      await waitFor(() => {
        expect(
          screen.getByText(/Point upserted successfully/i),
        ).toBeInTheDocument();
      });
    });

    it("should show error message when upsert fails", async () => {
      const mockUpsertFn = vi.fn().mockReturnValue({
        unwrap: () => Promise.reject(new Error("Internal Server Error")),
      });

      mockedUseUpsertVectorTextMutation.mockReturnValue([
        mockUpsertFn,
        { isLoading: false },
      ] as unknown as ReturnType<typeof apiModule.useUpsertVectorTextMutation>);

      renderWithProviders(<VectorsPage />);

      fireEvent.click(screen.getByText(/Upsert Points/i));

      await waitFor(() => {
        expect(screen.getByTestId("vector-upsert-panel")).toBeInTheDocument();
      });

      // Fill and submit
      fireEvent.change(screen.getByLabelText(/Select Collection/i), {
        target: { value: "documents" },
      });
      fireEvent.change(screen.getByPlaceholderText(/Enter text content/i), {
        target: { value: "Test content" },
      });
      fireEvent.click(screen.getByText("Upsert"));

      await waitFor(() => {
        expect(screen.getByText(/Failed to upsert/i)).toBeInTheDocument();
      });
    });

    it("should close upsert panel when close button clicked", async () => {
      renderWithProviders(<VectorsPage />);

      fireEvent.click(screen.getByText(/Upsert Points/i));

      await waitFor(() => {
        expect(screen.getByTestId("vector-upsert-panel")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByLabelText(/Close upsert/i));

      await waitFor(() => {
        expect(
          screen.queryByTestId("vector-upsert-panel"),
        ).not.toBeInTheDocument();
      });
    });

    it("should clear form after successful upsert", async () => {
      const mockUpsertFn = vi.fn().mockReturnValue({
        unwrap: () => Promise.resolve({ success: true, pointId: "point-123" }),
      });

      mockedUseUpsertVectorTextMutation.mockReturnValue([
        mockUpsertFn,
        { isLoading: false },
      ] as unknown as ReturnType<typeof apiModule.useUpsertVectorTextMutation>);

      renderWithProviders(<VectorsPage />);

      fireEvent.click(screen.getByText(/Upsert Points/i));

      await waitFor(() => {
        expect(screen.getByTestId("vector-upsert-panel")).toBeInTheDocument();
      });

      // Fill and submit
      fireEvent.change(screen.getByLabelText(/Select Collection/i), {
        target: { value: "documents" },
      });
      fireEvent.change(screen.getByPlaceholderText(/Enter text content/i), {
        target: { value: "Test content" },
      });
      fireEvent.click(screen.getByText("Upsert"));

      await waitFor(() => {
        expect(
          screen.getByText(/Point upserted successfully/i),
        ).toBeInTheDocument();
      });

      // Text input should be cleared (get fresh reference after state update)
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Enter text content/i)).toHaveValue(
          "",
        );
      });
    });
  });
});
