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
  selectCurrentProjectDetail,
  selectIsLoadingProjects,
  selectIsLoadingProjectDetail,
  selectProjectError,
  selectProjectById,
  selectProjectTotal,
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

      it("should use fallback error message when payload is undefined", () => {
        // Directly test reducer with undefined payload
        const state = projectReducer(
          { ...initialProjectState, isLoading: true },
          { type: fetchProjects.rejected.type, payload: undefined },
        );
        expect(state.error).toBe("Failed to load projects");
        expect(state.isLoading).toBe(false);
      });

      it("should use fallback error message when non-Error is thrown", async () => {
        // Simulate a non-Error exception (e.g., string thrown)
        mockFetch.mockRejectedValueOnce("Network failure");

        const store = createTestStore();
        await store.dispatch(fetchProjects());

        expect(selectProjectError(store.getState())).toBe(
          "Failed to load projects",
        );
      });

      it("should fallback to defaults when response fields are missing", async () => {
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: () =>
            Promise.resolve({
              // Response with missing fields
            }),
        });

        const store = createTestStore();
        await store.dispatch(fetchProjects());

        const state = store.getState();
        // Should use defaults when fields are missing
        expect(selectProjects(state)).toEqual([]); // items || []
        expect(selectProjectTotal(state)).toBe(0); // total || 0
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

      it("should use fallback error message when payload is undefined", () => {
        // Directly test reducer with undefined payload
        const state = projectReducer(
          { ...initialProjectState, isLoadingDetail: true, currentProject: mockProject },
          { type: loadProject.rejected.type, payload: undefined },
        );
        expect(state.error).toBe("Failed to load project");
        expect(state.isLoadingDetail).toBe(false);
        expect(state.currentProject).toBeNull();
        expect(state.currentProjectDetail).toBeNull();
      });

      it("should use fallback error message when non-Error is thrown", async () => {
        // Simulate a non-Error exception (e.g., string thrown)
        mockFetch.mockRejectedValueOnce("Network failure");

        const store = createTestStore();
        await store.dispatch(loadProject("proj-1"));

        expect(selectProjectError(store.getState())).toBe(
          "Failed to load project",
        );
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

      it("should handle API error response on creation", async () => {
        mockFetch.mockResolvedValueOnce({
          ok: false,
          status: 400,
          json: () => Promise.resolve({ detail: "Invalid project name" }),
        });

        const store = createTestStore();
        await store.dispatch(createProject({ name: "Test" }));

        expect(selectProjectError(store.getState())).toBe(
          "Failed to create project",
        );
        expect(selectProjects(store.getState())).toHaveLength(0);
      });

      it("should use fallback error message when payload is undefined", () => {
        // Directly test reducer with undefined payload
        const state = projectReducer(
          { ...initialProjectState, isLoading: true },
          { type: createProject.rejected.type, payload: undefined },
        );
        expect(state.error).toBe("Failed to create project");
        expect(state.isLoading).toBe(false);
      });

      it("should use fallback error message when non-Error is thrown", async () => {
        // Simulate a non-Error exception (e.g., string thrown)
        mockFetch.mockRejectedValueOnce("Network failure");

        const store = createTestStore();
        await store.dispatch(createProject({ name: "Test" }));

        expect(selectProjectError(store.getState())).toBe(
          "Failed to create project",
        );
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

      it("should not clear currentProject if deleted project is different", async () => {
        const otherProject: Project = {
          ...mockProject,
          id: "proj-2",
          name: "Other Project",
        };
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({}),
        });

        const store = createTestStore({
          projects: [mockProject, otherProject],
          currentProject: otherProject,
          total: 2,
        });
        await store.dispatch(deleteProject("proj-1"));

        // currentProject should remain unchanged since it's a different project
        expect(selectCurrentProject(store.getState())?.id).toBe("proj-2");
        expect(selectProjects(store.getState())).toHaveLength(1);
        expect(selectProjects(store.getState())[0].id).toBe("proj-2");
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

      it("should use fallback error message when payload is undefined", () => {
        // Directly test reducer with undefined payload
        const state = projectReducer(
          { ...initialProjectState, isLoading: true, projects: [mockProject], total: 1 },
          { type: deleteProject.rejected.type, payload: undefined },
        );
        expect(state.error).toBe("Failed to delete project");
        expect(state.isLoading).toBe(false);
        // Projects should remain unchanged
        expect(state.projects).toHaveLength(1);
      });

      it("should use fallback error message when non-Error is thrown", async () => {
        // Simulate a non-Error exception (e.g., string thrown)
        mockFetch.mockRejectedValueOnce("Network failure");

        const store = createTestStore({ projects: [mockProject], total: 1 });
        await store.dispatch(deleteProject("proj-1"));

        expect(selectProjectError(store.getState())).toBe(
          "Failed to delete project",
        );
        // Project should still exist
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

      it("should use fallback error message when payload is undefined", () => {
        // Directly test reducer with undefined payload
        const state = projectReducer(
          { ...initialProjectState, isLoading: true, projects: [mockProject] },
          { type: updateProject.rejected.type, payload: undefined },
        );
        expect(state.error).toBe("Failed to update project");
        expect(state.isLoading).toBe(false);
        // Projects should remain unchanged
        expect(state.projects[0].name).toBe("Test Project");
      });

      it("should use fallback error message when non-Error is thrown", async () => {
        // Simulate a non-Error exception (e.g., string thrown)
        mockFetch.mockRejectedValueOnce("Network failure");

        const store = createTestStore({ projects: [mockProject] });
        await store.dispatch(
          updateProject({ projectId: "proj-1", name: "Updated Name" }),
        );

        expect(selectProjectError(store.getState())).toBe(
          "Failed to update project",
        );
        // Project should retain original name
        expect(selectProjects(store.getState())[0].name).toBe("Test Project");
      });

      it("should not update projects array if project not found", async () => {
        const updatedProject = { ...mockProject, id: "nonexistent", name: "Updated Name" };
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(updatedProject),
        });

        const store = createTestStore({ projects: [mockProject] });
        await store.dispatch(
          updateProject({ projectId: "nonexistent", name: "Updated Name" }),
        );

        // Original project should be unchanged
        const projects = selectProjects(store.getState());
        expect(projects.length).toBe(1);
        expect(projects[0].name).toBe("Test Project");
      });

      it("should not update currentProject when currentProject is null", async () => {
        const updatedProject = { ...mockProject, name: "Updated Name" };
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(updatedProject),
        });

        const store = createTestStore({
          projects: [mockProject],
          currentProject: null,
        });
        await store.dispatch(
          updateProject({ projectId: "proj-1", name: "Updated Name" }),
        );

        // currentProject should remain null
        expect(selectCurrentProject(store.getState())).toBeNull();
        // But projects array should be updated
        expect(selectProjects(store.getState())[0].name).toBe("Updated Name");
      });

      it("should not update currentProject when it has different id", async () => {
        const otherProject: Project = {
          ...mockProject,
          id: "proj-2",
          name: "Other Project",
        };
        const updatedProject = { ...mockProject, name: "Updated Name" };
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(updatedProject),
        });

        const store = createTestStore({
          projects: [mockProject],
          currentProject: otherProject,
        });
        await store.dispatch(
          updateProject({ projectId: "proj-1", name: "Updated Name" }),
        );

        // currentProject should remain unchanged (different id)
        expect(selectCurrentProject(store.getState())?.name).toBe("Other Project");
        // But projects array should be updated
        expect(selectProjects(store.getState())[0].name).toBe("Updated Name");
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

    describe("selectCurrentProjectDetail", () => {
      it("should return null when no detail loaded", () => {
        const store = createTestStore();
        expect(selectCurrentProjectDetail(store.getState())).toBeNull();
      });

      it("should return project detail when loaded", () => {
        const detail: ProjectDetail = {
          ...mockProject,
          workflows: [],
          sessions: [],
          connections: [],
        };
        const store = createTestStore({ currentProjectDetail: detail });
        expect(selectCurrentProjectDetail(store.getState())?.id).toBe("proj-1");
      });
    });

    describe("selectIsLoadingProjectDetail", () => {
      it("should return false when not loading", () => {
        const store = createTestStore({ isLoadingDetail: false });
        expect(selectIsLoadingProjectDetail(store.getState())).toBe(false);
      });

      it("should return true when loading", () => {
        const store = createTestStore({ isLoadingDetail: true });
        expect(selectIsLoadingProjectDetail(store.getState())).toBe(true);
      });
    });

    describe("selectProjectTotal", () => {
      it("should return total count", () => {
        const store = createTestStore({ total: 10 });
        expect(selectProjectTotal(store.getState())).toBe(10);
      });
    });
  });
});
