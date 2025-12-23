/**
 * ProjectDocument Component Tests
 *
 * TDD tests for the project document component used in MainDock tabs.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router";
import { configureStore } from "@reduxjs/toolkit";
import { ProjectDocument } from "./ProjectDocument";
import projectReducer from "../../store/slices/projectSlice";
import uiReducer from "../../store/slices/uiSlice";

// Mock RTK Query hooks
vi.mock("../../api", () => ({
  useGetProjectQuery: (id: string | undefined) => {
    if (!id) {
      return {
        data: undefined,
        isLoading: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      };
    }
    return {
      data: {
        id,
        name: `Test Project ${id}`,
        description: "A test project",
        status: "active",
        owner_id: "user-123",
        owner_name: "Test User",
        session_count: 5,
        workflow_count: 3,
        connection_count: 2,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      isLoading: false,
      isError: false,
      error: undefined,
      refetch: vi.fn(),
    };
  },
}));

// Create test store
const createTestStore = () => {
  return configureStore({
    reducer: {
      project: projectReducer,
      ui: uiReducer,
    },
  });
};

const renderWithProviders = (ui: React.ReactElement) => {
  const store = createTestStore();
  return {
    store,
    ...render(
      <Provider store={store}>
        <MemoryRouter>{ui}</MemoryRouter>
      </Provider>,
    ),
  };
};

describe("ProjectDocument", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render with data-testid", () => {
      renderWithProviders(<ProjectDocument projectId="proj-123" />);
      expect(screen.getByTestId("project-document")).toBeInTheDocument();
    });

    it("should display project name when loaded", () => {
      renderWithProviders(<ProjectDocument projectId="proj-123" />);
      expect(screen.getByText(/Test Project proj-123/i)).toBeInTheDocument();
    });

    it("should show empty state when no projectId provided", () => {
      renderWithProviders(<ProjectDocument projectId="" />);
      expect(screen.getByText(/No project selected/i)).toBeInTheDocument();
    });

    it("should apply compact mode styling when compact prop is true", () => {
      renderWithProviders(<ProjectDocument projectId="proj-123" compact />);
      const doc = screen.getByTestId("project-document");
      expect(doc).toHaveClass("text-sm");
    });
  });

  describe("Props", () => {
    it("should accept projectId prop", () => {
      renderWithProviders(<ProjectDocument projectId="proj-456" />);
      expect(screen.getByText(/Test Project proj-456/i)).toBeInTheDocument();
    });

    it("should accept className prop", () => {
      renderWithProviders(
        <ProjectDocument projectId="proj-123" className="custom-class" />,
      );
      const doc = screen.getByTestId("project-document");
      expect(doc).toHaveClass("custom-class");
    });
  });
});
