/**
 * Test fixtures for storage tests
 */

export const mockData = {
  simpleObject: { foo: "bar" },
  simpleArray: [1, 2, 3],
  complexObject: {
    users: [{ id: 1, name: "Test" }],
    metadata: { version: 2 },
  },
  aiSuggestions: [
    {
      id: "1",
      type: "completion",
      content: "test suggestion",
      confidence: 0.9,
    },
  ],
  aiSuggestionSimple: [{ id: "1", content: "test" }],
  aiContext: { sessionId: "123", artifactId: "456" },
  aiPreferences: { autoSuggest: true, model: "claude-3" },
  legacyPreferences: { theme: "dark" },
  oldKeyData: { old: true },
  newKeyData: { new: true },
  migrationData: { value: "data" },
};

export const timeConstants = {
  ONE_SECOND: 1000,
  FIVE_SECONDS: 5000,
  TEN_SECONDS: 10000,
  THIRTY_SECONDS: 30000,
  ONE_MINUTE: 60000,
  FIVE_MINUTES: 5 * 60 * 1000,
  TEN_MINUTES: 10 * 60 * 1000,
  TWENTY_FIVE_MINUTES: 25 * 60 * 1000,
  THIRTY_MINUTES: 30 * 60 * 1000,
  THIRTY_FIVE_MINUTES: 35 * 60 * 1000,
  ONE_YEAR: 365 * 24 * 60 * 1000,
};

export function setupQuotaExceededError() {
  const error = new DOMException("Quota exceeded", "QuotaExceededError");
  throw error;
}

export function setupNSErrorQuotaReached() {
  const error = new DOMException("Quota", "NS_ERROR_DOM_QUOTA_REACHED");
  throw error;
}

export function setupGenericError() {
  throw new Error("Unknown error");
}

export function setupStorageError() {
  throw new Error("Storage error");
}

export function setupQuotaExceededErrorForMigration() {
  throw new Error("QuotaExceededError");
}

export function setupLocalStorageDisabledError() {
  throw new Error("localStorage disabled");
}

export function setupStorageQuotaExceededError() {
  throw new Error("Storage quota exceeded");
}
