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

import { devLogger } from "./devLogger";

const logger = devLogger.withPrefix("[Storage]");

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

  // Alert Settings
  ALERT_SOUND_ENABLED: "studio-alert-sound-enabled",

  // Progressive Disclosure (useProgressiveDisclosure hook)
  DISCLOSURE_STATE: "studio-disclosure_state",

  // Nudge System (useNudges hook)
  NUDGE_HISTORY: "studio-nudge_history",

  // Offline Queue (useOfflineQueue hook)
  OFFLINE_QUEUE: "studio-offline_queue",

  // Canvas State
  CANVAS_LAYOUT: "studio-canvas-layout",
  CANVAS_ZOOM: "studio-canvas-zoom",
  CANVAS_POSITION: "studio-canvas-position",

  // AI Features
  AI_SUGGESTIONS_CACHE: "studio-ai-suggestions-cache",
  AI_CONTEXT_HISTORY: "studio-ai-context-history",
  AI_DISMISSED_IDS: "studio-ai-dismissed-ids",
  AI_PREFERENCES: "studio-ai-preferences",

  // Session Sync
  SESSION_SYNC_STATE: "studio-session-sync-state",

  // Cross-Insights Panel
  CROSS_INSIGHTS_DISMISSED: "studio-cross-insights-dismissed",

  // DevTools Panel
  DEVTOOLS_COLLAPSED: "studio-devtools-collapsed",
  DEVTOOLS_HEIGHT: "studio-devtools-height",

  // Chat Input Preferences (Sprint 5.1)
  SUBMIT_ON_ENTER: "studio-submit-on-enter",

  // ActivityBar State (Sprint 4.2)
  ACTIVITY_BAR_COLLAPSED_GROUPS: "activity-bar-collapsed-groups",

  // Model Selection (Sprint 1 - Chat Input Gap Fix)
  SELECTED_MODEL: "studio-selected-model",
  REASONING_EFFORT: "studio-reasoning-effort",
  ENABLE_THINKING: "studio-enable-thinking",
  RECENT_MODELS: "studio-recent-models",
} as const;

// Type for storage keys
export type StorageKey = (typeof STORAGE_KEYS)[keyof typeof STORAGE_KEYS];

/**
 * Check if localStorage is available (SSR-safe)
 */
function isLocalStorageAvailable(): boolean {
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
 * Check if sessionStorage is available (SSR-safe)
 * Uses global sessionStorage for consistency with sessionStore methods
 */
function isSessionStorageAvailable(): boolean {
  try {
    // Check for SSR/non-browser environment
    if (typeof sessionStorage === "undefined") return false;
    const testKey = "__session_test__";
    sessionStorage.setItem(testKey, "1");
    sessionStorage.removeItem(testKey);
    return true;
  } catch {
    return false;
  }
}

/**
 * Wrapper type for values stored with TTL
 */
interface TTLWrapper<T> {
  __value: T;
  __expiresAt: number;
}

/**
 * Check if a value is a TTL wrapper
 */
function isTTLWrapper<T>(value: unknown): value is TTLWrapper<T> {
  return (
    typeof value === "object" &&
    value !== null &&
    "__value" in value &&
    "__expiresAt" in value &&
    typeof (value as TTLWrapper<T>).__expiresAt === "number"
  );
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

    if (!isLocalStorageAvailable()) return defaultValue;

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
      logger.warn(`Failed to get "${key}":`, error);
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
    if (!isLocalStorageAvailable()) return false;

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
        logger.error("Quota exceeded, cannot save:", key);
      } else {
        logger.error(`Failed to set "${key}":`, error);
      }
      return false;
    }
  },

  /**
   * Remove a value from storage
   * @param key - Storage key
   */
  remove(key: string): void {
    if (!isLocalStorageAvailable()) return;

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
      logger.warn(`Failed to remove "${key}":`, error);
    }
  },

  /**
   * Clear all studio-prefixed storage
   * @param includeAuth - Whether to also clear auth tokens
   */
  clear(includeAuth = false): void {
    if (!isLocalStorageAvailable()) return;

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
      logger.warn("Failed to clear storage:", error);
    }
  },

  /**
   * Get all storage keys with studio prefix
   * @returns Array of storage keys
   */
  keys(): string[] {
    if (!isLocalStorageAvailable()) return [];

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
    if (!isLocalStorageAvailable()) return { usedBytes: 0, keyCount: 0 };

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

  /**
   * Set a value with TTL (Time-To-Live) expiration
   * @param key - Storage key
   * @param value - Value to store
   * @param ttlMs - Time to live in milliseconds
   * @returns true if successful, false if failed
   */
  setWithTTL<T>(key: string, value: T, ttlMs: number): boolean {
    const wrapper: TTLWrapper<T> = {
      __value: value,
      __expiresAt: Date.now() + ttlMs,
    };
    return this.set(key, wrapper);
  },

  /**
   * Get a value that was stored with TTL
   * Returns undefined if expired or not found
   * @param key - Storage key
   * @param defaultValue - Default value if expired or not found
   * @returns Value or default
   */
  getWithTTL<T>(key: string, defaultValue?: T): T | undefined {
    if (!isLocalStorageAvailable()) return defaultValue;

    try {
      const prefixedKey = key.startsWith("studio-")
        ? key
        : `${STORAGE_PREFIX}${key}`;
      const item = localStorage.getItem(prefixedKey);

      if (item === null) return defaultValue;

      const parsed = JSON.parse(item);

      if (!isTTLWrapper<T>(parsed)) {
        return defaultValue;
      }

      // Check if expired
      if (Date.now() >= parsed.__expiresAt) {
        // Clean up expired key
        localStorage.removeItem(prefixedKey);
        return defaultValue;
      }

      return parsed.__value;
    } catch {
      return defaultValue;
    }
  },

  /**
   * Migrate a value from a legacy key to a new key
   * @param fromKey - Legacy key (with or without prefix)
   * @param toKey - New key (with or without prefix)
   * @param options - Migration options
   * @returns true if migration was successful, false otherwise
   */
  migrate(
    fromKey: string,
    toKey: string,
    options?: { force?: boolean },
  ): boolean {
    if (!isLocalStorageAvailable()) return false;

    try {
      // Try to get the value from the legacy key
      const legacyValue = localStorage.getItem(fromKey);
      if (legacyValue === null) return false;

      // Check if target key already exists (unless force is true)
      const prefixedToKey = toKey.startsWith("studio-")
        ? toKey
        : `${STORAGE_PREFIX}${toKey}`;
      const existingValue = localStorage.getItem(prefixedToKey);

      if (existingValue !== null && !options?.force) {
        return false;
      }

      // Copy to new key
      localStorage.setItem(prefixedToKey, legacyValue);

      // Remove legacy key
      localStorage.removeItem(fromKey);

      logger.debug(`Migrated "${fromKey}" to "${prefixedToKey}"`);
      return true;
    } catch (error) {
      logger.warn(`Failed to migrate "${fromKey}" to "${toKey}":`, error);
      return false;
    }
  },

  /**
   * Get storage quota information
   * @returns Quota info object with usage statistics
   */
  getQuotaInfo(): QuotaInfo {
    if (!isLocalStorageAvailable()) {
      return {
        usedBytes: 0,
        keyCount: 0,
        estimatedQuota: 0,
        availableBytes: 0,
        percentUsed: 0,
        largestKeys: [],
      };
    }

    // Estimate quota (most browsers allow 5-10MB)
    const ESTIMATED_QUOTA = 5 * 1024 * 1024; // 5MB

    const keyStats: Array<{ key: string; bytes: number }> = [];
    let totalUsedBytes = 0;
    let studioKeyCount = 0;

    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (!key) continue;

      const value = localStorage.getItem(key);
      const bytes = (key.length + (value?.length ?? 0)) * 2; // UTF-16
      totalUsedBytes += bytes;

      if (key.startsWith(STORAGE_PREFIX)) {
        studioKeyCount++;
        keyStats.push({ key, bytes });
      }
    }

    // Sort by size descending and take top 5
    keyStats.sort((a, b) => b.bytes - a.bytes);
    const largestKeys = keyStats.slice(0, 5);

    return {
      usedBytes: totalUsedBytes,
      keyCount: studioKeyCount,
      estimatedQuota: ESTIMATED_QUOTA,
      availableBytes: Math.max(0, ESTIMATED_QUOTA - totalUsedBytes),
      percentUsed: Math.min(100, (totalUsedBytes / ESTIMATED_QUOTA) * 100),
      largestKeys,
    };
  },

  /**
   * Check if storage is near quota limit
   * @param threshold - Percentage threshold (0-1), default 0.9 (90%)
   * @returns true if storage usage exceeds threshold
   */
  isNearQuota(threshold = 0.9): boolean {
    const quota = this.getQuotaInfo();
    return quota.percentUsed / 100 >= threshold;
  },

  /**
   * Clean up expired TTL entries and optionally old entries
   * @param options - Cleanup options
   * @returns Cleanup result with counts
   */
  cleanup(_options?: { maxAge?: number }): CleanupResult {
    if (!isLocalStorageAvailable()) {
      return { removedCount: 0, freedBytes: 0 };
    }

    let removedCount = 0;
    let freedBytes = 0;
    const keysToRemove: string[] = [];

    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (!key?.startsWith(STORAGE_PREFIX)) continue;

      const value = localStorage.getItem(key);
      if (!value) continue;

      try {
        const parsed = JSON.parse(value);

        // Check for expired TTL entries
        if (isTTLWrapper(parsed)) {
          if (Date.now() >= parsed.__expiresAt) {
            keysToRemove.push(key);
            freedBytes += (key.length + value.length) * 2;
          }
        }
      } catch {
        // Not JSON, skip
      }
    }

    // Remove expired entries
    for (const key of keysToRemove) {
      localStorage.removeItem(key);
      removedCount++;
    }

    if (removedCount > 0) {
      logger.debug(
        `Cleaned up ${removedCount} expired entries, freed ${freedBytes} bytes`,
      );
    }

    return { removedCount, freedBytes };
  },
};

// =============================================================================
// Types for Quota and Cleanup
// =============================================================================

export interface QuotaInfo {
  /** Total bytes used by all localStorage */
  usedBytes: number;
  /** Number of studio-prefixed keys */
  keyCount: number;
  /** Estimated quota limit (typically 5MB) */
  estimatedQuota: number;
  /** Estimated available bytes */
  availableBytes: number;
  /** Percentage of quota used (0-100) */
  percentUsed: number;
  /** Largest studio keys by size */
  largestKeys: Array<{ key: string; bytes: number }>;
}

export interface CleanupResult {
  /** Number of entries removed */
  removedCount: number;
  /** Bytes freed */
  freedBytes: number;
}

// Type-safe helpers for common storage operations

/**
 * Get auth token (checks both new and legacy keys)
 */
export function getAuthToken(): string | null {
  if (!isLocalStorageAvailable()) return null;
  // 1) Raw keys written by OAuth/PKCE flow or saveTokensToStorage
  const rawToken =
    localStorage.getItem("access_token") ?? localStorage.getItem("auth_token");
  if (rawToken) return rawToken;

  // 2) Structured storage (studio-auth) used by authSlice
  try {
    const stored = storage.get<{
      state?: { tokens?: { accessToken: string } };
    }>(STORAGE_KEYS.AUTH_STATE, { expectObject: true });
    return stored?.state?.tokens?.accessToken ?? null;
  } catch {
    return null;
  }
}

/**
 * Set auth tokens
 */
export function setAuthTokens(
  accessToken: string,
  refreshToken?: string,
): void {
  if (!isLocalStorageAvailable()) return;
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
  if (!isLocalStorageAvailable()) return;
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("auth_token");
}

// =============================================================================
// Session Storage Variant
// =============================================================================

/**
 * Session storage interface - same API as storage but uses sessionStorage
 * Data persists only for the browser session (cleared when tab/window closes)
 *
 * Use for:
 * - Temporary form data
 * - Single-session caches
 * - Navigation state that shouldn't persist
 */
export const sessionStore = {
  /**
   * Get a value from session storage
   * @param key - Storage key (with or without prefix)
   * @param defaultValue - Default value if not found
   * @returns Parsed value or default
   */
  get<T>(key: string, defaultValue?: T): T | undefined {
    if (!isSessionStorageAvailable()) return defaultValue;

    try {
      const prefixedKey = key.startsWith("studio-")
        ? key
        : `${STORAGE_PREFIX}${key}`;
      const item = sessionStorage.getItem(prefixedKey);

      if (item === null) return defaultValue;

      try {
        return JSON.parse(item) as T;
      } catch {
        return item as unknown as T;
      }
    } catch (error) {
      logger.warn(`[Session] Failed to get "${key}":`, error);
      return defaultValue;
    }
  },

  /**
   * Set a value in session storage
   * @param key - Storage key
   * @param value - Value to store
   * @returns true if successful, false if failed
   */
  set<T>(key: string, value: T): boolean {
    if (!isSessionStorageAvailable()) return false;

    try {
      const prefixedKey = key.startsWith("studio-")
        ? key
        : `${STORAGE_PREFIX}${key}`;
      const serialized =
        typeof value === "string" ? value : JSON.stringify(value);
      sessionStorage.setItem(prefixedKey, serialized);
      return true;
    } catch (error) {
      logger.error(`[Session] Failed to set "${key}":`, error);
      return false;
    }
  },

  /**
   * Remove a value from session storage
   * @param key - Storage key
   */
  remove(key: string): void {
    if (!isSessionStorageAvailable()) return;

    try {
      const prefixedKey = key.startsWith("studio-")
        ? key
        : `${STORAGE_PREFIX}${key}`;
      sessionStorage.removeItem(prefixedKey);
    } catch (error) {
      logger.warn(`[Session] Failed to remove "${key}":`, error);
    }
  },

  /**
   * Clear all studio-prefixed session storage
   */
  clear(): void {
    if (!isSessionStorageAvailable()) return;

    try {
      const keysToRemove: string[] = [];

      for (let i = 0; i < sessionStorage.length; i++) {
        const key = sessionStorage.key(i);
        if (key?.startsWith(STORAGE_PREFIX)) {
          keysToRemove.push(key);
        }
      }

      keysToRemove.forEach((key) => sessionStorage.removeItem(key));
    } catch (error) {
      logger.warn("[Session] Failed to clear storage:", error);
    }
  },

  /**
   * Get all session storage keys with studio prefix
   * @returns Array of storage keys
   */
  keys(): string[] {
    if (!isSessionStorageAvailable()) return [];

    const keys: string[] = [];
    for (let i = 0; i < sessionStorage.length; i++) {
      const key = sessionStorage.key(i);
      if (key?.startsWith(STORAGE_PREFIX)) {
        keys.push(key);
      }
    }
    return keys;
  },

  /**
   * Set a value with TTL (Time-To-Live) expiration in session storage
   * @param key - Storage key
   * @param value - Value to store
   * @param ttlMs - Time to live in milliseconds
   * @returns true if successful, false if failed
   */
  setWithTTL<T>(key: string, value: T, ttlMs: number): boolean {
    const wrapper: TTLWrapper<T> = {
      __value: value,
      __expiresAt: Date.now() + ttlMs,
    };
    return this.set(key, wrapper);
  },

  /**
   * Get a value that was stored with TTL from session storage
   * Returns undefined if expired or not found
   * @param key - Storage key
   * @param defaultValue - Default value if expired or not found
   * @returns Value or default
   */
  getWithTTL<T>(key: string, defaultValue?: T): T | undefined {
    if (!isSessionStorageAvailable()) return defaultValue;

    try {
      const prefixedKey = key.startsWith("studio-")
        ? key
        : `${STORAGE_PREFIX}${key}`;
      const item = sessionStorage.getItem(prefixedKey);

      if (item === null) return defaultValue;

      const parsed = JSON.parse(item);

      if (!isTTLWrapper<T>(parsed)) {
        return defaultValue;
      }

      // Check if expired
      if (Date.now() >= parsed.__expiresAt) {
        // Clean up expired key
        sessionStorage.removeItem(prefixedKey);
        return defaultValue;
      }

      return parsed.__value;
    } catch {
      return defaultValue;
    }
  },
};

export default storage;
