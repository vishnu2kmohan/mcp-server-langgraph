/**
 * ComplianceSlice - Phase 7
 *
 * State management for compliance dashboard status.
 * Tracks SOC-2, HIPAA, GDPR, and FedRAMP compliance states.
 */
import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

// =============================================================================
// Types
// =============================================================================

export type ComplianceFramework = "SOC2" | "HIPAA" | "GDPR" | "FEDRAMP";
export type ComplianceStatus =
  | "compliant"
  | "partial"
  | "non-compliant"
  | "not-applicable"
  | "loading"
  | "error";

export interface FrameworkStatus {
  framework: ComplianceFramework;
  status: ComplianceStatus;
  score: number;
  totalControls: number;
  compliantControls: number;
  lastAssessed: string | null;
  error?: string;
}

export interface ComplianceState {
  /** Status per framework */
  frameworks: Record<ComplianceFramework, FrameworkStatus>;
  /** Overall compliance score */
  overallScore: number;
  /** Whether data is loading */
  isLoading: boolean;
  /** Last refresh timestamp */
  lastRefresh: string | null;
}

// =============================================================================
// Initial State
// =============================================================================

const defaultFrameworkStatus = (
  framework: ComplianceFramework,
): FrameworkStatus => ({
  framework,
  status: "loading",
  score: 0,
  totalControls: 0,
  compliantControls: 0,
  lastAssessed: null,
});

const initialState: ComplianceState = {
  frameworks: {
    SOC2: defaultFrameworkStatus("SOC2"),
    HIPAA: defaultFrameworkStatus("HIPAA"),
    GDPR: defaultFrameworkStatus("GDPR"),
    FEDRAMP: defaultFrameworkStatus("FEDRAMP"),
  },
  overallScore: 0,
  isLoading: false,
  lastRefresh: null,
};

// =============================================================================
// Slice
// =============================================================================

const complianceSlice = createSlice({
  name: "compliance",
  initialState,
  reducers: {
    /**
     * Set loading state
     */
    setComplianceLoading(state, action: PayloadAction<boolean>) {
      state.isLoading = action.payload;
    },

    /**
     * Update framework status
     */
    setFrameworkStatus(state, action: PayloadAction<FrameworkStatus>) {
      const { framework } = action.payload;
      state.frameworks[framework] = action.payload;
      // Recalculate overall score
      const frameworks = Object.values(state.frameworks);
      const total = frameworks.reduce((acc, f) => acc + f.score, 0);
      state.overallScore = Math.round(total / frameworks.length);
    },

    /**
     * Update multiple frameworks at once
     */
    setAllFrameworkStatuses(
      state,
      action: PayloadAction<
        Partial<Record<ComplianceFramework, FrameworkStatus>>
      >,
    ) {
      Object.entries(action.payload).forEach(([framework, status]) => {
        if (status) {
          state.frameworks[framework as ComplianceFramework] = status;
        }
      });
      // Recalculate overall score
      const frameworks = Object.values(state.frameworks);
      const total = frameworks.reduce((acc, f) => acc + f.score, 0);
      state.overallScore = Math.round(total / frameworks.length);
      state.lastRefresh = new Date().toISOString();
    },

    /**
     * Set framework error
     */
    setFrameworkError(
      state,
      action: PayloadAction<{ framework: ComplianceFramework; error: string }>,
    ) {
      const { framework, error } = action.payload;
      state.frameworks[framework].status = "error";
      state.frameworks[framework].error = error;
    },

    /**
     * Reset compliance state
     */
    resetCompliance() {
      return initialState;
    },
  },
});

// =============================================================================
// Selectors
// =============================================================================

type StateWithCompliance = { compliance: ComplianceState };

export const selectFrameworkStatus = (
  state: StateWithCompliance,
  framework: ComplianceFramework,
): FrameworkStatus => state.compliance.frameworks[framework];

export const selectAllFrameworks = (
  state: StateWithCompliance,
): FrameworkStatus[] => Object.values(state.compliance.frameworks);

export const selectOverallScore = (state: StateWithCompliance): number =>
  state.compliance.overallScore;

export const selectComplianceLoading = (state: StateWithCompliance): boolean =>
  state.compliance.isLoading;

export const selectLastRefresh = (state: StateWithCompliance): string | null =>
  state.compliance.lastRefresh;

// =============================================================================
// Exports
// =============================================================================

export const {
  setComplianceLoading,
  setFrameworkStatus,
  setAllFrameworkStatuses,
  setFrameworkError,
  resetCompliance,
} = complianceSlice.actions;

export default complianceSlice.reducer;
