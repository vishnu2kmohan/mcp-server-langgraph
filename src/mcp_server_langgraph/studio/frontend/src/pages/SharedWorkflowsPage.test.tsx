/**
 * SharedWorkflowsPage Tests (TDD)
 *
 * Tests for the read-only shared workflows page.
 * This page is accessible to all personas (admin, developer, user).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router";
import { configureStore } from "@reduxjs/toolkit";
import { SharedWorkflowsPage } from "./SharedWorkflowsPage";
import { api } from "../api";
import personaReducer from "../store/slices/personaSlice";
import authReducer from "../store/slices/authSlice";

// Default mock data
const mockWorkflows = [
  {
    id: "workflow-1",
    name: "RAG Chatbot",
    description: "A RAG-powered chatbot workflow",
    owner: "alice",
    sharedWith: ["bob"],
    createdAt: "2025-01-01T00:00:00Z",
  },
  {
    id: "workflow-2",
    name: "Data Pipeline",
    description: "ETL data pipeline workflow",
    owner: "charlie",
    sharedWith: ["bob", "dave"],
    createdAt: "2025-01-02T00:00:00Z",
  },
];

// Create a mock function that can be reset
const mockUseGetSharedWorkflowsQuery = vi.fn(() => ({
  data: mockWorkflows,
  isLoading: false,
  error: null,
  refetch: vi.fn(),
}));

// Mock the API query
vi.mock("../api", async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return {
    ...actual,
    useGetSharedWorkflowsQuery: () => mockUseGetSharedWorkflowsQuery(),
  };
});

function createTestStore() {
  return configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,
      persona: personaReducer,
      auth: authReducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });
}

function renderWithProviders(component: React.ReactNode) {
  const store = createTestStore();
  return render(
    <Provider store={store}>
      <MemoryRouter>{component}</MemoryRouter>
    </Provider>,
  );
}

describe("SharedWorkflowsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset mock to default implementation
    mockUseGetSharedWorkflowsQuery.mockReturnValue({
      data: mockWorkflows,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("should render the page title", () => {
    renderWithProviders(<SharedWorkflowsPage />);
    expect(
      screen.getByRole("heading", { name: /shared workflows/i }),
    ).toBeInTheDocument();
  });

  it("should display shared workflows list", () => {
    renderWithProviders(<SharedWorkflowsPage />);
    expect(screen.getByText("RAG Chatbot")).toBeInTheDocument();
    expect(screen.getByText("Data Pipeline")).toBeInTheDocument();
  });

  it("should show workflow descriptions", () => {
    renderWithProviders(<SharedWorkflowsPage />);
    expect(screen.getByText(/RAG-powered chatbot/i)).toBeInTheDocument();
    expect(screen.getByText(/ETL data pipeline/i)).toBeInTheDocument();
  });

  it("should show workflow owners", () => {
    renderWithProviders(<SharedWorkflowsPage />);
    expect(screen.getByText(/alice/i)).toBeInTheDocument();
    expect(screen.getByText(/charlie/i)).toBeInTheDocument();
  });

  it("should indicate read-only access for standard users", () => {
    renderWithProviders(<SharedWorkflowsPage />);
    // Should have read-only indicator or view-only buttons (one per shared workflow)
    const viewButtons = screen.getAllByText(/view/i);
    expect(viewButtons.length).toBeGreaterThan(0);
  });

  it("should display loading state", () => {
    // Override mock for loading state
    mockUseGetSharedWorkflowsQuery.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    });

    renderWithProviders(<SharedWorkflowsPage />);
    expect(screen.getByTestId("loading-indicator")).toBeInTheDocument();
  });

  it("should display empty state when no shared workflows", () => {
    // Override mock for empty state
    mockUseGetSharedWorkflowsQuery.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithProviders(<SharedWorkflowsPage />);
    expect(screen.getByText(/no shared workflows/i)).toBeInTheDocument();
  });

  describe("Search and Filter", () => {
    it("should render search input", () => {
      renderWithProviders(<SharedWorkflowsPage />);
      expect(
        screen.getByPlaceholderText(/search.*workflows/i),
      ).toBeInTheDocument();
    });

    it("should filter workflows by search query", async () => {
      renderWithProviders(<SharedWorkflowsPage />);

      // Both workflows should be visible initially
      expect(screen.getByText("RAG Chatbot")).toBeInTheDocument();
      expect(screen.getByText("Data Pipeline")).toBeInTheDocument();

      // Type in search
      const searchInput = screen.getByPlaceholderText(/search.*workflows/i);
      fireEvent.change(searchInput, { target: { value: "RAG" } });

      // Only RAG Chatbot should be visible
      expect(screen.getByText("RAG Chatbot")).toBeInTheDocument();
      expect(screen.queryByText("Data Pipeline")).not.toBeInTheDocument();
    });

    it("should filter workflows case-insensitively", async () => {
      renderWithProviders(<SharedWorkflowsPage />);

      const searchInput = screen.getByPlaceholderText(/search.*workflows/i);
      fireEvent.change(searchInput, { target: { value: "rag" } });

      // RAG Chatbot should still be found with lowercase search
      expect(screen.getByText("RAG Chatbot")).toBeInTheDocument();
    });

    it("should search in workflow description", async () => {
      renderWithProviders(<SharedWorkflowsPage />);

      const searchInput = screen.getByPlaceholderText(/search.*workflows/i);
      fireEvent.change(searchInput, { target: { value: "ETL" } });

      // Data Pipeline has "ETL" in its description
      expect(screen.getByText("Data Pipeline")).toBeInTheDocument();
      expect(screen.queryByText("RAG Chatbot")).not.toBeInTheDocument();
    });

    it("should show empty message when no workflows match search", async () => {
      renderWithProviders(<SharedWorkflowsPage />);

      const searchInput = screen.getByPlaceholderText(/search.*workflows/i);
      fireEvent.change(searchInput, { target: { value: "nonexistent" } });

      expect(screen.getByText(/no workflows match/i)).toBeInTheDocument();
    });

    it("should render sort dropdown", () => {
      renderWithProviders(<SharedWorkflowsPage />);
      expect(screen.getByLabelText(/sort by/i)).toBeInTheDocument();
    });

    it("should sort workflows by name", async () => {
      renderWithProviders(<SharedWorkflowsPage />);

      // Default order (by date): RAG Chatbot then Data Pipeline (as returned by mock)
      const cards = screen.getAllByRole("button", { name: /view/i });
      expect(cards).toHaveLength(2);

      // Change sort to name (ascending)
      const sortDropdown = screen.getByLabelText(/sort by/i);
      fireEvent.change(sortDropdown, { target: { value: "name" } });

      // After sorting by name: Data Pipeline, RAG Chatbot (alphabetical)
      const workflowCards = screen.getAllByText(/Chatbot|Pipeline/);
      expect(workflowCards[0]).toHaveTextContent("Data Pipeline");
      expect(workflowCards[1]).toHaveTextContent("RAG Chatbot");
    });
  });
});
