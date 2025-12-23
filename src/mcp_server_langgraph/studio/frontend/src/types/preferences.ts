/**
 * User Preferences Types
 *
 * Type definitions for user preferences including:
 * - Theme settings
 * - Accessibility options
 * - Model defaults
 * - Keyboard shortcuts
 * - Privacy settings
 *
 * Based on UX analysis of Gemini CLI, OpenAI Codex, and Claude Code.
 */

// ==============================================================================
// Theme Types
// ==============================================================================

/** Theme options */
export type ThemeMode = "light" | "dark" | "system";

/** Font size options */
export type FontSize = "small" | "medium" | "large";

// ==============================================================================
// Accessibility Types
// ==============================================================================

/** Accessibility preferences */
export interface AccessibilityPreferences {
  /** Enable screen reader optimized mode */
  screenReaderMode: boolean;
  /** Reduce motion for animations */
  reducedMotion: boolean;
  /** Enable high contrast mode */
  highContrast: boolean;
  /** Font size adjustment */
  fontSize: FontSize;
  /** Announce streaming updates via aria-live */
  announceStreamingUpdates: boolean;
}

/** Default accessibility preferences */
export const DEFAULT_ACCESSIBILITY_PREFERENCES: AccessibilityPreferences = {
  screenReaderMode: false,
  reducedMotion: false,
  highContrast: false,
  fontSize: "medium",
  announceStreamingUpdates: false,
};

// ==============================================================================
// Model Defaults Types
// ==============================================================================

/** Model default preferences */
export interface ModelDefaultPreferences {
  /** Default LLM model name */
  defaultModel: string | null;
  /** Default temperature (0-1) */
  defaultTemperature: number;
  /** Default max tokens */
  defaultMaxTokens: number;
  /** Default reasoning effort for thinking models */
  defaultReasoningEffort: "low" | "medium" | "high";
}

/** Default model preferences */
export const DEFAULT_MODEL_PREFERENCES: ModelDefaultPreferences = {
  defaultModel: null,
  defaultTemperature: 0.7,
  defaultMaxTokens: 4096,
  defaultReasoningEffort: "medium",
};

// ==============================================================================
// General Preferences Types
// ==============================================================================

/** General preferences */
export interface GeneralPreferences {
  /** UI theme mode */
  theme: ThemeMode;
  /** User interface language */
  language: string;
  /** Auto-scroll to new messages */
  autoScroll: boolean;
  /** Enable desktop notifications */
  notificationsEnabled: boolean;
  /** Show keyboard shortcuts hints */
  showShortcutHints: boolean;
}

/** Default general preferences */
export const DEFAULT_GENERAL_PREFERENCES: GeneralPreferences = {
  theme: "system",
  language: "en",
  autoScroll: true,
  notificationsEnabled: true,
  showShortcutHints: true,
};

// ==============================================================================
// Keyboard Shortcuts Types
// ==============================================================================

/** Keyboard shortcut mapping */
export interface KeyboardShortcut {
  /** Unique action identifier */
  action: string;
  /** Display label for the action */
  label: string;
  /** Key combination (e.g., "Cmd+K", "Ctrl+Shift+P") */
  keys: string;
  /** Scope where shortcut is active */
  scope: "global" | "chat" | "workflow" | "settings" | "devtools";
  /** Whether the shortcut is customizable */
  customizable: boolean;
}

/** Default keyboard shortcuts */
export const DEFAULT_KEYBOARD_SHORTCUTS: KeyboardShortcut[] = [
  {
    action: "newSession",
    label: "New Session",
    keys: "Cmd+N",
    scope: "global",
    customizable: true,
  },
  {
    action: "searchSessions",
    label: "Search Sessions",
    keys: "Cmd+K",
    scope: "global",
    customizable: true,
  },
  {
    action: "toggleRightSidebar",
    label: "Toggle Right Sidebar",
    keys: "Cmd+B",
    scope: "global",
    customizable: true,
  },
  {
    action: "toggleBottomPanel",
    label: "Toggle Bottom Panel",
    keys: "Cmd+J",
    scope: "global",
    customizable: true,
  },
  {
    action: "sendMessage",
    label: "Send Message",
    keys: "Cmd+Enter",
    scope: "chat",
    customizable: true,
  },
  {
    action: "showShortcuts",
    label: "Show Shortcuts",
    keys: "Cmd+/",
    scope: "global",
    customizable: false,
  },
  {
    action: "openCommandPalette",
    label: "Command Palette",
    keys: "Cmd+P",
    scope: "global",
    customizable: true,
  },
  {
    action: "cancelOrClose",
    label: "Cancel / Close",
    keys: "Escape",
    scope: "global",
    customizable: false,
  },
  // DevTools shortcuts
  {
    action: "toggleDevTools",
    label: "Toggle DevTools",
    keys: "Cmd+Shift+I",
    scope: "global",
    customizable: true,
  },
  {
    action: "focusDevToolsConsole",
    label: "Focus DevTools Console",
    keys: "Cmd+Shift+C",
    scope: "global",
    customizable: true,
  },
  {
    action: "clearDevToolsConsole",
    label: "Clear DevTools Console",
    keys: "Cmd+K",
    scope: "devtools",
    customizable: true,
  },
  {
    action: "devToolsNextTab",
    label: "DevTools Next Tab",
    keys: "Cmd+]",
    scope: "devtools",
    customizable: true,
  },
  {
    action: "devToolsPrevTab",
    label: "DevTools Previous Tab",
    keys: "Cmd+[",
    scope: "devtools",
    customizable: true,
  },
];

// ==============================================================================
// Session Preferences Types
// ==============================================================================

/** Session-related preferences */
export interface SessionPreferences {
  /** List of pinned session IDs */
  pinnedSessions: string[];
  /** Recently accessed session IDs (for quick access) */
  recentSessions: string[];
  /** Maximum recent sessions to track */
  maxRecentSessions: number;
}

/** Default session preferences */
export const DEFAULT_SESSION_PREFERENCES: SessionPreferences = {
  pinnedSessions: [],
  recentSessions: [],
  maxRecentSessions: 10,
};

// ==============================================================================
// Privacy Preferences Types
// ==============================================================================

/** Privacy preferences */
export interface PrivacyPreferences {
  /** Allow usage analytics */
  analyticsEnabled: boolean;
  /** Allow error reporting */
  errorReportingEnabled: boolean;
  /** Store conversation history locally */
  storeHistoryLocally: boolean;
}

/** Default privacy preferences */
export const DEFAULT_PRIVACY_PREFERENCES: PrivacyPreferences = {
  analyticsEnabled: true,
  errorReportingEnabled: true,
  storeHistoryLocally: true,
};

// ==============================================================================
// HITL (Human-in-the-Loop) Preferences Types
// ==============================================================================

/** Task-specific HITL override */
export interface HITLTaskOverride {
  /** Whether HITL is enabled for this task type */
  enabled: boolean;
  /** Custom confidence threshold for this task type */
  threshold: number;
}

/** HITL preferences for agent approval workflows */
export interface HITLPreferences {
  /** Whether HITL is enabled globally */
  enabled: boolean;
  /** Confidence threshold below which approval is required (0-1) */
  confidenceThreshold: number;
  /** Confidence threshold above which auto-approval is allowed (0-1) */
  autoApproveThreshold: number;
  /** Whether to send push notifications for approval requests */
  pushNotificationsEnabled: boolean;
  /** Whether to play sound for approval requests */
  soundEnabled: boolean;
  /** Per-task-type overrides for HITL settings */
  taskOverrides: Record<string, HITLTaskOverride>;
}

/** Default HITL preferences */
export const DEFAULT_HITL_PREFERENCES: HITLPreferences = {
  enabled: true,
  confidenceThreshold: 0.7,
  autoApproveThreshold: 0.9,
  pushNotificationsEnabled: true,
  soundEnabled: false,
  taskOverrides: {},
};

// ==============================================================================
// Combined User Preferences
// ==============================================================================

/** Complete user preferences */
export interface UserPreferences {
  /** General UI preferences */
  general: GeneralPreferences;
  /** Accessibility preferences */
  accessibility: AccessibilityPreferences;
  /** Model default preferences */
  modelDefaults: ModelDefaultPreferences;
  /** Custom keyboard shortcuts (overrides defaults) */
  keyboardShortcuts: Record<string, string>;
  /** Session-related preferences */
  session: SessionPreferences;
  /** Privacy preferences */
  privacy: PrivacyPreferences;
  /** HITL (Human-in-the-Loop) preferences */
  hitl: HITLPreferences;
  /** Preference version for migrations */
  version: number;
  /** Last updated timestamp */
  updatedAt: number;
}

/** Default user preferences */
export const DEFAULT_USER_PREFERENCES: UserPreferences = {
  general: DEFAULT_GENERAL_PREFERENCES,
  accessibility: DEFAULT_ACCESSIBILITY_PREFERENCES,
  modelDefaults: DEFAULT_MODEL_PREFERENCES,
  keyboardShortcuts: {},
  session: DEFAULT_SESSION_PREFERENCES,
  privacy: DEFAULT_PRIVACY_PREFERENCES,
  hitl: DEFAULT_HITL_PREFERENCES,
  version: 1,
  updatedAt: Date.now(),
};

// ==============================================================================
// Preferences Store Types
// ==============================================================================

/** Preferences store state */
export interface PreferencesState {
  /** Current user preferences */
  preferences: UserPreferences;
  /** Whether preferences are loading */
  isLoading: boolean;
  /** Whether preferences have been loaded from storage */
  isInitialized: boolean;
  /** Whether preferences are syncing to backend */
  isSyncing: boolean;
  /** Error message if any */
  error: string | null;
  /** Whether there are unsaved changes */
  hasUnsavedChanges: boolean;
}

/** Preferences store actions */
export interface PreferencesActions {
  /** Update a single preference section */
  updatePreferences: (updates: Partial<UserPreferences>) => void;
  /** Update general preferences */
  updateGeneralPreferences: (updates: Partial<GeneralPreferences>) => void;
  /** Update accessibility preferences */
  updateAccessibilityPreferences: (
    updates: Partial<AccessibilityPreferences>,
  ) => void;
  /** Update model default preferences */
  updateModelDefaults: (updates: Partial<ModelDefaultPreferences>) => void;
  /** Update a keyboard shortcut */
  updateKeyboardShortcut: (action: string, keys: string) => void;
  /** Reset a keyboard shortcut to default */
  resetKeyboardShortcut: (action: string) => void;
  /** Update session preferences */
  updateSessionPreferences: (updates: Partial<SessionPreferences>) => void;
  /** Update privacy preferences */
  updatePrivacyPreferences: (updates: Partial<PrivacyPreferences>) => void;
  /** Update HITL preferences */
  updateHITLPreferences: (updates: Partial<HITLPreferences>) => void;
  /** Pin a session */
  pinSession: (sessionId: string) => void;
  /** Unpin a session */
  unpinSession: (sessionId: string) => void;
  /** Add a session to recents */
  addRecentSession: (sessionId: string) => void;
  /** Reset all preferences to defaults */
  resetToDefaults: () => void;
  /** Load preferences from storage */
  loadPreferences: () => Promise<void>;
  /** Save preferences to storage */
  savePreferences: () => Promise<void>;
  /** Sync preferences with backend */
  syncWithBackend: () => Promise<void>;
  /** Clear error */
  clearError: () => void;
}

/** Combined preferences store type */
export type PreferencesStore = PreferencesState & PreferencesActions;

// ==============================================================================
// API Types (for backend sync)
// ==============================================================================

/** Preferences API request/response format (snake_case for backend) */
export interface PreferencesApiData {
  theme: ThemeMode;
  language: string;
  auto_scroll: boolean;
  reduced_motion: boolean;
  high_contrast: boolean;
  screen_reader_mode: boolean;
  font_size: FontSize;
  default_model: string | null;
  default_temperature: number;
  default_max_tokens: number;
  keyboard_shortcuts: Record<string, string>;
  pinned_sessions: string[];
  notifications_enabled: boolean;
}

/** Convert UserPreferences to API format */
export function toApiFormat(preferences: UserPreferences): PreferencesApiData {
  return {
    theme: preferences.general.theme,
    language: preferences.general.language,
    auto_scroll: preferences.general.autoScroll,
    reduced_motion: preferences.accessibility.reducedMotion,
    high_contrast: preferences.accessibility.highContrast,
    screen_reader_mode: preferences.accessibility.screenReaderMode,
    font_size: preferences.accessibility.fontSize,
    default_model: preferences.modelDefaults.defaultModel,
    default_temperature: preferences.modelDefaults.defaultTemperature,
    default_max_tokens: preferences.modelDefaults.defaultMaxTokens,
    keyboard_shortcuts: preferences.keyboardShortcuts,
    pinned_sessions: preferences.session.pinnedSessions,
    notifications_enabled: preferences.general.notificationsEnabled,
  };
}

/** Convert API format to UserPreferences */
export function fromApiFormat(
  data: PreferencesApiData,
  existing: UserPreferences = DEFAULT_USER_PREFERENCES,
): UserPreferences {
  return {
    ...existing,
    general: {
      ...existing.general,
      theme: data.theme,
      language: data.language,
      autoScroll: data.auto_scroll,
      notificationsEnabled: data.notifications_enabled,
    },
    accessibility: {
      ...existing.accessibility,
      reducedMotion: data.reduced_motion,
      highContrast: data.high_contrast,
      screenReaderMode: data.screen_reader_mode,
      fontSize: data.font_size,
    },
    modelDefaults: {
      ...existing.modelDefaults,
      defaultModel: data.default_model,
      defaultTemperature: data.default_temperature,
      defaultMaxTokens: data.default_max_tokens,
    },
    keyboardShortcuts: data.keyboard_shortcuts,
    session: {
      ...existing.session,
      pinnedSessions: data.pinned_sessions,
    },
    updatedAt: Date.now(),
  };
}
