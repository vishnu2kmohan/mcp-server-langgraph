/**
 * HITL Preferences Tests
 *
 * TDD tests for Human-in-the-Loop preferences in PreferencesContext.
 * Tests verify:
 * - HITLPreferences interface exists in types
 * - UserPreferences includes hitl property
 * - updateHITLPreferences action exists
 * - Default values are correct
 * - Settings persist correctly
 *
 * RED phase - tests written FIRST before implementation.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor, act, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { PreferencesProvider, usePreferences } from "./PreferencesContext";
import type { HITLPreferences } from "../types/preferences";
import { DEFAULT_USER_PREFERENCES } from "../types/preferences";
import { storage } from "../utils/storage";
import { api } from "../api";

// Mock storage
vi.mock("../utils/storage", async () => {
  const actual = await vi.importActual("../utils/storage");
  return {
    ...actual,
    storage: {
      get: vi.fn(),
      set: vi.fn(() => true),
      remove: vi.fn(),
    },
    STORAGE_KEYS: {
      PREFERENCES: "mcp_user_preferences",
    },
  };
});
// Create a minimal store for testing
const createTestStore = () =>
  configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });

// Test component that exposes preferences
function TestComponent({
  onPreferences,
}: {
  onPreferences: (prefs: ReturnType<typeof usePreferences>) => void;
}) {
  const prefs = usePreferences();
  onPreferences(prefs);
  return <div data-testid="test">Loaded</div>;
}

describe("HITL Preferences Types", () => {
  it("should have HITLPreferences interface with correct properties", () => {
    // This test verifies the type exists by importing it
    // The test will fail at compile time if the type doesn't exist
    const hitlPrefs: HITLPreferences = {
      enabled: true,
      confidenceThreshold: 0.7,
      autoApproveThreshold: 0.9,
      pushNotificationsEnabled: true,
      soundEnabled: false,
      taskOverrides: {},
    };

    expect(hitlPrefs.enabled).toBe(true);
    expect(hitlPrefs.confidenceThreshold).toBe(0.7);
    expect(hitlPrefs.autoApproveThreshold).toBe(0.9);
    expect(hitlPrefs.pushNotificationsEnabled).toBe(true);
    expect(hitlPrefs.soundEnabled).toBe(false);
    expect(hitlPrefs.taskOverrides).toEqual({});
  });

  it("should include hitl property in UserPreferences", () => {
    // Verify hitl exists in DEFAULT_USER_PREFERENCES (imported at top of file)
    expect(DEFAULT_USER_PREFERENCES).toHaveProperty("hitl");
    expect(DEFAULT_USER_PREFERENCES.hitl).toHaveProperty("enabled");
    expect(DEFAULT_USER_PREFERENCES.hitl).toHaveProperty("confidenceThreshold");
    expect(DEFAULT_USER_PREFERENCES.hitl).toHaveProperty(
      "autoApproveThreshold",
    );
    expect(DEFAULT_USER_PREFERENCES.hitl).toHaveProperty(
      "pushNotificationsEnabled",
    );
  });

  it("should have correct default values for HITL preferences", () => {
    // Verify default values from imported constant
    expect(DEFAULT_USER_PREFERENCES.hitl.enabled).toBe(true);
    expect(DEFAULT_USER_PREFERENCES.hitl.confidenceThreshold).toBe(0.7);
    expect(DEFAULT_USER_PREFERENCES.hitl.autoApproveThreshold).toBe(0.9);
    expect(DEFAULT_USER_PREFERENCES.hitl.pushNotificationsEnabled).toBe(true);
    expect(DEFAULT_USER_PREFERENCES.hitl.soundEnabled).toBe(false);
  });
});

describe("PreferencesContext HITL Support", () => {
  let store: ReturnType<typeof createTestStore>;
  let capturedPrefs: ReturnType<typeof usePreferences> | null = null;

  beforeEach(() => {
    vi.clearAllMocks();
    store = createTestStore();
    capturedPrefs = null;
    // Reset storage mock
    vi.mocked(storage.get).mockReturnValue(null);
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  const renderWithProvider = () => {
    return render(
      <Provider store={store}>
        <PreferencesProvider>
          <TestComponent
            onPreferences={(prefs) => {
              capturedPrefs = prefs;
            }}
          />
        </PreferencesProvider>
      </Provider>,
    );
  };

  it("should provide updateHITLPreferences action", async () => {
    renderWithProvider();

    await waitFor(() => {
      expect(screen.getByTestId("test")).toBeInTheDocument();
    });

    expect(capturedPrefs).not.toBeNull();
    expect(capturedPrefs).toHaveProperty("updateHITLPreferences");
    expect(typeof capturedPrefs?.updateHITLPreferences).toBe("function");
  });

  it("should include hitl in preferences object", async () => {
    renderWithProvider();

    await waitFor(() => {
      expect(screen.getByTestId("test")).toBeInTheDocument();
    });

    expect(capturedPrefs?.preferences).toHaveProperty("hitl");
    expect(capturedPrefs?.preferences.hitl).toHaveProperty("enabled");
    expect(capturedPrefs?.preferences.hitl).toHaveProperty(
      "confidenceThreshold",
    );
  });

  it("should update HITL preferences when updateHITLPreferences is called", async () => {
    renderWithProvider();

    await waitFor(() => {
      expect(screen.getByTestId("test")).toBeInTheDocument();
    });

    // Update HITL preferences
    act(() => {
      capturedPrefs?.updateHITLPreferences({
        confidenceThreshold: 0.8,
      });
    });

    // Verify update (immediate state update, debounce is for persistence)
    expect(capturedPrefs?.preferences.hitl.confidenceThreshold).toBe(0.8);
  });

  it("should persist HITL preferences to storage", async () => {
    renderWithProvider();

    await waitFor(() => {
      expect(screen.getByTestId("test")).toBeInTheDocument();
    });

    // Update HITL preferences
    act(() => {
      capturedPrefs?.updateHITLPreferences({
        enabled: false,
      });
    });

    // Wait for debounced storage call with updated value (500ms + buffer)
    await waitFor(
      () => {
        const calls = vi.mocked(storage.set).mock.calls;
        const lastCall = calls[calls.length - 1];
        expect(lastCall).toBeDefined();
        expect(lastCall[1]).toHaveProperty("hitl");
        expect(lastCall[1].hitl.enabled).toBe(false);
      },
      { timeout: 1500 },
    );
  });

  it("should load HITL preferences from storage on mount", async () => {
    const storedPrefs = {
      general: {
        theme: "dark",
        language: "en",
        autoScroll: true,
        notificationsEnabled: true,
      },
      accessibility: {
        reducedMotion: false,
        highContrast: false,
        screenReaderMode: false,
        fontSize: "medium",
      },
      modelDefaults: {
        defaultModel: null,
        defaultTemperature: 0.7,
        defaultMaxTokens: 4096,
      },
      session: {
        pinnedSessions: [],
        recentSessions: [],
        maxRecentSessions: 10,
      },
      privacy: {
        analyticsEnabled: true,
        errorReportingEnabled: true,
        storeHistoryLocally: true,
      },
      hitl: {
        enabled: false,
        confidenceThreshold: 0.6,
        autoApproveThreshold: 0.95,
        pushNotificationsEnabled: false,
        soundEnabled: true,
        taskOverrides: { analysis: { enabled: true, threshold: 0.5 } },
      },
      keyboardShortcuts: {},
      updatedAt: Date.now(),
    };

    vi.mocked(storage.get).mockReturnValue(storedPrefs);

    renderWithProvider();

    await waitFor(() => {
      expect(screen.getByTestId("test")).toBeInTheDocument();
    });

    // Verify stored HITL preferences were loaded
    expect(capturedPrefs?.preferences.hitl.enabled).toBe(false);
    expect(capturedPrefs?.preferences.hitl.confidenceThreshold).toBe(0.6);
    expect(capturedPrefs?.preferences.hitl.autoApproveThreshold).toBe(0.95);
    expect(capturedPrefs?.preferences.hitl.soundEnabled).toBe(true);
  });
});

describe("useHITLPreferences Hook", () => {
  let store: ReturnType<typeof createTestStore>;

  beforeEach(() => {
    vi.clearAllMocks();
    store = createTestStore();
    vi.mocked(storage.get).mockReturnValue(null);
  });

  it("should export useHITLPreferences hook", async () => {
    // This will fail at compile time if hook doesn't exist
    const { useHITLPreferences } = await import("./PreferencesContext");
    expect(typeof useHITLPreferences).toBe("function");
  });

  it("should return HITL preferences and update functions", async () => {
    const { useHITLPreferences } = await import("./PreferencesContext");

    let hookResult: ReturnType<typeof useHITLPreferences> | null = null;

    function TestHook() {
      hookResult = useHITLPreferences();
      return <div data-testid="hook-test">Hook Loaded</div>;
    }

    render(
      <Provider store={store}>
        <PreferencesProvider>
          <TestHook />
        </PreferencesProvider>
      </Provider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("hook-test")).toBeInTheDocument();
    });

    expect(hookResult).not.toBeNull();
    expect(hookResult).toHaveProperty("enabled");
    expect(hookResult).toHaveProperty("confidenceThreshold");
    expect(hookResult).toHaveProperty("autoApproveThreshold");
    expect(hookResult).toHaveProperty("pushNotificationsEnabled");
    expect(hookResult).toHaveProperty("setEnabled");
    expect(hookResult).toHaveProperty("setConfidenceThreshold");
    expect(hookResult).toHaveProperty("setAutoApproveThreshold");
    expect(hookResult).toHaveProperty("togglePushNotifications");
  });
});
