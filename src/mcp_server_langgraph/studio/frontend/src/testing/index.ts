/**
 * Testing Utilities for Agent Studio Frontend
 *
 * This module provides shared testing utilities, mocks, and helpers
 * to ensure consistent testing patterns across the codebase.
 */

// Storage mocks - use to avoid incomplete mock issues
export {
  createStorageMock,
  createStorageMockFactory,
  createStorageWithValuesMock,
  DEFAULT_MOCK_TOKEN,
  mockStorageUnauthenticated,
  mockStorageWithAuth,
  mockStorageWithValues,
} from "./storageMocks";

export type { ImportOriginal } from "./storageMocks";
