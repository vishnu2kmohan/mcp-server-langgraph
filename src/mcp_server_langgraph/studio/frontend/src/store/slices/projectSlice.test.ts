/**
 * Project Slice Tests
 *
 * TDD tests for project Redux slice.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import projectReducer, {
  initialProjectState,
  fetchProjects,
  loadProject,
  createProject,
  deleteProject,
  updateProject,
  setCurrentProject,
  clearCurrentProject,
  clearError,
  resetProject,
  selectProjects,
  selectCurrentProject,
  selectIsLoadingProjects,
  selectProjectError,
  selectProjectById,
} from "./projectSlice";
import type { Project, ProjectDetail, ProjectState } from "./projectSlice";

// Helper to create a test store
const createTestStore = (preloadedState?: Partial<ProjectState>) => {
  return configureStore({
    reducer: { project: projectReducer },
    preloadedState: preloadedState
      ? { project: { ...initialProjectState, ...preloadedState } }
      : undefined,
  });
};

// Mock project data
const mockProject: Project = {
  id: "proj-1",
  name: "Test Project",
  description: "A test project",
  owner_id: "user-1",
  organization_id: null,
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-01T00:00:00Z",
  workflow_count: 2,
  session_count: 5,
  connection_count: 1,
  status: "active",
};

const mockProjectDetail: ProjectDetail = {
  ...mockProject,
  workflows: [],
  sessions: [],
  connections: [],
  members: [],
};

describe("projectSlice", () => {
  const mockFetch = vi.fn();

  beforeEach(() => {
    mockFetch.mockReset();
    vi.stubGlobal("fetch", mockFetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe("Initial State", () => {
    it("should have null currentProject initially", () => {
      const store = createTestStore();
      expect(selectCurrentProject(store.getState())).toBeNull();
    });

    it("should have empty projects array initially", () => {
      const store = createTestStore();
      expect(selectProjects(store.getState())).toEqual([]);
    });

    it("should have isLoading as false initially", () => {
      const store = createTestStore();
      expect(selectIsLoadingProjects(store.getState())).toBe(false);
    });

    it("should have error as null initially", () => {
      const store = createTestStore();
      expect(selectProjectError(store.getState())).toBeNull();
    });
  });

  describe("Synchronous Actions", () => {
    describe("setCurrentProject", () => {
      it("should set the current project", () => {
        const store = createTestStore();
        store.dispatch(setCurrentProject(mockProject));

        const state = store.getState();
        expect(selectCurrentProject(state)).toEqual(mockProject);
      });

      it("should clear current project when set to null", () => {
        const store = createTestStore({ currentProject: mockProject });
        expect(selectCurrentProject(store.getState())).toEqual(mockProject);

        store.dispatch(setCurrentProject(null));
        expect(selectCurrentProject(store.getState())).toBeNull();
      });
    });

    describe("clearCurrentProject", () => {
      it("should clear the current project", () => {
        const store = createTestStore({ currentProject: mockProject });
        expect(selectCurrentProject(store.getState())).toEqual(mockProject);

        store.dispatch(clearCurrentProject());
        expect(selectCurrentProject(store.getState())).toBeNull();
      });
    });

    describe("clearError", () => {
      it("should clear the error", () => {
        const store = createTestStore({ error: "Test error" });
        expect(selectProjectError(store.getState())).toBe("Test error");

        store.dispatch(clearError());
        expect(selectProjectError(store.getState())).toBeNull();
      });
    });

    describe("resetProject", () => {
      it("should reset to initial state", () => {
        const store = createTestStore({
          projects: [mockProject],
          currentProject: mockProject,
          error: "Test error",
          isLoading: true,
        });

        store.dispatch(resetProject());

        const state = store.getState();
        expect(selectProjects(state)).toEqual([]);
        expect(selectCurrentProject(state)).toBeNull();
        expect(selectProjectError(state)).toBeNull();
        expect(selectIsLoadingProjects(state)).toBe(false);
      });
    });
  });

  describe("Async Thunks", () => {
    describe("fetchProjects", () => {
      it("should fetch projects from API", async () => {
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: () =>
            Promise.resolve({
              // Backend returns 'items' per PagePaginatedResponse contract
              items: [mockProject],
              total: 1,
              page: 1,
              per_page: 20,
            }),
        });

        const store = createTestStore();
        await store.dispatch(fetchProjects());

        const state = store.getState();
        expect(mockFetch).toHaveBeenCalledWith(
          "/api/v1/projects?page=1&per_page=20",
          expect.any(Object),
        );
        expect(selectProjects(state)).toHaveLength(1);
        expect(selectProjects(state)[0].name).toBe("Test Project");
      });

      it("should set isLoading during fetch", async () => {
        mockFetch.mockImplementation(() => new Promise(() => {})); // Never resolves

        const store = createTestStore();
        store.dispatch(fetchProjects());

        // During fetch, isLoading should be true
        expect(selectIsLoadingProjects(store.getState())).toBe(true);
      });

      it("should set error on fetch failure", async () => {
        mockFetch.mockRejectedValueOnce(new Error("Network error"));

        const store = createTestStore();
        await store.dispatch(fetchProjects());

        expect(selectProjectError(store.getState())).toBe("Network error");
        expect(selectIsLoadingProjects(store.getState())).toBe(false);
      });

      it("should handle API error response", async () => {
        mockFetch.mockResolvedValueOnce({
          ok: false,
          status: 500,
        });

        const store = createTestStore();
        await store.dispatch(fetchProjects());

        expect(selectProjectError(store.getState())).toBe(
          "Failed to load projects",
        );
      });
    });

    describe("loadProject", () => {
      it("should load a specific project by ID", async () => {
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockProjectDetail),
        });

        const store = createTestStore();
        await store.dispatch(loadProject("proj-1"));

        expect(mockFetch).toHaveBeenCalledWith(
          "/api/v1/projects/proj-1",
          expect.any(Object),
        );
        expect(selectCurrentProject(store.getState())?.id).toBe("proj-1");
      });

      it("should set error if project not found", async () => {
        mockFetch.mockResolvedValueOnce({
          ok: false,
          status: 404,
        });

        const store = createTestStore();
        await store.dispatch(loadProject("nonexistent"));

        expect(selectProjectError(store.getState())).toBe(
          "Failed to load project",
        );
        expect(selectCurrentProject(store.getState())).toBeNull();
      });
    });

    describe("createProject", () => {
      it("should create a new project", async () => {
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockProject),
        });

        const store = createTestStore();
        await store.dispatch(
          createProject({
            name: "Test Project",
            description: "A test project",
          }),
        );

        expect(mockFetch).toHaveBeenCalledWith(
          "/api/v1/projects",
          expect.objectContaining({
            method: "POST",
            body: JSON.stringify({
              name: "Test Project",
              description: "A test project",
            }),
          }),
        );
        expect(selectProjects(store.getState())).toHaveLength(1);
      });

      it("should set error on creation failure", async () => {
        mockFetch.mockRejectedValueOnce(new Error("Failed to create"));

        const store = createTestStore();
        await store.dispatch(createProject({ name: "Test" }));

        expect(selectProjectError(store.getState())).toBe("Failed to create");
      });
    });

    describe("deleteProject", () => {
      it("should delete a project", async () => {
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({}),
        });

        const store = createTestStore({ projects: [mockProject], total: 1 });
        await store.dispatch(deleteProject("proj-1"));

        expect(mockFetch).toHaveBeenCalledWith(
          "/api/v1/projects/proj-1",
          expect.objectContaining({ method: "DELETE" }),
        );
        expect(selectProjects(store.getState())).toHaveLength(0);
      });

      it("should clear currentProject if deleted project was current", async () => {
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({}),
        });

        const store = createTestStore({
          projects: [mockProject],
          currentProject: mockProject,
          total: 1,
        });
        await store.dispatch(deleteProject("proj-1"));

        expect(selectCurrentProject(store.getState())).toBeNull();
      });

      it("should set error on delete failure", async () => {
        mockFetch.mockRejectedValueOnce(new Error("Delete failed"));

        const store = createTestStore({ projects: [mockProject], total: 1 });
        await store.dispatch(deleteProject("proj-1"));

        expect(selectProjectError(store.getState())).toBe("Delete failed");
        // Project should still exist
        expect(selectProjects(store.getState())).toHaveLength(1);
      });

      it("should handle API error response on delete", async () => {
        mockFetch.mockResolvedValueOnce({
          ok: false,
          status: 403,
          json: () => Promise.resolve({ detail: "Permission denied" }),
        });

        const store = createTestStore({ projects: [mockProject], total: 1 });
        await store.dispatch(deleteProject("proj-1"));

        // The slice uses a generic error message for failed API responses
        expect(selectProjectError(store.getState())).toBe(
          "Failed to delete project",
        );
        // Project should still exist after failed delete
        expect(selectProjects(store.getState())).toHaveLength(1);
      });
    });

    describe("updateProject", () => {
      it("should update a project", async () => {
        const updatedProject = { ...mockProject, name: "Updated Name" };
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(updatedProject),
        });

        const store = createTestStore({ projects: [mockProject] });
        await store.dispatch(
          updateProject({ projectId: "proj-1", name: "Updated Name" }),
        );

        const projects = selectProjects(store.getState());
        expect(projects[0].name).toBe("Updated Name");
      });

      it("should update currentProject if it matches", async () => {
        const updatedProject = { ...mockProject, name: "Updated Name" };
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(updatedProject),
        });

        const store = createTestStore({
          projects: [mockProject],
          currentProject: mockProject,
        });
        await store.dispatch(
          updateProject({ projectId: "proj-1", name: "Updated Name" }),
        );

        expect(selectCurrentProject(store.getState())?.name).toBe(
          "Updated Name",
        );
      });

      it("should set error on update failure", async () => {
        mockFetch.mockRejectedValueOnce(new Error("Update failed"));

        const store = createTestStore({ projects: [mockProject] });
        await store.dispatch(
          updateProject({ projectId: "proj-1", name: "Updated Name" }),
        );

        expect(selectProjectError(store.getState())).toBe("Update failed");
        // Project should retain original name
        expect(selectProjects(store.getState())[0].name).toBe("Test Project");
      });

      it("should handle API error response on update", async () => {
        mockFetch.mockResolvedValueOnce({
          ok: false,
          status: 400,
          json: () => Promise.resolve({ detail: "Invalid project name" }),
        });

        const store = createTestStore({ projects: [mockProject] });
        await store.dispatch(updateProject({ projectId: "proj-1", name: "" }));

        // The slice uses a generic error message for failed API responses
        expect(selectProjectError(store.getState())).toBe(
          "Failed to update project",
        );
        // Project should retain original name
        expect(selectProjects(store.getState())[0].name).toBe("Test Project");
      });
    });
  });

  describe("Selectors", () => {
    describe("selectProjectById", () => {
      it("should find project by ID", () => {
        const store = createTestStore({ projects: [mockProject] });
        const selector = selectProjectById("proj-1");
        expect(selector(store.getState())?.name).toBe("Test Project");
      });

      it("should return undefined if project not found", () => {
        const store = createTestStore({ projects: [mockProject] });
        const selector = selectProjectById("nonexistent");
        expect(selector(store.getState())).toBeUndefined();
      });
    });
  });
});
