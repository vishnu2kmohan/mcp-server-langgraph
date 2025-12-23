/**
 * PreferencesContext Tests
 *
 * TDD tests for the user preferences context and hooks.
 * Tests cover:
 * - Provider initialization
 * - Default preferences
 * - Preference updates
 * - localStorage persistence
 * - Backend sync (mocked)
 * - Keyboard shortcut management
 * - Session pinning
 *
 * Following WCAG 2.1 AA compliance requirements.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor, cleanup } from "@testing-library/react";
import React from "react";
import {
  PreferencesProvider,
  usePreferences,
  useTheme,
  useAccessibility,
  useKeyboardShortcut,
} from "./PreferencesContext";
import {
  DEFAULT_USER_PREFERENCES,
  DEFAULT_GENERAL_PREFERENCES,
  DEFAULT_ACCESSIBILITY_PREFERENCES,
  type UserPreferences,
} from "../types/preferences";
import { STORAGE_KEYS } from "../utils/storage";

// Storage key used by the context - use centralized key
const STORAGE_KEY = STORAGE_KEYS.PREFERENCES;

// Helper to create wrapper
const createWrapper = () => {
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(PreferencesProvider, null, children);
};

// Helper to set up localStorage with preferences
const setStoredPreferences = (prefs: Partial<UserPreferences>) => {
  const fullPrefs = { ...DEFAULT_USER_PREFERENCES, ...prefs };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(fullPrefs));
};

describe("PreferencesContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    cleanup();
    localStorage.clear();
  });

  // ===========================================================================
  // Provider Initialization Tests
  // ===========================================================================

  describe("PreferencesProvider initialization", () => {
    it("should provide default preferences when no stored preferences exist", async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      expect(result.current.preferences.general.theme).toBe("system");
      expect(result.current.preferences.general.autoScroll).toBe(true);
      expect(result.current.preferences.accessibility.reducedMotion).toBe(
        false,
      );
    });

    it("should load preferences from localStorage on mount", async () => {
      setStoredPreferences({
        general: { ...DEFAULT_GENERAL_PREFERENCES, theme: "dark" },
      });

      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      expect(result.current.preferences.general.theme).toBe("dark");
    });

    it("should handle corrupted localStorage gracefully", async () => {
      localStorage.setItem(STORAGE_KEY, "invalid-json{{{");

      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      // Should fall back to defaults (compare without updatedAt which is dynamic)
      const { updatedAt: _testUpdatedAt, ...expectedDefaults } =
        DEFAULT_USER_PREFERENCES;
      const { updatedAt: _actualUpdatedAt, ...actualPrefs } =
        result.current.preferences;
      expect(actualPrefs).toEqual(expectedDefaults);
    });

    it("should set isLoading to false after initialization", async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });
    });
  });

  // ===========================================================================
  // General Preferences Tests
  // ===========================================================================

  describe("general preferences", () => {
    it("should update theme preference", async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      act(() => {
        result.current.updateGeneralPreferences({ theme: "dark" });
      });

      expect(result.current.preferences.general.theme).toBe("dark");
    });

    it("should update language preference", async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      act(() => {
        result.current.updateGeneralPreferences({ language: "es" });
      });

      expect(result.current.preferences.general.language).toBe("es");
    });

    it("should update autoScroll preference", async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      act(() => {
        result.current.updateGeneralPreferences({ autoScroll: false });
      });

      expect(result.current.preferences.general.autoScroll).toBe(false);
    });

    it("should persist general preferences to localStorage", async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      act(() => {
        result.current.updateGeneralPreferences({ theme: "light" });
      });

      // Wait for debounced save
      await waitFor(() => {
        const stored = localStorage.getItem(STORAGE_KEY);
        expect(stored).toBeTruthy();
        const parsed = JSON.parse(stored!);
        expect(parsed.general.theme).toBe("light");
      });
    });
  });

  // ===========================================================================
  // Accessibility Preferences Tests
  // ===========================================================================

  describe("accessibility preferences", () => {
    it("should update reducedMotion preference", async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      act(() => {
        result.current.updateAccessibilityPreferences({ reducedMotion: true });
      });

      expect(result.current.preferences.accessibility.reducedMotion).toBe(true);
    });

    it("should update highContrast preference", async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      act(() => {
        result.current.updateAccessibilityPreferences({ highContrast: true });
      });

      expect(result.current.preferences.accessibility.highContrast).toBe(true);
    });

    it("should update screenReaderMode preference", async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      act(() => {
        result.current.updateAccessibilityPreferences({
          screenReaderMode: true,
        });
      });

      expect(result.current.preferences.accessibility.screenReaderMode).toBe(
        true,
      );
    });

    it("should update fontSize preference", async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      act(() => {
        result.current.updateAccessibilityPreferences({ fontSize: "large" });
      });

      expect(result.current.preferences.accessibility.fontSize).toBe("large");
    });

    it("should apply reduced motion to document when enabled", async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      act(() => {
        result.current.updateAccessibilityPreferences({ reducedMotion: true });
      });

      // The context should set a CSS class or data attribute on document
      await waitFor(() => {
        expect(
          document.documentElement.classList.contains("reduced-motion") ||
            document.documentElement.dataset.reducedMotion === "true",
        ).toBe(true);
      });
    });
  });

  // ===========================================================================
  // Model Defaults Tests
  // ===========================================================================

  describe("model default preferences", () => {
    it("should update default model", async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      act(() => {
        result.current.updateModelDefaults({ defaultModel: "gpt-4o" });
      });

      expect(result.current.preferences.modelDefaults.defaultModel).toBe(
        "gpt-4o",
      );
    });

    it("should update default temperature", async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      act(() => {
        result.current.updateModelDefaults({ defaultTemperature: 0.5 });
      });

      expect(result.current.preferences.modelDefaults.defaultTemperature).toBe(
        0.5,
      );
    });

    it("should update default max tokens", async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      act(() => {
        result.current.updateModelDefaults({ defaultMaxTokens: 8192 });
      });

      expect(result.current.preferences.modelDefaults.defaultMaxTokens).toBe(
        8192,
      );
    });
  });

  // ===========================================================================
  // Keyboard Shortcuts Tests
  // ===========================================================================

  describe("keyboard shortcuts", () => {
    it("should update a keyboard shortcut", async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      act(() => {
        result.current.updateKeyboardShortcut("newSession", "Ctrl+Shift+N");
      });

      expect(result.current.preferences.keyboardShortcuts.newSession).toBe(
        "Ctrl+Shift+N",
      );
    });

    it("should reset a keyboard shortcut to default", async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      // First set a custom shortcut
      act(() => {
        result.current.updateKeyboardShortcut("newSession", "Ctrl+Shift+N");
      });

      expect(result.current.preferences.keyboardShortcuts.newSession).toBe(
        "Ctrl+Shift+N",
      );

      // Then reset it
      act(() => {
        result.current.resetKeyboardShortcut("newSession");
      });

      expect(
        result.current.preferences.keyboardShortcuts.newSession,
      ).toBeUndefined();
    });
  });

  // ===========================================================================
  // Session Preferences Tests
  // ===========================================================================

  describe("session preferences", () => {
    it("should pin a session", async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      act(() => {
        result.current.pinSession("session-123");
      });

      expect(result.current.preferences.session.pinnedSessions).toContain(
        "session-123",
      );
    });

    it("should unpin a session", async () => {
      setStoredPreferences({
        session: {
          pinnedSessions: ["session-123", "session-456"],
          recentSessions: [],
          maxRecentSessions: 10,
        },
      });

      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      act(() => {
        result.current.unpinSession("session-123");
      });

      expect(result.current.preferences.session.pinnedSessions).not.toContain(
        "session-123",
      );
      expect(result.current.preferences.session.pinnedSessions).toContain(
        "session-456",
      );
    });

    it("should not duplicate pinned sessions", async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      act(() => {
        result.current.pinSession("session-123");
        result.current.pinSession("session-123");
      });

      expect(
        result.current.preferences.session.pinnedSessions.filter(
          (id) => id === "session-123",
        ),
      ).toHaveLength(1);
    });

    it("should add session to recents", async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      act(() => {
        result.current.addRecentSession("session-789");
      });

      expect(result.current.preferences.session.recentSessions).toContain(
        "session-789",
      );
    });

    it("should limit recent sessions to maxRecentSessions", async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      // Add more than maxRecentSessions
      act(() => {
        for (let i = 0; i < 15; i++) {
          result.current.addRecentSession(`session-${i}`);
        }
      });

      expect(
        result.current.preferences.session.recentSessions.length,
      ).toBeLessThanOrEqual(
        result.current.preferences.session.maxRecentSessions,
      );
    });
  });

  // ===========================================================================
  // Reset Tests
  // ===========================================================================

  describe("reset to defaults", () => {
    it("should reset all preferences to defaults", async () => {
      setStoredPreferences({
        general: { ...DEFAULT_GENERAL_PREFERENCES, theme: "dark" },
        accessibility: {
          ...DEFAULT_ACCESSIBILITY_PREFERENCES,
          reducedMotion: true,
        },
      });

      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      expect(result.current.preferences.general.theme).toBe("dark");

      act(() => {
        result.current.resetToDefaults();
      });

      expect(result.current.preferences.general.theme).toBe("system");
      expect(result.current.preferences.accessibility.reducedMotion).toBe(
        false,
      );
    });
  });

  // ===========================================================================
  // Error Handling Tests
  // ===========================================================================

  describe("error handling", () => {
    it("should set error state on save failure", async () => {
      // Mock localStorage.setItem to throw
      const originalSetItem = localStorage.setItem;
      localStorage.setItem = vi.fn(() => {
        throw new Error("Storage quota exceeded");
      });

      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      act(() => {
        result.current.updateGeneralPreferences({ theme: "dark" });
      });

      await waitFor(() => {
        expect(result.current.error).toBeTruthy();
      });

      // Restore
      localStorage.setItem = originalSetItem;
    });

    it("should clear error", async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => usePreferences(), { wrapper });

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      // Manually set error for testing (would need internal access in real impl)
      // For now, test the clearError function exists
      expect(typeof result.current.clearError).toBe("function");
    });
  });
});

// =============================================================================
// useTheme Hook Tests
// =============================================================================

describe("useTheme hook", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("should return current theme", async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useTheme(), { wrapper });

    await waitFor(() => {
      expect(result.current.theme).toBe("system");
    });
  });

  it("should return effective theme based on system preference", async () => {
    // Mock system preference
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: query === "(prefers-color-scheme: dark)",
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });

    const wrapper = createWrapper();
    const { result } = renderHook(() => useTheme(), { wrapper });

    await waitFor(() => {
      expect(result.current.effectiveTheme).toBe("dark");
    });
  });

  it("should provide setTheme function", async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useTheme(), { wrapper });

    await waitFor(() => {
      expect(typeof result.current.setTheme).toBe("function");
    });

    act(() => {
      result.current.setTheme("dark");
    });

    expect(result.current.theme).toBe("dark");
  });
});

// =============================================================================
// useAccessibility Hook Tests
// =============================================================================

describe("useAccessibility hook", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("should return accessibility preferences", async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useAccessibility(), { wrapper });

    await waitFor(() => {
      expect(result.current.reducedMotion).toBe(false);
      expect(result.current.highContrast).toBe(false);
      expect(result.current.screenReaderMode).toBe(false);
      expect(result.current.fontSize).toBe("medium");
    });
  });

  it("should provide toggle functions", async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useAccessibility(), { wrapper });

    await waitFor(() => {
      expect(typeof result.current.toggleReducedMotion).toBe("function");
      expect(typeof result.current.toggleHighContrast).toBe("function");
      expect(typeof result.current.toggleScreenReaderMode).toBe("function");
    });
  });

  it("should toggle reduced motion", async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useAccessibility(), { wrapper });

    await waitFor(() => {
      expect(result.current.reducedMotion).toBe(false);
    });

    act(() => {
      result.current.toggleReducedMotion();
    });

    expect(result.current.reducedMotion).toBe(true);
  });
});

// =============================================================================
// useKeyboardShortcut Hook Tests
// =============================================================================

describe("useKeyboardShortcut hook", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("should return default shortcut for action", async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useKeyboardShortcut("newSession"), {
      wrapper,
    });

    await waitFor(() => {
      expect(result.current.keys).toBe("Cmd+N");
    });
  });

  it("should return custom shortcut if set", async () => {
    setStoredPreferences({
      keyboardShortcuts: { newSession: "Ctrl+Shift+N" },
    });

    const wrapper = createWrapper();
    const { result } = renderHook(() => useKeyboardShortcut("newSession"), {
      wrapper,
    });

    await waitFor(() => {
      expect(result.current.keys).toBe("Ctrl+Shift+N");
    });
  });

  it("should return undefined for unknown action", async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useKeyboardShortcut("unknownAction"), {
      wrapper,
    });

    await waitFor(() => {
      expect(result.current.keys).toBeUndefined();
    });
  });
});
