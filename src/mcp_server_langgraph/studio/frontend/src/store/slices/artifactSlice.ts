/**
 * Artifact Slice
 *
 * Redux slice for managing artifacts (charts, tables, code, diagrams, etc.)
 * displayed in chat messages and other UI components.
 */

import { createSlice, createSelector, PayloadAction } from "@reduxjs/toolkit";
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
/**
 * Factory for selecting artifacts by type (memoized)
 * Caches selector instances per type to prevent redundant filtering
 */
const selectArtifactsByTypeCache = new Map<
  ArtifactType,
  ReturnType<typeof createSelector<[typeof selectArtifacts], Artifact[]>>
>();

export const selectArtifactsByType = (type: ArtifactType) => {
  if (!selectArtifactsByTypeCache.has(type)) {
    selectArtifactsByTypeCache.set(
      type,
      createSelector([selectArtifacts], (artifacts): Artifact[] =>
        artifacts.filter((a) => a.type === type),
      ),
    );
  }
  return selectArtifactsByTypeCache.get(type)!;
};
/**
 * Select the currently selected artifact (memoized)
 * Only recomputes when artifacts array or selectedArtifactId changes
 */
export const selectSelectedArtifact = createSelector(
  [selectArtifacts, selectSelectedArtifactId],
  (artifacts, selectedId): Artifact | null => {
    if (!selectedId) return null;
    return artifacts.find((a) => a.id === selectedId) ?? null;
  },
);

// ============================================================================
// Export
// ============================================================================

export default artifactSlice.reducer;
