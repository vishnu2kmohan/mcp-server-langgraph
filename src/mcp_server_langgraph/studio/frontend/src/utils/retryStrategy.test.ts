/**
 * Retry Strategy Tests
 *
 * TDD - RED Phase: Tests written first to define expected behavior
 *
 * Tests the exponential backoff retry strategy.
 */

import { describe, it, expect } from "vitest";
import {
  calculateBackoff,
  shouldRetry,
  getRetryConfig,
  DEFAULT_RETRY_CONFIG,
  type RetryConfig,
  type RetryContext,
} from "./retryStrategy";
import type { ClassifiedError } from "../errors/ErrorTypes";

describe("retryStrategy", () => {
  describe("DEFAULT_RETRY_CONFIG", () => {
    it("should have sensible default values", () => {
      expect(DEFAULT_RETRY_CONFIG.maxRetries).toBe(3);
      expect(DEFAULT_RETRY_CONFIG.baseDelayMs).toBe(1000);
      expect(DEFAULT_RETRY_CONFIG.maxDelayMs).toBe(16000);
      expect(DEFAULT_RETRY_CONFIG.backoffMultiplier).toBe(2);
      expect(DEFAULT_RETRY_CONFIG.jitterFactor).toBeGreaterThanOrEqual(0);
      expect(DEFAULT_RETRY_CONFIG.jitterFactor).toBeLessThanOrEqual(1);
    });
  });

  describe("calculateBackoff", () => {
    it("should calculate delay for first retry (attempt 0)", () => {
      const delay = calculateBackoff(0, {
        ...DEFAULT_RETRY_CONFIG,
        jitterFactor: 0,
      });
      expect(delay).toBe(1000); // 1000 * 2^0 = 1000
    });

    it("should calculate delay for second retry (attempt 1)", () => {
      const delay = calculateBackoff(1, {
        ...DEFAULT_RETRY_CONFIG,
        jitterFactor: 0,
      });
      expect(delay).toBe(2000); // 1000 * 2^1 = 2000
    });

    it("should calculate delay for third retry (attempt 2)", () => {
      const delay = calculateBackoff(2, {
        ...DEFAULT_RETRY_CONFIG,
        jitterFactor: 0,
      });
      expect(delay).toBe(4000); // 1000 * 2^2 = 4000
    });

    it("should calculate delay for fourth retry (attempt 3)", () => {
      const delay = calculateBackoff(3, {
        ...DEFAULT_RETRY_CONFIG,
        jitterFactor: 0,
      });
      expect(delay).toBe(8000); // 1000 * 2^3 = 8000
    });

    it("should cap delay at maxDelayMs", () => {
      const delay = calculateBackoff(10, {
        ...DEFAULT_RETRY_CONFIG,
        jitterFactor: 0,
      });
      expect(delay).toBe(16000); // capped at maxDelayMs
    });

    it("should add jitter when jitterFactor > 0", () => {
      // Run multiple times to check jitter variance
      const delays = new Set<number>();
      for (let i = 0; i < 10; i++) {
        delays.add(
          calculateBackoff(1, { ...DEFAULT_RETRY_CONFIG, jitterFactor: 0.2 }),
        );
      }
      // With jitter, we should get varying delays
      // Jitter range: 2000 * (1 - 0.2) to 2000 * (1 + 0.2) = 1600 to 2400
      // Note: Random might produce same values, so just check reasonable range
      const allDelays = Array.from(delays);
      allDelays.forEach((d) => {
        expect(d).toBeGreaterThanOrEqual(1600);
        expect(d).toBeLessThanOrEqual(2400);
      });
    });

    it("should use custom baseDelayMs", () => {
      const delay = calculateBackoff(0, {
        ...DEFAULT_RETRY_CONFIG,
        baseDelayMs: 500,
        jitterFactor: 0,
      });
      expect(delay).toBe(500);
    });

    it("should use custom backoffMultiplier", () => {
      const delay = calculateBackoff(2, {
        ...DEFAULT_RETRY_CONFIG,
        baseDelayMs: 100,
        backoffMultiplier: 3,
        jitterFactor: 0,
      });
      expect(delay).toBe(900); // 100 * 3^2 = 900
    });
  });

  describe("shouldRetry", () => {
    const createMockError = (
      category: string,
      recoverable: boolean | "maybe",
    ): ClassifiedError => ({
      category: category as ClassifiedError["category"],
      message: "Test error",
      recoverable,
      timestamp: Date.now(),
      originalError: new Error("Test"),
    });

    it("should retry network errors", () => {
      const error = createMockError("network", true);
      const context: RetryContext = {
        attemptNumber: 0,
        config: DEFAULT_RETRY_CONFIG,
      };
      expect(shouldRetry(error, context)).toBe(true);
    });

    it("should retry timeout errors", () => {
      const error = createMockError("timeout", true);
      const context: RetryContext = {
        attemptNumber: 0,
        config: DEFAULT_RETRY_CONFIG,
      };
      expect(shouldRetry(error, context)).toBe(true);
    });

    it("should retry server errors (5xx)", () => {
      const error = createMockError("server", true);
      const context: RetryContext = {
        attemptNumber: 0,
        config: DEFAULT_RETRY_CONFIG,
      };
      expect(shouldRetry(error, context)).toBe(true);
    });

    it("should not retry authentication errors", () => {
      const error = createMockError("authentication", true);
      const context: RetryContext = {
        attemptNumber: 0,
        config: DEFAULT_RETRY_CONFIG,
      };
      expect(shouldRetry(error, context)).toBe(false);
    });

    it("should not retry authorization errors", () => {
      const error = createMockError("authorization", false);
      const context: RetryContext = {
        attemptNumber: 0,
        config: DEFAULT_RETRY_CONFIG,
      };
      expect(shouldRetry(error, context)).toBe(false);
    });

    it("should not retry authorization errors even when marked recoverable", () => {
      // Authorization errors should never be retried regardless of recoverable flag
      const error = createMockError("authorization", true);
      const context: RetryContext = {
        attemptNumber: 0,
        config: DEFAULT_RETRY_CONFIG,
      };
      expect(shouldRetry(error, context)).toBe(false);
    });

    it("should not retry validation errors", () => {
      const error = createMockError("validation", false);
      const context: RetryContext = {
        attemptNumber: 0,
        config: DEFAULT_RETRY_CONFIG,
      };
      expect(shouldRetry(error, context)).toBe(false);
    });

    it("should not retry validation errors even when marked recoverable", () => {
      // Validation errors should never be retried regardless of recoverable flag
      const error = createMockError("validation", true);
      const context: RetryContext = {
        attemptNumber: 0,
        config: DEFAULT_RETRY_CONFIG,
      };
      expect(shouldRetry(error, context)).toBe(false);
    });

    it("should not retry client errors", () => {
      const error = createMockError("client", false);
      const context: RetryContext = {
        attemptNumber: 0,
        config: DEFAULT_RETRY_CONFIG,
      };
      expect(shouldRetry(error, context)).toBe(false);
    });

    it("should not retry client errors even when marked recoverable", () => {
      // Client errors (4xx) should never be retried regardless of recoverable flag
      const error = createMockError("client", true);
      const context: RetryContext = {
        attemptNumber: 0,
        config: DEFAULT_RETRY_CONFIG,
      };
      expect(shouldRetry(error, context)).toBe(false);
    });

    it("should respect maxRetries limit", () => {
      const error = createMockError("network", true);
      const context: RetryContext = {
        attemptNumber: 3,
        config: DEFAULT_RETRY_CONFIG,
      };
      expect(shouldRetry(error, context)).toBe(false); // 3 >= maxRetries (3)
    });

    it("should retry quota errors with retryAfter", () => {
      const error: ClassifiedError = {
        ...createMockError("quota", true),
        retryAfter: 5000,
      };
      const context: RetryContext = {
        attemptNumber: 0,
        config: DEFAULT_RETRY_CONFIG,
      };
      expect(shouldRetry(error, context)).toBe(true);
    });

    it("should handle maybe recoverable errors", () => {
      const error = createMockError("unknown", "maybe");
      const context: RetryContext = {
        attemptNumber: 0,
        config: DEFAULT_RETRY_CONFIG,
      };
      // Maybe recoverable - should try once
      expect(shouldRetry(error, context)).toBe(true);
    });

    it("should not retry maybe errors after first attempt", () => {
      const error = createMockError("unknown", "maybe");
      const context: RetryContext = {
        attemptNumber: 1,
        config: DEFAULT_RETRY_CONFIG,
      };
      expect(shouldRetry(error, context)).toBe(false);
    });

    it("should not retry non-recoverable errors even for retryable categories", () => {
      const error = createMockError("network", false);
      const context: RetryContext = {
        attemptNumber: 0,
        config: DEFAULT_RETRY_CONFIG,
      };
      expect(shouldRetry(error, context)).toBe(false);
    });

    it("should handle config without retryableCategories", () => {
      const error = createMockError("network", true);
      const configWithoutCategories: RetryConfig = {
        ...DEFAULT_RETRY_CONFIG,
        retryableCategories: undefined,
      };
      const context: RetryContext = {
        attemptNumber: 0,
        config: configWithoutCategories,
      };
      // Falls back to DEFAULT_RETRY_CONFIG.retryableCategories
      expect(shouldRetry(error, context)).toBe(true);
    });

    it("should not retry unknown category not in retryableCategories", () => {
      const error = createMockError("unknown", true);
      const context: RetryContext = {
        attemptNumber: 0,
        config: DEFAULT_RETRY_CONFIG,
      };
      // "unknown" is not in the retryableCategories list
      expect(shouldRetry(error, context)).toBe(false);
    });

    it("should allow custom retryableCategories to include categories", () => {
      const error = createMockError("unknown", true);
      const config: RetryConfig = {
        ...DEFAULT_RETRY_CONFIG,
        retryableCategories: ["unknown", "network"],
      };
      const context: RetryContext = { attemptNumber: 0, config };
      expect(shouldRetry(error, context)).toBe(true);
    });

    it("should handle empty retryableCategories array", () => {
      const error = createMockError("network", true);
      const config: RetryConfig = {
        ...DEFAULT_RETRY_CONFIG,
        retryableCategories: [],
      };
      const context: RetryContext = { attemptNumber: 0, config };
      // Network is usually retryable but not in empty array
      expect(shouldRetry(error, context)).toBe(false);
    });
  });

  describe("getRetryConfig", () => {
    it("should return default config when no overrides", () => {
      const config = getRetryConfig();
      expect(config).toEqual(DEFAULT_RETRY_CONFIG);
    });

    it("should merge partial overrides", () => {
      const config = getRetryConfig({ maxRetries: 5 });
      expect(config.maxRetries).toBe(5);
      expect(config.baseDelayMs).toBe(DEFAULT_RETRY_CONFIG.baseDelayMs);
    });

    it("should override all values when provided", () => {
      const customConfig: RetryConfig = {
        maxRetries: 5,
        baseDelayMs: 500,
        maxDelayMs: 10000,
        backoffMultiplier: 1.5,
        jitterFactor: 0.1,
        retryableCategories: ["network"],
      };
      const config = getRetryConfig(customConfig);
      expect(config).toEqual(customConfig);
    });

    it("should allow custom retryable categories", () => {
      const config = getRetryConfig({
        retryableCategories: ["network", "timeout"],
      });
      expect(config.retryableCategories).toEqual(["network", "timeout"]);
    });
  });
});
