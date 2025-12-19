/**
 * Unified Storage Layer for Agent Studio
 *
 * Provides a centralized, type-safe interface for localStorage operations.
 * All storage keys are prefixed with 'studio-' for consistency.
 *
 * Usage:
 *   import { storage } from '@/utils/storage';
 *   storage.set('theme', 'dark');
 *   const theme = storage.get<string>('theme');
 *
 * Benefits:
 * - Consistent key prefixing (studio-)
 * - Type-safe get/set operations
 * - JSON serialization handled automatically
 * - Error handling for quota exceeded
 * - SSR-safe (checks for window)
 */

// Storage key prefix for all Agent Studio data
const STORAGE_PREFIX = "studio-";

// Known storage keys with their types
export const STORAGE_KEYS = {
  // Authentication
  ACCESS_TOKEN: "access_token", // No prefix - legacy key used by auth system
  REFRESH_TOKEN: "refresh_token", // No prefix - legacy key
  AUTH_TOKEN: "auth_token", // No prefix - legacy key
  AUTH_STATE: "studio-auth",

  // UI Preferences
  THEME: "studio-theme",
  SIDEBAR_COLLAPSED: "studio-sidebar-collapsed",
  PREFERENCES: "studio-preferences",
  ACCESSIBILITY: "studio-accessibility",

  // Workspace State
  WORKSPACE: "studio-workspace",

  // Onboarding & Feedback
  ONBOARDING: "studio-onboarding",
  TOUR_COMPLETED: "studio-tour-completed",
  SUS_COMPLETED: "studio-sus-completed",
  SUS_DISMISSED: "studio-sus-dismissed",
  SESSION_COUNT: "studio-session-count",
  FIRST_VISIT: "studio-first-visit",

  // Feature State
  RECENT_COMMANDS: "studio-recent-commands",
  LAST_VISIT: "studio-last-visit",
  PROMPT_TEMPLATES: "studio-prompt-templates",
} as const;

// Type for storage keys
export type StorageKey = (typeof STORAGE_KEYS)[keyof typeof STORAGE_KEYS];

/**
 * Check if localStorage is available (SSR-safe)
 */
function isStorageAvailable(): boolean {
  try {
    if (typeof window === "undefined") return false;
    const testKey = "__storage_test__";
    window.localStorage.setItem(testKey, "1");
    window.localStorage.removeItem(testKey);
    return true;
  } catch {
    return false;
  }
}

/**
 * Unified storage interface
 */
/**
 * Options for storage.get()
 */
export interface StorageGetOptions<T> {
  /** Default value if key not found or validation fails */
  defaultValue?: T;
  /**
   * Validator function to check if parsed value is valid.
   * If provided and returns false, defaultValue is returned.
   */
  validator?: (value: unknown) => value is T;
  /**
   * If true, only return parsed JSON objects (not raw strings).
   * Useful for structured data like preferences.
   */
  expectObject?: boolean;
}

export const storage = {
  /**
   * Get a value from storage
   * @param key - Storage key (with or without prefix)
   * @param defaultValueOrOptions - Default value or options object
   * @returns Parsed value or default
   */
  get<T>(
    key: string,
    defaultValueOrOptions?: T | StorageGetOptions<T>,
  ): T | undefined {
    // Parse options
    const isOptionsObject =
      defaultValueOrOptions !== null &&
      typeof defaultValueOrOptions === "object" &&
      ("defaultValue" in defaultValueOrOptions ||
        "validator" in defaultValueOrOptions ||
        "expectObject" in defaultValueOrOptions);

    const options: StorageGetOptions<T> = isOptionsObject
      ? (defaultValueOrOptions as StorageGetOptions<T>)
      : { defaultValue: defaultValueOrOptions as T | undefined };

    const { defaultValue, validator, expectObject } = options;

    if (!isStorageAvailable()) return defaultValue;

    try {
      const prefixedKey = key.startsWith("studio-")
        ? key
        : `${STORAGE_PREFIX}${key}`;
      const item = localStorage.getItem(prefixedKey);

      // Try non-prefixed if prefixed not found (legacy support)
      const value = item ?? localStorage.getItem(key);

      if (value === null) return defaultValue;

      try {
        const parsed = JSON.parse(value) as T;

        // If expectObject is true, verify the result is an object
        if (expectObject && (typeof parsed !== "object" || parsed === null)) {
          return defaultValue;
        }

        // If validator is provided, use it to validate
        if (validator && !validator(parsed)) {
          return defaultValue;
        }

        return parsed;
      } catch {
        // JSON parse failed - only return raw string if not expecting object
        if (expectObject) {
          return defaultValue;
        }
        // Return as-is if not valid JSON (e.g., plain strings)
        return value as unknown as T;
      }
    } catch (error) {
      console.warn(`[Storage] Failed to get "${key}":`, error);
      return defaultValue;
    }
  },

  /**
   * Set a value in storage
   * @param key - Storage key
   * @param value - Value to store (will be JSON stringified)
   * @returns true if successful, false if failed
   */
  set<T>(key: string, value: T): boolean {
    if (!isStorageAvailable()) return false;

    try {
      const prefixedKey = key.startsWith("studio-")
        ? key
        : `${STORAGE_PREFIX}${key}`;
      const serialized =
        typeof value === "string" ? value : JSON.stringify(value);
      localStorage.setItem(prefixedKey, serialized);
      return true;
    } catch (error) {
      // Handle quota exceeded
      if (
        error instanceof DOMException &&
        (error.code === 22 ||
          error.code === 1014 ||
          error.name === "QuotaExceededError" ||
          error.name === "NS_ERROR_DOM_QUOTA_REACHED")
      ) {
        console.error("[Storage] Quota exceeded, cannot save:", key);
      } else {
        console.error(`[Storage] Failed to set "${key}":`, error);
      }
      return false;
    }
  },

  /**
   * Remove a value from storage
   * @param key - Storage key
   */
  remove(key: string): void {
    if (!isStorageAvailable()) return;

    try {
      const prefixedKey = key.startsWith("studio-")
        ? key
        : `${STORAGE_PREFIX}${key}`;
      localStorage.removeItem(prefixedKey);
      // Also try removing without prefix (legacy cleanup)
      if (!key.startsWith("studio-")) {
        localStorage.removeItem(key);
      }
    } catch (error) {
      console.warn(`[Storage] Failed to remove "${key}":`, error);
    }
  },

  /**
   * Clear all studio-prefixed storage
   * @param includeAuth - Whether to also clear auth tokens
   */
  clear(includeAuth = false): void {
    if (!isStorageAvailable()) return;

    try {
      const keysToRemove: string[] = [];

      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key?.startsWith(STORAGE_PREFIX)) {
          keysToRemove.push(key);
        }
      }

      keysToRemove.forEach((key) => localStorage.removeItem(key));

      if (includeAuth) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("auth_token");
      }
    } catch (error) {
      console.warn("[Storage] Failed to clear storage:", error);
    }
  },

  /**
   * Get all storage keys with studio prefix
   * @returns Array of storage keys
   */
  keys(): string[] {
    if (!isStorageAvailable()) return [];

    const keys: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key?.startsWith(STORAGE_PREFIX)) {
        keys.push(key);
      }
    }
    return keys;
  },

  /**
   * Get storage usage stats
   * @returns Object with used bytes and key count
   */
  stats(): { usedBytes: number; keyCount: number } {
    if (!isStorageAvailable()) return { usedBytes: 0, keyCount: 0 };

    let usedBytes = 0;
    let keyCount = 0;

    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key?.startsWith(STORAGE_PREFIX)) {
        const value = localStorage.getItem(key);
        usedBytes += (key.length + (value?.length ?? 0)) * 2; // UTF-16
        keyCount++;
      }
    }

    return { usedBytes, keyCount };
  },
};

// Type-safe helpers for common storage operations

/**
 * Get auth token (checks both new and legacy keys)
 */
export function getAuthToken(): string | null {
  if (!isStorageAvailable()) return null;
  return (
    localStorage.getItem("access_token") ?? localStorage.getItem("auth_token")
  );
}

/**
 * Set auth tokens
 */
export function setAuthTokens(
  accessToken: string,
  refreshToken?: string,
): void {
  if (!isStorageAvailable()) return;
  localStorage.setItem("access_token", accessToken);
  localStorage.setItem("auth_token", accessToken); // Legacy support
  if (refreshToken) {
    localStorage.setItem("refresh_token", refreshToken);
  }
}

/**
 * Clear auth tokens
 */
export function clearAuthTokens(): void {
  if (!isStorageAvailable()) return;
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("auth_token");
}

export default storage;
