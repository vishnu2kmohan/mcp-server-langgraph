/**
 * Common Mocks for Test Files
 *
 * Centralized mock definitions to reduce memory overhead from duplicate
 * mock closures across test files. Instead of defining mocks inline in
 * each test file, import these shared mocks.
 *
 * MEMORY OPTIMIZATION:
 * - Each vi.mock() creates closures that persist for the test file's lifetime
 * - By sharing mock implementations, we reduce closure overhead
 * - Mutable state objects allow per-test configuration without re-mocking
 *
 * Usage:
 *   import {
 *     mockTelemetryContext,
 *     mockFeatureFlagContext,
 *     createMockUseFeatureFlag,
 *   } from '../test/commonMocks';
 *
 *   // In your test file, use vi.mock with the shared implementations
 *   vi.mock('../contexts/TelemetryContext', () => mockTelemetryContext);
 *
 * NOTE: vi.mock() calls are hoisted, so the mock modules must be importable
 * at module load time. These exports provide the mock implementations.
 */

import { vi } from "vitest";
import type { ReactNode } from "react";

// =============================================================================
// Telemetry Context Mocks
// =============================================================================

/**
 * Mock implementation for TelemetryContext.
 * Use with: vi.mock('../contexts/TelemetryContext', () => mockTelemetryContext);
 */
export const mockTelemetryContext = {
  TelemetryProvider: ({ children }: { children: ReactNode }) => children,
  useSessionTelemetry: () => ({
    trackSessionCreation: vi.fn(),
    trackRevalidation: vi.fn(),
    trackSync: vi.fn(),
    getMetrics: () => ({}),
  }),
  useWebVitals: () => ({
    start: vi.fn(),
    stop: vi.fn(),
    getMetrics: () => ({ fcp: null, lcp: null, cls: null, inp: null }),
  }),
};

/**
 * Mock implementation for TelemetryViewer component.
 * Use with: vi.mock('../devtools/TelemetryViewer', () => mockTelemetryViewer);
 */
export const mockTelemetryViewer = {
  TelemetryViewer: () => null,
};

// =============================================================================
// Feature Flag Context Mocks
// =============================================================================

/**
 * Mutable feature flag state for per-test configuration.
 * Modify this object in your test to change feature flag behavior.
 *
 * @example
 * beforeEach(() => {
 *   mockFeatureFlagState.enabledFlags = ['canvas_ai_palette', 'ai_suggestions'];
 * });
 */
export const mockFeatureFlagState = {
  /** List of feature flags that should return true */
  enabledFlags: ["canvas_ai_palette", "ai_suggestions"] as string[],
  /** Default return value for flags not in enabledFlags */
  defaultValue: false,
};

/**
 * Create a mock useFeatureFlag function that checks against mockFeatureFlagState.
 * This allows per-test configuration of feature flags.
 */
export function createMockUseFeatureFlag() {
  return vi.fn((flag: string) => {
    return mockFeatureFlagState.enabledFlags.includes(flag)
      ? true
      : mockFeatureFlagState.defaultValue;
  });
}

/**
 * Mock implementation for FeatureFlagContext.
 * Use with: vi.mock('../contexts/FeatureFlagContext', () => mockFeatureFlagContext);
 */
export const mockFeatureFlagContext = {
  useFeatureFlag: createMockUseFeatureFlag(),
  FeatureFlagProvider: ({ children }: { children: ReactNode }) => children,
};

/**
 * Reset feature flag state to defaults.
 * Call in afterEach or beforeEach to ensure clean state.
 */
export function resetFeatureFlagState(): void {
  mockFeatureFlagState.enabledFlags = ["canvas_ai_palette", "ai_suggestions"];
  mockFeatureFlagState.defaultValue = false;
}

// =============================================================================
// HITL (Human-in-the-Loop) Mocks
// =============================================================================

/**
 * Mutable HITL dialogs state for per-test configuration.
 */
export const mockHITLDialogsState = {
  isPending: false,
  isApproved: false,
  pendingCount: 0,
  approvalDialogOpen: false,
  clarificationDialogOpen: false,
};

/**
 * Mock implementation for useHITLDialogs hook.
 */
export function createMockUseHITLDialogs() {
  const mockApprove = vi.fn();
  const mockReject = vi.fn();
  const mockClarify = vi.fn();
  const mockOpenApprovalDialog = vi.fn();
  const mockCloseApprovalDialog = vi.fn();
  const mockOpenClarificationDialog = vi.fn();
  const mockCloseClarificationDialog = vi.fn();

  return {
    mock: vi.fn(() => ({
      isPending: mockHITLDialogsState.isPending,
      isApproved: mockHITLDialogsState.isApproved,
      pendingCount: mockHITLDialogsState.pendingCount,
      approvalDialogOpen: mockHITLDialogsState.approvalDialogOpen,
      clarificationDialogOpen: mockHITLDialogsState.clarificationDialogOpen,
      approve: mockApprove,
      reject: mockReject,
      clarify: mockClarify,
      openApprovalDialog: mockOpenApprovalDialog,
      closeApprovalDialog: mockCloseApprovalDialog,
      openClarificationDialog: mockOpenClarificationDialog,
      closeClarificationDialog: mockCloseClarificationDialog,
    })),
    mockApprove,
    mockReject,
    mockClarify,
    mockOpenApprovalDialog,
    mockCloseApprovalDialog,
    mockOpenClarificationDialog,
    mockCloseClarificationDialog,
  };
}

/**
 * Reset HITL dialogs state to defaults.
 */
export function resetHITLDialogsState(): void {
  mockHITLDialogsState.isPending = false;
  mockHITLDialogsState.isApproved = false;
  mockHITLDialogsState.pendingCount = 0;
  mockHITLDialogsState.approvalDialogOpen = false;
  mockHITLDialogsState.clarificationDialogOpen = false;
}

// =============================================================================
// Nudges Hook Mocks
// =============================================================================

/**
 * Mutable nudges state for per-test configuration.
 */
export const mockNudgesState = {
  activeNudge: null as null | {
    id: string;
    type: string;
    title: string;
    message: string;
    action: unknown;
    priority: number;
    dismissable: boolean;
  },
  nudges: [] as unknown[],
  isLoading: false,
};

/**
 * Create mock functions for useNudges hook.
 */
export function createMockUseNudges() {
  const mockDismiss = vi.fn();
  const mockTrackAcceptance = vi.fn();

  return {
    mock: vi.fn(() => ({
      activeNudge: mockNudgesState.activeNudge,
      nudges: mockNudgesState.nudges,
      isLoading: mockNudgesState.isLoading,
      dismiss: mockDismiss,
      trackAcceptance: mockTrackAcceptance,
    })),
    mockDismiss,
    mockTrackAcceptance,
  };
}

/**
 * Reset nudges state to defaults.
 */
export function resetNudgesState(): void {
  mockNudgesState.activeNudge = null;
  mockNudgesState.nudges = [];
  mockNudgesState.isLoading = false;
}

// =============================================================================
// AI Persona Analysis Mocks
// =============================================================================

/**
 * Mutable persona analysis state for per-test configuration.
 */
export const mockPersonaAnalysisState = {
  isLoading: false,
  error: null as null | Error,
  assignedPersona: "user" as string,
  detectedPersona: null as null | string,
  confidence: 0,
  behaviorSignals: [] as string[],
  recommendation: null as null | string,
  uiAdaptations: [] as string[],
  isPersonaMismatch: false,
};

/**
 * Create mock functions for useAIPersonaAnalysis hook.
 */
export function createMockUseAIPersonaAnalysis() {
  const mockRefresh = vi.fn();

  return {
    mock: vi.fn(() => ({
      ...mockPersonaAnalysisState,
      refresh: mockRefresh,
    })),
    mockRefresh,
  };
}

/**
 * Reset persona analysis state to defaults.
 */
export function resetPersonaAnalysisState(): void {
  mockPersonaAnalysisState.isLoading = false;
  mockPersonaAnalysisState.error = null;
  mockPersonaAnalysisState.assignedPersona = "user";
  mockPersonaAnalysisState.detectedPersona = null;
  mockPersonaAnalysisState.confidence = 0;
  mockPersonaAnalysisState.behaviorSignals = [];
  mockPersonaAnalysisState.recommendation = null;
  mockPersonaAnalysisState.uiAdaptations = [];
  mockPersonaAnalysisState.isPersonaMismatch = false;
}

// =============================================================================
// WebSocket Mocks
// =============================================================================

/**
 * Mutable WebSocket state for per-test configuration.
 */
export const mockWebSocketState = {
  status: "connected" as "connecting" | "connected" | "disconnected" | "error",
  error: null as null | Error,
  messageQueue: [] as unknown[],
};

/**
 * Create mock functions for WebSocket hooks.
 */
export function createMockWebSocket() {
  const mockSend = vi.fn();
  const mockConnect = vi.fn();
  const mockDisconnect = vi.fn();
  const mockSubscribe = vi.fn();

  return {
    mock: vi.fn(() => ({
      status: mockWebSocketState.status,
      error: mockWebSocketState.error,
      send: mockSend,
      connect: mockConnect,
      disconnect: mockDisconnect,
      subscribe: mockSubscribe,
    })),
    mockSend,
    mockConnect,
    mockDisconnect,
    mockSubscribe,
  };
}

/**
 * Reset WebSocket state to defaults.
 */
export function resetWebSocketState(): void {
  mockWebSocketState.status = "connected";
  mockWebSocketState.error = null;
  mockWebSocketState.messageQueue = [];
}

// =============================================================================
// Cross Insights Panel Mocks
// =============================================================================

/**
 * Mutable cross insights panel state for per-test configuration.
 */
export const mockCrossInsightsPanelState = {
  isOpen: false,
  insights: [] as unknown[],
  isLoading: false,
};

/**
 * Create mock functions for useCrossInsightsPanel hook.
 */
export function createMockUseCrossInsightsPanel() {
  const mockOpen = vi.fn();
  const mockClose = vi.fn();
  const mockToggle = vi.fn();
  const mockRefresh = vi.fn();

  return {
    mock: vi.fn(() => ({
      isOpen: mockCrossInsightsPanelState.isOpen,
      insights: mockCrossInsightsPanelState.insights,
      isLoading: mockCrossInsightsPanelState.isLoading,
      open: mockOpen,
      close: mockClose,
      toggle: mockToggle,
      refresh: mockRefresh,
    })),
    mockOpen,
    mockClose,
    mockToggle,
    mockRefresh,
  };
}

/**
 * Reset cross insights panel state to defaults.
 */
export function resetCrossInsightsPanelState(): void {
  mockCrossInsightsPanelState.isOpen = false;
  mockCrossInsightsPanelState.insights = [];
  mockCrossInsightsPanelState.isLoading = false;
}

// =============================================================================
// Comprehensive Reset Function
// =============================================================================

/**
 * Reset ALL mutable mock states to their defaults.
 * Call this in afterEach to ensure clean state between tests.
 *
 * @example
 * afterEach(() => {
 *   resetAllMockStates();
 * });
 */
export function resetAllMockStates(): void {
  resetFeatureFlagState();
  resetHITLDialogsState();
  resetNudgesState();
  resetPersonaAnalysisState();
  resetWebSocketState();
  resetCrossInsightsPanelState();
}
