/**
 * Shared test utilities for transforms tests
 *
 * This file contains common async import helpers and cleanup utilities
 * used across the split transform test files.
 */

import { afterEach, vi } from "vitest";

// =============================================================================
// Async Import Helpers
// =============================================================================
// These helpers allow dynamic import of transform functions for test isolation

export const getTransformSnakeToCamel = async () => {
  const { transformSnakeToCamel } = await import("./transforms");
  return transformSnakeToCamel;
};

export const getTransformCamelToSnake = async () => {
  const { transformCamelToSnake } = await import("./transforms");
  return transformCamelToSnake;
};

export const getToCamelCase = async () => {
  const { toCamelCase } = await import("./transforms");
  return toCamelCase;
};

export const getToSnakeCase = async () => {
  const { toSnakeCase } = await import("./transforms");
  return toSnakeCase;
};

export const getTransforms = async () => {
  const { transformSnakeToCamel, transformCamelToSnake } =
    await import("./transforms");
  return { transformSnakeToCamel, transformCamelToSnake };
};

// =============================================================================
// Test Cleanup Setup
// =============================================================================

export const setupTransformTestCleanup = () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });
};
