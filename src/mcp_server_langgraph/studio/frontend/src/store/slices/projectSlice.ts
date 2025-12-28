/**
 * Project Slice
 *
 * Redux slice for managing project context in the Unified Workspace Paradigm.
 */

import { createSlice, createAsyncThunk, PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "../index";
import { authenticatedFetch } from "../../utils/authenticatedFetch";

// ============================================================================
// Types
// ============================================================================

export interface Project {
  id: string;
  name: string;
  description: string | null;
  owner_id: string;
  organization_id: string | null;
  created_at: string;
  updated_at: string;
  workflow_count: number;
  session_count: number;
  connection_count: number;
  status: string;
}

export interface ProjectDetail extends Project {
  workflows: Array<{ id: string; name: string; created_at: string | null }>;
  sessions: Array<{
    id: string;
    name: string;
    message_count: number;
    created_at: string | null;
  }>;
  connections: Array<{
    id: string;
    type: string;
    name: string;
    status: string;
  }>;
  members: Array<{ user_id: string; role: string; added_at: string }>;
}

export interface ProjectState {
  currentProject: Project | null;
  currentProjectDetail: ProjectDetail | null;
  projects: Project[];
  isLoading: boolean;
  isLoadingDetail: boolean;
  error: string | null;
  total: number;
  page: number;
  perPage: number;
}

// ============================================================================
// Initial State
// ============================================================================

export const initialProjectState: ProjectState = {
  currentProject: null,
  currentProjectDetail: null,
  projects: [],
  isLoading: false,
  isLoadingDetail: false,
  error: null,
  total: 0,
  page: 1,
  perPage: 20,
};

// ============================================================================
// Async Thunks
// ============================================================================

export const fetchProjects = createAsyncThunk<
  { projects: Project[]; total: number; page: number; perPage: number },
  { page?: number; perPage?: number } | void,
  { rejectValue: string }
>("project/fetchProjects", async (params, { rejectWithValue }) => {
  try {
    const page = params?.page ?? 1;
    const perPage = params?.perPage ?? 20;
    const response = await authenticatedFetch(
      `/api/v1/projects?page=${page}&per_page=${perPage}`,
    );

    if (!response.ok) {
      throw new Error("Failed to load projects");
    }

    const data = await response.json();
    return {
      // Backend returns 'items' per PagePaginatedResponse contract
      projects: data.items || [],
      total: data.total || 0,
      page: data.page || 1,
      perPage: data.per_page || 20,
    };
  } catch (error) {
    return rejectWithValue(
      error instanceof Error ? error.message : "Failed to load projects",
    );
  }
});

export const loadProject = createAsyncThunk<
  ProjectDetail,
  string,
  { rejectValue: string }
>("project/loadProject", async (projectId, { rejectWithValue }) => {
  try {
    const response = await authenticatedFetch(`/api/v1/projects/${projectId}`);

    if (!response.ok) {
      throw new Error("Failed to load project");
    }

    return await response.json();
  } catch (error) {
    return rejectWithValue(
      error instanceof Error ? error.message : "Failed to load project",
    );
  }
});

export const createProject = createAsyncThunk<
  Project,
  { name: string; description?: string | null },
  { rejectValue: string }
>("project/createProject", async (params, { rejectWithValue }) => {
  try {
    const response = await authenticatedFetch("/api/v1/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: params.name,
        description: params.description || null,
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to create project");
    }

    return await response.json();
  } catch (error) {
    return rejectWithValue(
      error instanceof Error ? error.message : "Failed to create project",
    );
  }
});

export const deleteProject = createAsyncThunk<
  string,
  string,
  { rejectValue: string }
>("project/deleteProject", async (projectId, { rejectWithValue }) => {
  try {
    const response = await authenticatedFetch(`/api/v1/projects/${projectId}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      throw new Error("Failed to delete project");
    }

    return projectId;
  } catch (error) {
    return rejectWithValue(
      error instanceof Error ? error.message : "Failed to delete project",
    );
  }
});

export const updateProject = createAsyncThunk<
  Project,
  { projectId: string; name?: string; description?: string | null },
  { rejectValue: string }
>(
  "project/updateProject",
  async ({ projectId, ...updates }, { rejectWithValue }) => {
    try {
      const response = await authenticatedFetch(
        `/api/v1/projects/${projectId}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(updates),
        },
      );

      if (!response.ok) {
        throw new Error("Failed to update project");
      }

      return await response.json();
    } catch (error) {
      return rejectWithValue(
        error instanceof Error ? error.message : "Failed to update project",
      );
    }
  },
);

// ============================================================================
// Slice
// ============================================================================

export const projectSlice = createSlice({
  name: "project",
  initialState: initialProjectState,
  reducers: {
    setCurrentProject: (state, action: PayloadAction<Project | null>) => {
      state.currentProject = action.payload;
    },
    clearCurrentProject: (state) => {
      state.currentProject = null;
      state.currentProjectDetail = null;
    },
    clearError: (state) => {
      state.error = null;
    },
    resetProject: (_state) => {
      return initialProjectState;
    },
  },
  extraReducers: (builder) => {
    // fetchProjects
    builder
      .addCase(fetchProjects.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchProjects.fulfilled, (state, action) => {
        state.projects = action.payload.projects;
        state.total = action.payload.total;
        state.page = action.payload.page;
        state.perPage = action.payload.perPage;
        state.isLoading = false;
      })
      .addCase(fetchProjects.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload || "Failed to load projects";
      });

    // loadProject
    builder
      .addCase(loadProject.pending, (state) => {
        state.isLoadingDetail = true;
        state.error = null;
      })
      .addCase(loadProject.fulfilled, (state, action) => {
        state.currentProject = action.payload;
        state.currentProjectDetail = action.payload;
        state.isLoadingDetail = false;
      })
      .addCase(loadProject.rejected, (state, action) => {
        state.isLoadingDetail = false;
        state.currentProject = null;
        state.currentProjectDetail = null;
        state.error = action.payload || "Failed to load project";
      });

    // createProject
    builder
      .addCase(createProject.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(createProject.fulfilled, (state, action) => {
        state.projects.unshift(action.payload);
        state.total += 1;
        state.isLoading = false;
      })
      .addCase(createProject.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload || "Failed to create project";
      });

    // deleteProject
    builder
      .addCase(deleteProject.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(deleteProject.fulfilled, (state, action) => {
        state.projects = state.projects.filter((p) => p.id !== action.payload);
        state.total -= 1;
        if (state.currentProject?.id === action.payload) {
          state.currentProject = null;
          state.currentProjectDetail = null;
        }
        state.isLoading = false;
      })
      .addCase(deleteProject.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload || "Failed to delete project";
      });

    // updateProject
    builder
      .addCase(updateProject.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(updateProject.fulfilled, (state, action) => {
        const index = state.projects.findIndex(
          (p) => p.id === action.payload.id,
        );
        if (index !== -1) {
          state.projects[index] = action.payload;
        }
        if (state.currentProject?.id === action.payload.id) {
          state.currentProject = action.payload;
        }
        state.isLoading = false;
      })
      .addCase(updateProject.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload || "Failed to update project";
      });
  },
});

// ============================================================================
// Actions
// ============================================================================

export const {
  setCurrentProject,
  clearCurrentProject,
  clearError,
  resetProject,
} = projectSlice.actions;

// ============================================================================
// Selectors
// ============================================================================

export const selectProjects = (state: RootState) => state.project.projects;
export const selectCurrentProject = (state: RootState) =>
  state.project.currentProject;
export const selectCurrentProjectDetail = (state: RootState) =>
  state.project.currentProjectDetail;
export const selectIsLoadingProjects = (state: RootState) =>
  state.project.isLoading;
export const selectIsLoadingProjectDetail = (state: RootState) =>
  state.project.isLoadingDetail;
export const selectProjectError = (state: RootState) => state.project.error;
export const selectProjectTotal = (state: RootState) => state.project.total;
export const selectProjectById = (id: string) => (state: RootState) =>
  state.project.projects.find((p) => p.id === id);

// ============================================================================
// Export
// ============================================================================

export default projectSlice.reducer;
