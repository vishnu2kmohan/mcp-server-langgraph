/**
 * Artifact Slice
 *
 * Redux slice for managing artifacts (charts, tables, code, diagrams, etc.)
 * displayed in chat messages and other UI components.
 */

import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "../index";
import type { Artifact, ArtifactType } from "../../types/artifacts";

// ============================================================================
// State Type
// ============================================================================

export interface ArtifactSliceState {
  artifacts: Artifact[];
  selectedArtifactId: string | null;
}

// ============================================================================
// Initial State
// ============================================================================

export const initialArtifactState: ArtifactSliceState = {
  artifacts: [],
  selectedArtifactId: null,
};

// ============================================================================
// Slice
// ============================================================================

export const artifactSlice = createSlice({
  name: "artifact",
  initialState: initialArtifactState,
  reducers: {
    addArtifact: (state, action: PayloadAction<Artifact>) => {
      state.artifacts.push(action.payload);
    },

    removeArtifact: (state, action: PayloadAction<string>) => {
      const id = action.payload;
      state.artifacts = state.artifacts.filter((a) => a.id !== id);
      // Clear selection if removing selected artifact
      if (state.selectedArtifactId === id) {
        state.selectedArtifactId = null;
      }
    },

    updateArtifact: (
      state,
      action: PayloadAction<{ id: string; updates: Partial<Artifact> }>,
    ) => {
      const { id, updates } = action.payload;
      const artifact = state.artifacts.find((a) => a.id === id);
      if (artifact) {
        Object.assign(artifact, updates);
      }
    },

    selectArtifact: (state, action: PayloadAction<string>) => {
      state.selectedArtifactId = action.payload;
    },

    clearArtifactSelection: (state) => {
      state.selectedArtifactId = null;
    },

    clearArtifacts: (state) => {
      state.artifacts = [];
      state.selectedArtifactId = null;
    },
  },
});

// ============================================================================
// Actions
// ============================================================================

export const {
  addArtifact,
  removeArtifact,
  updateArtifact,
  selectArtifact,
  clearArtifactSelection,
  clearArtifacts,
} = artifactSlice.actions;

// ============================================================================
// Selectors
// ============================================================================

export const selectArtifacts = (state: RootState) => state.artifact.artifacts;
export const selectSelectedArtifactId = (state: RootState) =>
  state.artifact.selectedArtifactId;
export const selectArtifactById = (id: string) => (state: RootState) =>
  state.artifact.artifacts.find((a) => a.id === id);
export const selectArtifactsByType =
  (type: ArtifactType) => (state: RootState) =>
    state.artifact.artifacts.filter((a) => a.type === type);
export const selectSelectedArtifact = (state: RootState) => {
  const id = state.artifact.selectedArtifactId;
  return id ? state.artifact.artifacts.find((a) => a.id === id) : null;
};

// ============================================================================
// Export
// ============================================================================

export default artifactSlice.reducer;
