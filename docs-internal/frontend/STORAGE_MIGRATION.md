# localStorage Migration Guide

## Overview

This document describes the unified storage layer implemented for the MCP Server LangGraph Studio frontend. All localStorage operations should go through the centralized storage utility at `src/utils/storage.ts`.

## Why This Migration?

1. **Consistency**: All storage keys use the `studio-` prefix for namespacing
2. **Type Safety**: Generic `storage.get<T>()` provides type inference
3. **Validation**: `expectObject` and `validator` options prevent bugs like string-spreading
4. **Error Handling**: Automatic JSON parsing with graceful fallbacks
5. **SSR Safety**: All operations check for `window` availability
6. **Maintainability**: Single source of truth for storage operations

## Quick Reference

### Import

```typescript
import { storage, STORAGE_KEYS } from "../utils/storage";
import { getAuthToken, setAuthTokens, clearAuthTokens } from "../utils/storage";
```

### Basic Operations

```typescript
// Get a value (returns T | undefined)
const theme = storage.get<string>(STORAGE_KEYS.THEME);

// Get with default value
const theme = storage.get<string>(STORAGE_KEYS.THEME, "dark");

// Get structured object with validation
const prefs = storage.get<UserPreferences>(STORAGE_KEYS.PREFERENCES, {
  expectObject: true,
  validator: isValidPreferences,
});

// Set a value (auto-JSON stringified)
storage.set(STORAGE_KEYS.THEME, "dark");
storage.set(STORAGE_KEYS.PREFERENCES, { fontSize: "medium" });

// Remove a value
storage.remove(STORAGE_KEYS.THEME);

// List all studio-* keys
const keys = storage.keys();

// Get storage stats
const { usedBytes, keyCount } = storage.stats();

// Clear all studio-* storage
storage.clear();
storage.clear(true); // Also clears auth tokens
```

### Auth Token Operations

```typescript
// Get current auth token (checks access_token, falls back to auth_token)
const token = getAuthToken();

// Set auth tokens (sets both access_token and refresh_token)
setAuthTokens(accessToken, refreshToken);

// Clear all auth tokens
clearAuthTokens();
```

## STORAGE_KEYS Registry

All storage keys should be registered in `STORAGE_KEYS`:

```typescript
export const STORAGE_KEYS = {
  // Authentication
  ACCESS_TOKEN: "access_token",       // Legacy - no prefix
  REFRESH_TOKEN: "refresh_token",     // Legacy - no prefix
  AUTH_TOKEN: "auth_token",           // Legacy - no prefix
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

  // Progressive Disclosure
  DISCLOSURE_STATE: "studio-disclosure_state",

  // Nudge System
  NUDGE_HISTORY: "studio-nudge_history",

  // Offline Queue
  OFFLINE_QUEUE: "studio-offline_queue",

  // Canvas State
  CANVAS_LAYOUT: "studio-canvas-layout",
  CANVAS_ZOOM: "studio-canvas-zoom",
  CANVAS_POSITION: "studio-canvas-position",

  // AI Features (with TTL support)
  AI_SUGGESTIONS_CACHE: "studio-ai-suggestions-cache",
  AI_CONTEXT_HISTORY: "studio-ai-context-history",
  AI_PREFERENCES: "studio-ai-preferences",

  // Session Sync
  SESSION_SYNC_STATE: "studio-session-sync-state",
} as const;
```

## ESLint Enforcement

The codebase uses `no-restricted-globals` to prevent direct localStorage usage:

```javascript
// eslint.config.js
'no-restricted-globals': [
  'error',
  {
    name: 'localStorage',
    message: 'Use the storage utility from utils/storage.ts instead.',
  },
  {
    name: 'sessionStorage',
    message: 'Use the storage utility from utils/storage.ts instead.',
  },
],
```

### Exceptions

1. **`utils/storage.ts`** - The storage utility itself
2. **Test files (`*.test.ts(x)`, `*.spec.ts(x)`)** - For mocking localStorage

## Migration Patterns

### Pattern 1: Simple Get

```typescript
// BEFORE
const value = localStorage.getItem("studio-theme");

// AFTER
const value = storage.get<string>(STORAGE_KEYS.THEME);
```

### Pattern 2: JSON Get with Error Handling

```typescript
// BEFORE
const stored = localStorage.getItem("studio-preferences");
if (stored) {
  try {
    const data = JSON.parse(stored);
    // use data
  } catch {
    // handle error
  }
}

// AFTER
const data = storage.get<PreferencesType>(STORAGE_KEYS.PREFERENCES, {
  expectObject: true,
});
// Returns undefined if not found or invalid JSON
```

### Pattern 3: Set with JSON

```typescript
// BEFORE
localStorage.setItem("studio-preferences", JSON.stringify(prefs));

// AFTER
storage.set(STORAGE_KEYS.PREFERENCES, prefs);
```

### Pattern 4: Auth Token Access

```typescript
// BEFORE
const token = localStorage.getItem("access_token") || localStorage.getItem("auth_token");

// AFTER
const token = getAuthToken();
```

### Pattern 5: Auth Token Cleanup

```typescript
// BEFORE
localStorage.removeItem("access_token");
localStorage.removeItem("refresh_token");
localStorage.removeItem("auth_token");

// AFTER
clearAuthTokens();
```

### Pattern 6: Iterating Keys

```typescript
// BEFORE
for (let i = 0; i < localStorage.length; i++) {
  const key = localStorage.key(i);
  if (key?.startsWith("studio-")) {
    // ...
  }
}

// AFTER
for (const key of storage.keys()) {
  // All keys already have studio- prefix
}
```

## Validation Options

The `storage.get()` function supports validation options:

```typescript
interface StorageGetOptions<T> {
  /** Default value if key not found or validation fails */
  defaultValue?: T;

  /** Validator function to check if parsed value is valid */
  validator?: (value: unknown) => value is T;

  /** If true, only return parsed JSON objects (not raw strings) */
  expectObject?: boolean;
}
```

### Example: Object with Validator

```typescript
function isValidPreferences(value: unknown): value is UserPreferences {
  return (
    typeof value === "object" &&
    value !== null &&
    "theme" in value &&
    typeof (value as { theme: unknown }).theme === "string"
  );
}

const prefs = storage.get<UserPreferences>(STORAGE_KEYS.PREFERENCES, {
  expectObject: true,
  validator: isValidPreferences,
  defaultValue: DEFAULT_PREFERENCES,
});
```

## Scripts

### Check Storage Usage

```bash
# Run from frontend directory
./scripts/check-storage-usage.sh report   # Full report
./scripts/check-storage-usage.sh check    # CI-friendly check
./scripts/check-storage-usage.sh migrate  # Migration suggestions
./scripts/check-storage-usage.sh stats    # Usage statistics
```

## Adding New Storage Keys

1. Add the key to `STORAGE_KEYS` in `utils/storage.ts`
2. Use the `studio-` prefix for consistency
3. Document the key's purpose with a comment
4. Use the appropriate storage functions

```typescript
export const STORAGE_KEYS = {
  // ... existing keys ...

  // My Feature
  MY_FEATURE_STATE: "studio-my-feature-state",
} as const;
```

## Testing

When testing components that use storage:

```typescript
// Mock localStorage in test setup
const mockStorage: Record<string, string> = {};
const localStorageMock = {
  getItem: vi.fn((key: string) => mockStorage[key] ?? null),
  setItem: vi.fn((key: string, value: string) => {
    mockStorage[key] = value;
  }),
  removeItem: vi.fn((key: string) => {
    delete mockStorage[key];
  }),
  clear: vi.fn(() => {
    Object.keys(mockStorage).forEach((key) => delete mockStorage[key]);
  }),
  get length() {
    return Object.keys(mockStorage).length;
  },
  key: vi.fn((index: number) => Object.keys(mockStorage)[index] ?? null),
};

beforeEach(() => {
  vi.stubGlobal("localStorage", localStorageMock);
  localStorageMock.clear();
  vi.clearAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
});
```

## TTL Support

The storage utility supports time-to-live (TTL) for cached values:

```typescript
// Set a value with TTL (5 minutes)
storage.setWithTTL(STORAGE_KEYS.AI_SUGGESTIONS_CACHE, suggestions, 5 * 60 * 1000);

// Get a value with TTL (returns undefined if expired)
const cached = storage.getWithTTL<Suggestion[]>(STORAGE_KEYS.AI_SUGGESTIONS_CACHE);
```

TTL values are stored with a wrapper object containing `value` and `expiresAt` fields.

## Session Storage

For per-session data that should be cleared when the browser tab closes:

```typescript
import { sessionStore, STORAGE_KEYS } from "../utils/storage";

// Store session-specific context
sessionStore.set(STORAGE_KEYS.AI_CONTEXT_HISTORY, { sessionId, artifactId });

// Retrieve session data
const context = sessionStore.get<AIContext>(STORAGE_KEYS.AI_CONTEXT_HISTORY);

// Remove session data
sessionStore.remove(STORAGE_KEYS.AI_CONTEXT_HISTORY);
```

## Legacy Key Migration

When migrating from old key formats to new prefixed keys:

```typescript
// Migrate a value from legacy key to new key
const success = storage.migrate("old_preferences", STORAGE_KEYS.PREFERENCES);
// success === true if migration occurred

// Force overwrite if target already exists
storage.migrate("old_preferences", STORAGE_KEYS.PREFERENCES, { force: true });
```

The migrate function:
- Copies the value from the old key to the new key
- Removes the old key after successful migration
- Returns `false` if the old key doesn't exist
- Won't overwrite existing values unless `force: true` is set

## Quota Monitoring

Monitor localStorage usage to prevent quota exceeded errors:

```typescript
// Get storage quota information
const quotaInfo = storage.getQuotaInfo();
// {
//   usedBytes: 45000,
//   keyCount: 12,
//   estimatedQuota: 5242880,  // 5MB (typical browser limit)
//   availableBytes: 5197880,
//   percentUsed: 0.86,
//   largestKeys: [
//     { key: "studio-cache", bytes: 15000 },
//     { key: "studio-preferences", bytes: 8000 }
//   ]
// }

// Check if near quota (default 90% threshold)
if (storage.isNearQuota()) {
  console.warn("Storage nearly full, consider cleanup");
}

// Custom threshold (80%)
if (storage.isNearQuota(0.8)) {
  // ...
}
```

## Cleanup

Remove expired TTL entries and free up space:

```typescript
// Clean up expired TTL entries
const result = storage.cleanup();
// { removedCount: 3, freedBytes: 2500 }

// Clean up entries older than a specific age (24 hours)
const result = storage.cleanup({ maxAge: 24 * 60 * 60 * 1000 });
```

## AI Suggestions Caching (useAISuggestionsCache)

For caching AI suggestions with context tracking:

```typescript
import { useAISuggestionsCache } from "../hooks";

const {
  suggestions,
  context,
  isStale,
  cacheSuggestions,
  invalidateCache,
  setContext,
  getCacheAge,
} = useAISuggestionsCache({
  ttlMs: 5 * 60 * 1000, // 5 minutes (default)
  invalidateOnContextChange: true, // Auto-clear cache on context change
});

// Cache new suggestions
cacheSuggestions(fetchedSuggestions);

// Track context (auto-invalidates when changed)
setContext({ sessionId: "session-123", artifactId: "artifact-456" });

// Check cache age
const ageMs = getCacheAge();
```

## AI Suggestions Fetching (useAISuggestionsFetch)

Higher-level hook combining fetching and caching:

```typescript
import { useAISuggestionsFetch } from "../hooks";

const {
  suggestions,
  isLoading,
  error,
  isStale,
  acceptSuggestion,
  dismissSuggestion,
  clearSuggestions,
  refresh,
  getCacheAge,
} = useAISuggestionsFetch({
  artifactId: selectedArtifactId,
  sessionId: currentSessionId,
  enabled: aiSuggestionsEnabled,
  debounceMs: 500, // Debounce fetch requests
  ttlMs: 5 * 60 * 1000, // Cache TTL
});

// Accept or dismiss suggestions
acceptSuggestion("sugg-1");
dismissSuggestion("sugg-2");

// Force refresh (bypass cache)
refresh();
```

## Migration Status

- [x] ESLint rule added to prevent direct localStorage usage
- [x] Storage utility enhanced with validation options
- [x] Auth token helpers created (getAuthToken, setAuthTokens, clearAuthTokens)
- [x] All production files migrated to use storage utility
- [x] Test files updated for new storage key prefixes
- [x] Migration script created for ongoing maintenance
- [x] TTL support added (setWithTTL, getWithTTL)
- [x] Session storage wrapper added (sessionStore)
- [x] Legacy key migration utility added (storage.migrate)
- [x] Quota monitoring added (getQuotaInfo, isNearQuota)
- [x] Cleanup utility added (storage.cleanup)
- [x] AI suggestions cache hook created (useAISuggestionsCache)
- [x] AI suggestions fetch hook created (useAISuggestionsFetch)
