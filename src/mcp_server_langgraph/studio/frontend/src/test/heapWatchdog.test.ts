/**
 * Heap Watchdog Tests
 *
 * TDD tests for the worker-side heap watchdog that polls V8 heap statistics
 * and kills the worker before entering a GC death spiral.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  HeapWatchdog,
  createHeapWatchdog,
  formatHeapWatchdogMessage,
  type HeapStats,
} from "./heapWatchdog";

// We don't mock v8 globally — instead, HeapWatchdog.getHeapStats() calls v8
// internally and tests verify behavior through callbacks and return values.

describe("heapWatchdog", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  // ===========================================================================
  // HeapWatchdog Class
  // ===========================================================================

  describe("HeapWatchdog", () => {
    describe("constructor", () => {
      it("should accept config and use defaults", () => {
        const watchdog = new HeapWatchdog({ filePath: "test.ts" });
        const stats = watchdog.getHeapStats();

        // Should be able to get stats without starting
        expect(stats.usedMB).toBeGreaterThan(0);
        expect(stats.limitMB).toBeGreaterThan(0);
        expect(stats.percentage).toBeGreaterThan(0);
      });

      it("should use default threshold of 0.85", () => {
        const callback = vi.fn();
        const watchdog = new HeapWatchdog({
          filePath: "test.ts",
          onThresholdExceeded: callback,
        });

        // Real heap usage is well under 85%, so callback should not fire
        watchdog.start();
        vi.advanceTimersByTime(10000);
        watchdog.stop();

        expect(callback).not.toHaveBeenCalled();
      });

      it("should use default poll interval of 2000ms", () => {
        const callback = vi.fn();
        const watchdog = new HeapWatchdog({
          filePath: "test.ts",
          threshold: 0.0001, // Extremely low - will trigger on any heap usage
          onThresholdExceeded: callback,
        });

        watchdog.start();

        // Advance 1999ms - should not have polled yet
        vi.advanceTimersByTime(1999);
        expect(callback).not.toHaveBeenCalled();

        // Advance 1ms more (total 2000ms) - first poll should fire
        vi.advanceTimersByTime(1);
        expect(callback).toHaveBeenCalledTimes(1);

        watchdog.stop();
      });

      it("should accept custom threshold and poll interval", () => {
        const callback = vi.fn();
        const watchdog = new HeapWatchdog({
          filePath: "test.ts",
          threshold: 0.0001, // Extremely low - will trigger on any heap usage
          pollIntervalMs: 500,
          onThresholdExceeded: callback,
        });

        watchdog.start();
        vi.advanceTimersByTime(500);
        watchdog.stop();

        expect(callback).toHaveBeenCalled();
      });
    });

    describe("start", () => {
      it("should start polling and call callback on threshold breach", () => {
        const callback = vi.fn();
        const watchdog = new HeapWatchdog({
          filePath: "src/components/Heavy.test.tsx",
          threshold: 0.0001, // Extremely low - will trigger
          onThresholdExceeded: callback,
        });

        watchdog.start();
        vi.advanceTimersByTime(2000);

        expect(callback).toHaveBeenCalledWith(
          expect.objectContaining({
            usedMB: expect.any(Number),
            limitMB: expect.any(Number),
            percentage: expect.any(Number),
          }),
          "src/components/Heavy.test.tsx",
        );

        watchdog.stop();
      });

      it("should be a no-op if already started", () => {
        const callback = vi.fn();
        const watchdog = new HeapWatchdog({
          filePath: "test.ts",
          threshold: 0.0001,
          onThresholdExceeded: callback,
        });

        watchdog.start();
        // Start again - should not create a second interval
        watchdog.start();

        vi.advanceTimersByTime(2000);
        // Should only fire once (one interval, not two)
        expect(callback).toHaveBeenCalledTimes(1);

        watchdog.stop();
      });

      it("should not call callback when under threshold", () => {
        const callback = vi.fn();
        const watchdog = new HeapWatchdog({
          filePath: "test.ts",
          threshold: 0.99, // Very high threshold - real heap won't reach this
          onThresholdExceeded: callback,
        });

        watchdog.start();
        vi.advanceTimersByTime(10000);
        watchdog.stop();

        expect(callback).not.toHaveBeenCalled();
      });
    });

    describe("stop", () => {
      it("should clear the polling interval", () => {
        const callback = vi.fn();
        const watchdog = new HeapWatchdog({
          filePath: "test.ts",
          threshold: 0.0001,
          onThresholdExceeded: callback,
        });

        watchdog.start();
        watchdog.stop();

        // Advance time - callback should not fire after stop
        vi.advanceTimersByTime(10000);
        expect(callback).not.toHaveBeenCalled();
      });

      it("should be safe to call multiple times", () => {
        const watchdog = new HeapWatchdog({ filePath: "test.ts" });

        watchdog.start();
        watchdog.stop();
        watchdog.stop();
        watchdog.stop();

        // Should not throw
        expect(true).toBe(true);
      });

      it("should be safe to call before start", () => {
        const watchdog = new HeapWatchdog({ filePath: "test.ts" });

        // Should not throw
        watchdog.stop();
        expect(true).toBe(true);
      });
    });

    describe("getHeapStats", () => {
      it("should return usedMB, limitMB, percentage from v8", () => {
        const watchdog = new HeapWatchdog({ filePath: "test.ts" });
        const stats = watchdog.getHeapStats();

        // Real V8 heap: usedMB should be > 0 and < limitMB
        expect(stats.usedMB).toBeGreaterThan(0);
        expect(stats.limitMB).toBeGreaterThan(0);
        expect(stats.limitMB).toBeGreaterThan(stats.usedMB);
        expect(stats.percentage).toBeGreaterThan(0);
        expect(stats.percentage).toBeLessThan(100);
      });
    });
  });

  // ===========================================================================
  // createHeapWatchdog Factory
  // ===========================================================================

  describe("createHeapWatchdog", () => {
    const originalEnv = process.env;

    beforeEach(() => {
      process.env = { ...originalEnv };
      delete process.env.VITEST_SHARDED;
      delete process.env.VITEST_HEAP_WATCHDOG;
    });

    afterEach(() => {
      process.env = originalEnv;
    });

    it("should return watchdog when VITEST_SHARDED=1", () => {
      process.env.VITEST_SHARDED = "1";

      const watchdog = createHeapWatchdog("test.ts");
      expect(watchdog).toBeInstanceOf(HeapWatchdog);
    });

    it("should return watchdog when VITEST_HEAP_WATCHDOG=true", () => {
      process.env.VITEST_HEAP_WATCHDOG = "true";

      const watchdog = createHeapWatchdog("test.ts");
      expect(watchdog).toBeInstanceOf(HeapWatchdog);
    });

    it("should return null when neither env var is set", () => {
      const watchdog = createHeapWatchdog("test.ts");
      expect(watchdog).toBeNull();
    });

    it("should create watchdog with default callback that writes to stderr and exits 137", () => {
      process.env.VITEST_SHARDED = "1";

      const stderrSpy = vi
        .spyOn(process.stderr, "write")
        .mockImplementation(() => true);
      const exitSpy = vi
        .spyOn(process, "exit")
        .mockImplementation(() => undefined as never);

      // Use the actual factory to verify default callback wiring
      const watchdog = createHeapWatchdog("src/components/Heavy.test.tsx")!;
      expect(watchdog).toBeInstanceOf(HeapWatchdog);

      // Stub getHeapStats to simulate near-OOM (100% usage) so the default
      // threshold (0.85) is exceeded and the factory-wired callback fires
      vi.spyOn(watchdog, "getHeapStats").mockReturnValue({
        usedMB: 3072,
        limitMB: 3072,
        percentage: 100,
      });

      watchdog.start();
      vi.advanceTimersByTime(2000);

      expect(stderrSpy).toHaveBeenCalledWith(
        expect.stringContaining("[HEAP WATCHDOG]"),
      );
      expect(stderrSpy).toHaveBeenCalledWith(
        expect.stringContaining("KILLING WORKER"),
      );
      expect(exitSpy).toHaveBeenCalledWith(137);

      watchdog.stop();

      stderrSpy.mockRestore();
      exitSpy.mockRestore();
    });
  });

  // ===========================================================================
  // formatHeapWatchdogMessage Helper
  // ===========================================================================

  describe("formatHeapWatchdogMessage", () => {
    it("should format [HEAP WATCHDOG] line with path, usedMB, limitMB, percentage", () => {
      const stats: HeapStats = {
        usedMB: 2610,
        limitMB: 3072,
        percentage: 85.0,
      };

      const message = formatHeapWatchdogMessage(
        "src/components/CanvasArtifact.test.tsx",
        stats,
      );

      expect(message).toBe(
        "[HEAP WATCHDOG] src/components/CanvasArtifact.test.tsx: 2610MB / 3072MB (85.0%) - KILLING WORKER\n",
      );
    });

    it("should handle decimal percentages", () => {
      const stats: HeapStats = {
        usedMB: 2611,
        limitMB: 3072,
        percentage: 85.03,
      };

      const message = formatHeapWatchdogMessage("test.ts", stats);

      expect(message).toContain("85.0%");
    });

    it("should include the full file path in the message", () => {
      const stats: HeapStats = {
        usedMB: 1000,
        limitMB: 3072,
        percentage: 32.6,
      };

      const message = formatHeapWatchdogMessage(
        "src/hooks/useStreamingChat.test.ts",
        stats,
      );

      expect(message).toContain("src/hooks/useStreamingChat.test.ts");
    });
  });
});
