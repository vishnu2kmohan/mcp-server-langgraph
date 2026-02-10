/**
 * UnifiedMessageList Test Fixtures
 *
 * Shared mock state objects and test data factories for UnifiedMessageList shards.
 */
import { vi } from "vitest";
import type { ChatMessage } from "../../types/session";

// =============================================================================
// Mock clipboard
// =============================================================================
export const mockClipboard = {
  writeText: vi.fn().mockResolvedValue(undefined),
};

// =============================================================================
// Mock message factory
// =============================================================================
export const createMockMessage = (
  overrides: Partial<ChatMessage> = {},
): ChatMessage => ({
  id: `msg-${Math.random().toString(36).slice(2, 11)}`,
  role: "user",
  content: "Hello, world!",
  timestamp: Date.now(),
  ...overrides,
});
