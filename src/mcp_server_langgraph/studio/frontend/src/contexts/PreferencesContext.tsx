/**
 * PreferencesContext
 *
 * React context for user preferences management.
 * Provides user preferences to all child components with:
 * - localStorage persistence
 * - Backend sync (optional)
 * - Theme management
 * - Accessibility settings
 * - Keyboard shortcuts
 * - Session pinning
 *
 * Based on UX patterns from Gemini CLI, OpenAI Codex, and Claude Code.
 * Implements WCAG 2.1 AA accessibility requirements.
 */

import {
  createContext,
  useContext,
  useCallback,
  useEffect,
  useState,
  useMemo,
  type ReactNode,
} from "react";
import {
  type UserPreferences,
  type GeneralPreferences,
  type AccessibilityPreferences,
  type ModelDefaultPreferences,
  type SessionPreferences,
  type PrivacyPreferences,
  type ThemeMode,
  type PreferencesState,
  type PreferencesActions,
  DEFAULT_USER_PREFERENCES,
  DEFAULT_KEYBOARD_SHORTCUTS,
} from "../types/preferences";
import { store } from "../store";
import { api } from "../api";
import type {
  UserPreferences as ApiUserPreferences,
  UserPreferencesUpdate as ApiUserPreferencesUpdate,
} from "../types/api";

// ==============================================================================
// Constants
// ==============================================================================

/** localStorage key for preferences */
const STORAGE_KEY = "mcp_studio_preferences";

/** Debounce delay for saving preferences (ms) */
const SAVE_DEBOUNCE_MS = 500;

// ==============================================================================
// API Conversion Functions
// ==============================================================================

/**
 * Convert frontend nested preferences to flat API format
 */
function toApiFormat(prefs: UserPreferences): ApiUserPreferencesUpdate {
  return {
    theme: prefs.general.theme,
    language: prefs.general.language,
    auto_scroll: prefs.general.autoScroll,
    reduced_motion: prefs.accessibility.reducedMotion,
    high_contrast: prefs.accessibility.highContrast,
    screen_reader_mode: prefs.accessibility.screenReaderMode,
    font_size: prefs.accessibility.fontSize,
    default_model: prefs.modelDefaults.defaultModel,
    default_temperature: prefs.modelDefaults.defaultTemperature,
    default_max_tokens: prefs.modelDefaults.defaultMaxTokens,
    pinned_sessions: prefs.session.pinnedSessions,
    notifications_enabled: prefs.general.notificationsEnabled,
    keyboard_shortcuts: prefs.keyboardShortcuts,
  };
}

/**
 * Merge API format preferences into frontend nested format
 */
function fromApiFormat(
  apiPrefs: ApiUserPreferences,
  existing: UserPreferences,
): UserPreferences {
  return {
    ...existing,
    general: {
      ...existing.general,
      theme: apiPrefs.theme,
      language: apiPrefs.language,
      autoScroll: apiPrefs.auto_scroll,
      notificationsEnabled: apiPrefs.notifications_enabled,
    },
    accessibility: {
      ...existing.accessibility,
      reducedMotion: apiPrefs.reduced_motion,
      highContrast: apiPrefs.high_contrast,
      screenReaderMode: apiPrefs.screen_reader_mode,
      fontSize: apiPrefs.font_size,
    },
    modelDefaults: {
      ...existing.modelDefaults,
      defaultModel: apiPrefs.default_model,
      defaultTemperature: apiPrefs.default_temperature,
      defaultMaxTokens: apiPrefs.default_max_tokens,
    },
    session: {
      ...existing.session,
      pinnedSessions: apiPrefs.pinned_sessions,
    },
    keyboardShortcuts: apiPrefs.keyboard_shortcuts,
    updatedAt: Date.now(),
  };
}

// ==============================================================================
// Context Types
// ==============================================================================

/** Combined context value */
type PreferencesContextValue = PreferencesState & PreferencesActions;

/** Default context value */
const defaultContextValue: PreferencesContextValue = {
  preferences: DEFAULT_USER_PREFERENCES,
  isLoading: true,
  isInitialized: false,
  isSyncing: false,
  error: null,
  hasUnsavedChanges: false,
  updatePreferences: () => {},
  updateGeneralPreferences: () => {},
  updateAccessibilityPreferences: () => {},
  updateModelDefaults: () => {},
  updateKeyboardShortcut: () => {},
  resetKeyboardShortcut: () => {},
  updateSessionPreferences: () => {},
  updatePrivacyPreferences: () => {},
  pinSession: () => {},
  unpinSession: () => {},
  addRecentSession: () => {},
  resetToDefaults: () => {},
  loadPreferences: async () => {},
  savePreferences: async () => {},
  syncWithBackend: async () => {},
  clearError: () => {},
};

// ==============================================================================
// Context
// ==============================================================================

const PreferencesContext =
  createContext<PreferencesContextValue>(defaultContextValue);

// ==============================================================================
// Provider Props
// ==============================================================================

export interface PreferencesProviderProps {
  children: ReactNode;
}

// ==============================================================================
// Provider Component
// ==============================================================================

/**
 * Preferences provider component.
 * Wraps the application to provide user preferences to all children.
 *
 * @example
 * ```tsx
 * <PreferencesProvider>
 *   <App />
 * </PreferencesProvider>
 * ```
 */
export function PreferencesProvider({ children }: PreferencesProviderProps) {
  const [preferences, setPreferences] = useState<UserPreferences>(
    DEFAULT_USER_PREFERENCES,
  );
  const [isLoading, setIsLoading] = useState(true);
  const [isInitialized, setIsInitialized] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Track save timeout for debouncing
  const [saveTimeoutId, setSaveTimeoutId] = useState<ReturnType<
    typeof setTimeout
  > | null>(null);

  // ---------------------------------------------------------------------------
  // Load preferences from localStorage on mount
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const loadFromStorage = () => {
      try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) {
          const parsed = JSON.parse(stored) as UserPreferences;
          // Merge with defaults to handle missing fields from older versions
          setPreferences({
            ...DEFAULT_USER_PREFERENCES,
            ...parsed,
            general: { ...DEFAULT_USER_PREFERENCES.general, ...parsed.general },
            accessibility: {
              ...DEFAULT_USER_PREFERENCES.accessibility,
              ...parsed.accessibility,
            },
            modelDefaults: {
              ...DEFAULT_USER_PREFERENCES.modelDefaults,
              ...parsed.modelDefaults,
            },
            session: {
              ...DEFAULT_USER_PREFERENCES.session,
              ...parsed.session,
            },
            privacy: { ...DEFAULT_USER_PREFERENCES.privacy, ...parsed.privacy },
          });
        }
      } catch {
        // Fall back to defaults on parse error
        setPreferences(DEFAULT_USER_PREFERENCES);
      } finally {
        setIsLoading(false);
        setIsInitialized(true);
      }
    };

    loadFromStorage();
  }, []);

  // ---------------------------------------------------------------------------
  // Apply accessibility settings to document
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const { reducedMotion, highContrast, fontSize } = preferences.accessibility;

    // Apply reduced motion
    if (reducedMotion) {
      document.documentElement.classList.add("reduced-motion");
      document.documentElement.dataset.reducedMotion = "true";
    } else {
      document.documentElement.classList.remove("reduced-motion");
      document.documentElement.dataset.reducedMotion = "false";
    }

    // Apply high contrast
    if (highContrast) {
      document.documentElement.classList.add("high-contrast");
      document.documentElement.dataset.highContrast = "true";
    } else {
      document.documentElement.classList.remove("high-contrast");
      document.documentElement.dataset.highContrast = "false";
    }

    // Apply font size
    document.documentElement.dataset.fontSize = fontSize;
  }, [preferences.accessibility]);

  // ---------------------------------------------------------------------------
  // Apply theme to document
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const { theme } = preferences.general;

    const applyTheme = (effectiveTheme: "light" | "dark") => {
      document.documentElement.classList.remove("light", "dark");
      document.documentElement.classList.add(effectiveTheme);
      document.documentElement.dataset.theme = effectiveTheme;
    };

    if (theme === "system") {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      applyTheme(mediaQuery.matches ? "dark" : "light");

      const handler = (e: MediaQueryListEvent) => {
        applyTheme(e.matches ? "dark" : "light");
      };
      mediaQuery.addEventListener("change", handler);
      return () => mediaQuery.removeEventListener("change", handler);
    } else {
      applyTheme(theme);
    }
    // We only want to re-run when theme changes, not on every general preferences update
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preferences.general.theme]);

  // ---------------------------------------------------------------------------
  // Save preferences to localStorage (debounced)
  // ---------------------------------------------------------------------------
  const saveToStorage = useCallback(
    (prefs: UserPreferences) => {
      // Clear existing timeout
      if (saveTimeoutId) {
        clearTimeout(saveTimeoutId);
      }

      const timeoutId = setTimeout(() => {
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
          setHasUnsavedChanges(false);
        } catch (err) {
          setError(
            `Failed to save preferences: ${err instanceof Error ? err.message : String(err)}`,
          );
        }
      }, SAVE_DEBOUNCE_MS);

      setSaveTimeoutId(timeoutId);
    },
    [saveTimeoutId],
  );

  // ---------------------------------------------------------------------------
  // Update functions
  // ---------------------------------------------------------------------------

  const updatePreferences = useCallback(
    (updates: Partial<UserPreferences>) => {
      setPreferences((prev) => {
        const updated = {
          ...prev,
          ...updates,
          updatedAt: Date.now(),
        };
        saveToStorage(updated);
        setHasUnsavedChanges(true);
        return updated;
      });
    },
    [saveToStorage],
  );

  const updateGeneralPreferences = useCallback(
    (updates: Partial<GeneralPreferences>) => {
      setPreferences((prev) => {
        const updated = {
          ...prev,
          general: { ...prev.general, ...updates },
          updatedAt: Date.now(),
        };
        saveToStorage(updated);
        setHasUnsavedChanges(true);
        return updated;
      });
    },
    [saveToStorage],
  );

  const updateAccessibilityPreferences = useCallback(
    (updates: Partial<AccessibilityPreferences>) => {
      setPreferences((prev) => {
        const updated = {
          ...prev,
          accessibility: { ...prev.accessibility, ...updates },
          updatedAt: Date.now(),
        };
        saveToStorage(updated);
        setHasUnsavedChanges(true);
        return updated;
      });
    },
    [saveToStorage],
  );

  const updateModelDefaults = useCallback(
    (updates: Partial<ModelDefaultPreferences>) => {
      setPreferences((prev) => {
        const updated = {
          ...prev,
          modelDefaults: { ...prev.modelDefaults, ...updates },
          updatedAt: Date.now(),
        };
        saveToStorage(updated);
        setHasUnsavedChanges(true);
        return updated;
      });
    },
    [saveToStorage],
  );

  const updateKeyboardShortcut = useCallback(
    (action: string, keys: string) => {
      setPreferences((prev) => {
        const updated = {
          ...prev,
          keyboardShortcuts: { ...prev.keyboardShortcuts, [action]: keys },
          updatedAt: Date.now(),
        };
        saveToStorage(updated);
        setHasUnsavedChanges(true);
        return updated;
      });
    },
    [saveToStorage],
  );

  const resetKeyboardShortcut = useCallback(
    (action: string) => {
      setPreferences((prev) => {
        const { [action]: _, ...rest } = prev.keyboardShortcuts;
        const updated = {
          ...prev,
          keyboardShortcuts: rest,
          updatedAt: Date.now(),
        };
        saveToStorage(updated);
        setHasUnsavedChanges(true);
        return updated;
      });
    },
    [saveToStorage],
  );

  const updateSessionPreferences = useCallback(
    (updates: Partial<SessionPreferences>) => {
      setPreferences((prev) => {
        const updated = {
          ...prev,
          session: { ...prev.session, ...updates },
          updatedAt: Date.now(),
        };
        saveToStorage(updated);
        setHasUnsavedChanges(true);
        return updated;
      });
    },
    [saveToStorage],
  );

  const updatePrivacyPreferences = useCallback(
    (updates: Partial<PrivacyPreferences>) => {
      setPreferences((prev) => {
        const updated = {
          ...prev,
          privacy: { ...prev.privacy, ...updates },
          updatedAt: Date.now(),
        };
        saveToStorage(updated);
        setHasUnsavedChanges(true);
        return updated;
      });
    },
    [saveToStorage],
  );

  const pinSession = useCallback(
    (sessionId: string) => {
      setPreferences((prev) => {
        // Don't add duplicates
        if (prev.session.pinnedSessions.includes(sessionId)) {
          return prev;
        }
        const updated = {
          ...prev,
          session: {
            ...prev.session,
            pinnedSessions: [...prev.session.pinnedSessions, sessionId],
          },
          updatedAt: Date.now(),
        };
        saveToStorage(updated);
        setHasUnsavedChanges(true);
        return updated;
      });
    },
    [saveToStorage],
  );

  const unpinSession = useCallback(
    (sessionId: string) => {
      setPreferences((prev) => {
        const updated = {
          ...prev,
          session: {
            ...prev.session,
            pinnedSessions: prev.session.pinnedSessions.filter(
              (id) => id !== sessionId,
            ),
          },
          updatedAt: Date.now(),
        };
        saveToStorage(updated);
        setHasUnsavedChanges(true);
        return updated;
      });
    },
    [saveToStorage],
  );

  const addRecentSession = useCallback(
    (sessionId: string) => {
      setPreferences((prev) => {
        // Remove if already exists (will be added to front)
        const filtered = prev.session.recentSessions.filter(
          (id) => id !== sessionId,
        );
        // Add to front, limit to max
        const recentSessions = [sessionId, ...filtered].slice(
          0,
          prev.session.maxRecentSessions,
        );
        const updated = {
          ...prev,
          session: {
            ...prev.session,
            recentSessions,
          },
          updatedAt: Date.now(),
        };
        saveToStorage(updated);
        setHasUnsavedChanges(true);
        return updated;
      });
    },
    [saveToStorage],
  );

  const resetToDefaults = useCallback(() => {
    setPreferences({
      ...DEFAULT_USER_PREFERENCES,
      updatedAt: Date.now(),
    });
    saveToStorage({ ...DEFAULT_USER_PREFERENCES, updatedAt: Date.now() });
    setHasUnsavedChanges(false);
  }, [saveToStorage]);

  const loadPreferences = useCallback(async () => {
    setIsLoading(true);
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        setPreferences(JSON.parse(stored));
      }
    } catch {
      setError("Failed to load preferences");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const savePreferences = useCallback(async () => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
      setHasUnsavedChanges(false);
    } catch (err) {
      setError(
        `Failed to save preferences: ${err instanceof Error ? err.message : String(err)}`,
      );
    }
  }, [preferences]);

  const syncWithBackend = useCallback(async () => {
    setIsSyncing(true);
    setError(null);
    try {
      // Convert nested frontend format to flat API format
      const apiPrefs = toApiFormat(preferences);

      // Use RTK Query to update preferences on backend
      const result = await store.dispatch(
        api.endpoints.updateUserPreferences.initiate(apiPrefs),
      );

      if ("error" in result) {
        throw new Error(
          typeof result.error === "object" && "message" in result.error
            ? String(result.error.message)
            : "Sync failed",
        );
      }

      // Optionally merge server response back into local state
      // This ensures server-side defaults/validation are respected
      if (result.data) {
        const merged = fromApiFormat(result.data, preferences);
        setPreferences(merged);
        saveToStorage(merged);
      }

      setHasUnsavedChanges(false);
    } catch (err) {
      setError(
        `Failed to sync preferences: ${err instanceof Error ? err.message : String(err)}`,
      );
    } finally {
      setIsSyncing(false);
    }
  }, [preferences, saveToStorage]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // ---------------------------------------------------------------------------
  // Memoized context value
  // ---------------------------------------------------------------------------
  const value = useMemo<PreferencesContextValue>(
    () => ({
      preferences,
      isLoading,
      isInitialized,
      isSyncing,
      error,
      hasUnsavedChanges,
      updatePreferences,
      updateGeneralPreferences,
      updateAccessibilityPreferences,
      updateModelDefaults,
      updateKeyboardShortcut,
      resetKeyboardShortcut,
      updateSessionPreferences,
      updatePrivacyPreferences,
      pinSession,
      unpinSession,
      addRecentSession,
      resetToDefaults,
      loadPreferences,
      savePreferences,
      syncWithBackend,
      clearError,
    }),
    [
      preferences,
      isLoading,
      isInitialized,
      isSyncing,
      error,
      hasUnsavedChanges,
      updatePreferences,
      updateGeneralPreferences,
      updateAccessibilityPreferences,
      updateModelDefaults,
      updateKeyboardShortcut,
      resetKeyboardShortcut,
      updateSessionPreferences,
      updatePrivacyPreferences,
      pinSession,
      unpinSession,
      addRecentSession,
      resetToDefaults,
      loadPreferences,
      savePreferences,
      syncWithBackend,
      clearError,
    ],
  );

  return (
    <PreferencesContext.Provider value={value}>
      {children}
    </PreferencesContext.Provider>
  );
}

// ==============================================================================
// Hooks
// ==============================================================================

/**
 * Hook to access all preferences and actions.
 *
 * @example
 * ```tsx
 * const { preferences, updateGeneralPreferences } = usePreferences();
 *
 * return (
 *   <select
 *     value={preferences.general.theme}
 *     onChange={(e) => updateGeneralPreferences({ theme: e.target.value as ThemeMode })}
 *   >
 *     <option value="light">Light</option>
 *     <option value="dark">Dark</option>
 *     <option value="system">System</option>
 *   </select>
 * );
 * ```
 */
// eslint-disable-next-line react-refresh/only-export-components
export function usePreferences(): PreferencesContextValue {
  return useContext(PreferencesContext);
}

/**
 * Hook to access theme settings with effective theme calculation.
 *
 * @returns Theme state and setter
 *
 * @example
 * ```tsx
 * const { theme, effectiveTheme, setTheme } = useTheme();
 *
 * return (
 *   <button onClick={() => setTheme(effectiveTheme === 'dark' ? 'light' : 'dark')}>
 *     Toggle Theme
 *   </button>
 * );
 * ```
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useTheme() {
  const { preferences, updateGeneralPreferences } = usePreferences();
  const [effectiveTheme, setEffectiveTheme] = useState<"light" | "dark">(
    "light",
  );

  // Calculate effective theme based on system preference
  useEffect(() => {
    const { theme } = preferences.general;

    if (theme === "system") {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      setEffectiveTheme(mediaQuery.matches ? "dark" : "light");

      const handler = (e: MediaQueryListEvent) => {
        setEffectiveTheme(e.matches ? "dark" : "light");
      };
      mediaQuery.addEventListener("change", handler);
      return () => mediaQuery.removeEventListener("change", handler);
    } else {
      setEffectiveTheme(theme);
    }
    // We only want to re-run when theme changes, not on every general preferences update
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preferences.general.theme]);

  const setTheme = useCallback(
    (theme: ThemeMode) => {
      updateGeneralPreferences({ theme });
    },
    [updateGeneralPreferences],
  );

  return {
    theme: preferences.general.theme,
    effectiveTheme,
    setTheme,
  };
}

/**
 * Hook to access accessibility settings with toggle functions.
 *
 * @returns Accessibility state and toggle functions
 *
 * @example
 * ```tsx
 * const { reducedMotion, toggleReducedMotion } = useAccessibility();
 *
 * return (
 *   <label>
 *     <input
 *       type="checkbox"
 *       checked={reducedMotion}
 *       onChange={toggleReducedMotion}
 *     />
 *     Reduce Motion
 *   </label>
 * );
 * ```
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useAccessibility() {
  const { preferences, updateAccessibilityPreferences } = usePreferences();

  const toggleReducedMotion = useCallback(() => {
    updateAccessibilityPreferences({
      reducedMotion: !preferences.accessibility.reducedMotion,
    });
  }, [preferences.accessibility.reducedMotion, updateAccessibilityPreferences]);

  const toggleHighContrast = useCallback(() => {
    updateAccessibilityPreferences({
      highContrast: !preferences.accessibility.highContrast,
    });
  }, [preferences.accessibility.highContrast, updateAccessibilityPreferences]);

  const toggleScreenReaderMode = useCallback(() => {
    updateAccessibilityPreferences({
      screenReaderMode: !preferences.accessibility.screenReaderMode,
    });
  }, [
    preferences.accessibility.screenReaderMode,
    updateAccessibilityPreferences,
  ]);

  return {
    ...preferences.accessibility,
    toggleReducedMotion,
    toggleHighContrast,
    toggleScreenReaderMode,
    setFontSize: (fontSize: "small" | "medium" | "large") =>
      updateAccessibilityPreferences({ fontSize }),
  };
}

/**
 * Hook to get a specific keyboard shortcut by action name.
 *
 * @param action - The action identifier (e.g., "newSession", "sendMessage")
 * @returns Shortcut info including keys and metadata
 *
 * @example
 * ```tsx
 * const { keys, label } = useKeyboardShortcut('newSession');
 *
 * return <span>{label}: {keys}</span>;
 * ```
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useKeyboardShortcut(action: string) {
  const { preferences } = usePreferences();

  // Check for custom override first
  const customKeys = preferences.keyboardShortcuts[action];

  // Find default shortcut
  const defaultShortcut = DEFAULT_KEYBOARD_SHORTCUTS.find(
    (s) => s.action === action,
  );

  return {
    keys: customKeys ?? defaultShortcut?.keys,
    label: defaultShortcut?.label,
    scope: defaultShortcut?.scope,
    customizable: defaultShortcut?.customizable ?? true,
    isCustomized: !!customKeys,
  };
}

export default PreferencesProvider;
