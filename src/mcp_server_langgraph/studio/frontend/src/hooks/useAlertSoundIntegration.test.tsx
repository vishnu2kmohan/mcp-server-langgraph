/**
 * useAlertSoundIntegration Hook Tests
 *
 * Tests the integration between Redux alert state and sound notifications.
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import type { ReactNode } from "react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";

import { useAlertSoundIntegration } from "./useAlertSoundIntegration";
import alertReducer, { addAlert } from "../store/slices/alertSlice";
import type { Alert } from "../store/slices/alertSlice";

// =============================================================================
// Test Setup
// =============================================================================

// Mock the useAlertSound hook
const mockPlayAlertSound = vi.fn();
vi.mock("./useAlertSound", () => ({
  useAlertSound: () => ({
    playAlertSound: mockPlayAlertSound,
    stopSound: vi.fn(),
    isPlaying: false,
  }),
}));

// Create test store
const createTestStore = (
  soundEnabled = true,
  lastCriticalAlertTime: number | null = null,
) =>
  configureStore({
    reducer: {
      alerts: alertReducer,
    },
    preloadedState: {
      alerts: {
        alerts: [],
        selectedAlertId: null,
        pendingRemediations: [],
        soundEnabled,
        lastCriticalAlertTime,
        filters: { severity: ["critical", "warning"], state: ["firing"] },
      },
    },
  });

// Wrapper component
const createWrapper = (store: ReturnType<typeof createTestStore>) => {
  return ({ children }: { children: ReactNode }) => (
    <Provider store={store}>{children}</Provider>
  );
};

// Sample critical alert
const createCriticalAlert = (id: string): Alert => ({
  alert_id: id,
  name: "HighCPUUsage",
  severity: "critical",
  state: "firing",
  message: "CPU usage above 90%",
  labels: {},
  annotations: {},
  started_at: new Date().toISOString(),
  ended_at: null,
  fingerprint: `fp-${id}`,
});

// =============================================================================
// Tests
// =============================================================================

describe("useAlertSoundIntegration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("should not play sound when no critical alert", () => {
    const store = createTestStore();

    renderHook(() => useAlertSoundIntegration(), {
      wrapper: createWrapper(store),
    });

    expect(mockPlayAlertSound).not.toHaveBeenCalled();
  });

  it("should play sound when a new critical alert is added", () => {
    const store = createTestStore();

    renderHook(() => useAlertSoundIntegration(), {
      wrapper: createWrapper(store),
    });

    // Dispatch a critical alert
    act(() => {
      store.dispatch(addAlert(createCriticalAlert("alert-1")));
    });

    expect(mockPlayAlertSound).toHaveBeenCalledWith("critical");
  });

  it("should not play sound when sound is disabled", () => {
    const store = createTestStore(false); // soundEnabled = false

    renderHook(() => useAlertSoundIntegration(), {
      wrapper: createWrapper(store),
    });

    // Dispatch a critical alert
    act(() => {
      store.dispatch(addAlert(createCriticalAlert("alert-1")));
    });

    expect(mockPlayAlertSound).not.toHaveBeenCalled();
  });

  it("should play sound for each new critical alert", () => {
    const store = createTestStore();

    renderHook(() => useAlertSoundIntegration(), {
      wrapper: createWrapper(store),
    });

    // Dispatch first critical alert
    act(() => {
      store.dispatch(addAlert(createCriticalAlert("alert-1")));
    });

    // Advance time to allow second alert
    act(() => {
      vi.advanceTimersByTime(1000);
    });

    // Dispatch second critical alert
    act(() => {
      store.dispatch(addAlert(createCriticalAlert("alert-2")));
    });

    expect(mockPlayAlertSound).toHaveBeenCalledTimes(2);
  });

  it("should not play sound for warning alerts", () => {
    const store = createTestStore();

    renderHook(() => useAlertSoundIntegration(), {
      wrapper: createWrapper(store),
    });

    // Dispatch a warning alert
    act(() => {
      store.dispatch(
        addAlert({
          ...createCriticalAlert("alert-1"),
          severity: "warning",
        }),
      );
    });

    expect(mockPlayAlertSound).not.toHaveBeenCalled();
  });
});
