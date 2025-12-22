/**
 * Memory Monitor Tests
 *
 * TDD tests for memory monitoring utilities that track heap usage
 * during test runs to detect memory leaks and excessive allocation.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  MemoryMonitor,
  getMemoryStats,
  formatBytes,
  MemoryThresholds,
} from "./memoryMonitor";

describe("memoryMonitor", () => {
  describe("formatBytes", () => {
    it("should format bytes to human readable string", () => {
      expect(formatBytes(0)).toBe("0 B");
      expect(formatBytes(1024)).toBe("1.00 KB");
      expect(formatBytes(1024 * 1024)).toBe("1.00 MB");
      expect(formatBytes(1024 * 1024 * 1024)).toBe("1.00 GB");
    });

    it("should handle fractional values", () => {
      expect(formatBytes(1536)).toBe("1.50 KB");
      expect(formatBytes(1024 * 1024 * 2.5)).toBe("2.50 MB");
    });

    it("should handle negative values", () => {
      expect(formatBytes(-1024)).toBe("-1.00 KB");
    });
  });

  describe("getMemoryStats", () => {
    it("should return memory usage object", () => {
      const stats = getMemoryStats();
      expect(stats).toHaveProperty("heapUsed");
      expect(stats).toHaveProperty("heapTotal");
      expect(stats).toHaveProperty("external");
      expect(stats).toHaveProperty("rss");
    });

    it("should return numeric values", () => {
      const stats = getMemoryStats();
      expect(typeof stats.heapUsed).toBe("number");
      expect(typeof stats.heapTotal).toBe("number");
      expect(stats.heapUsed).toBeGreaterThan(0);
    });
  });

  describe("MemoryMonitor", () => {
    let monitor: MemoryMonitor;
    let consoleSpy: ReturnType<typeof vi.spyOn>;

    beforeEach(() => {
      // Explicitly enable for testing (default is disabled without DEBUG env)
      monitor = new MemoryMonitor({ enabled: true });
      consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});
    });

    afterEach(() => {
      consoleSpy.mockRestore();
    });

    describe("snapshot", () => {
      it("should take a memory snapshot with label", () => {
        monitor.snapshot("test-point");
        const snapshots = monitor.getSnapshots();
        expect(snapshots).toHaveLength(1);
        expect(snapshots[0].label).toBe("test-point");
      });

      it("should record heap usage in snapshot", () => {
        monitor.snapshot("test");
        const snapshots = monitor.getSnapshots();
        expect(snapshots[0].heapUsed).toBeGreaterThan(0);
        expect(snapshots[0].heapTotal).toBeGreaterThan(0);
      });

      it("should take multiple snapshots", () => {
        monitor.snapshot("before");
        monitor.snapshot("after");
        expect(monitor.getSnapshots()).toHaveLength(2);
      });
    });

    describe("delta", () => {
      it("should calculate delta between two snapshots", () => {
        monitor.snapshot("before");
        // Allocate some memory
        const arr = new Array(10000).fill("test");
        monitor.snapshot("after");

        const delta = monitor.getDelta("before", "after");
        expect(delta).not.toBeNull();
        expect(delta?.heapUsedDelta).toBeDefined();

        // Prevent optimization
        expect(arr.length).toBe(10000);
      });

      it("should return null for non-existent labels", () => {
        monitor.snapshot("exists");
        expect(monitor.getDelta("exists", "missing")).toBeNull();
        expect(monitor.getDelta("missing", "exists")).toBeNull();
      });
    });

    describe("threshold checking", () => {
      it("should detect when heap exceeds threshold", () => {
        // Set impossibly low thresholds to guarantee exceeding them
        // Error threshold is lower than warning, so errors get triggered first
        const thresholds: MemoryThresholds = {
          heapUsedWarningMB: 0.001, // 1KB - guaranteed to exceed
          heapUsedErrorMB: 0.002, // 2KB - also exceeded, so error triggers
        };

        monitor = new MemoryMonitor({ enabled: true, thresholds });
        const result = monitor.checkThresholds();

        // Since both thresholds are exceeded, error is triggered (takes priority)
        expect(result.errors.length).toBeGreaterThan(0);
        expect(result.passed).toBe(false);
      });

      it("should not warn when under threshold", () => {
        const thresholds: MemoryThresholds = {
          heapUsedWarningMB: 10000, // 10GB - way above normal usage
          heapUsedErrorMB: 20000,
        };

        monitor = new MemoryMonitor({ enabled: true, thresholds });
        const result = monitor.checkThresholds();

        expect(result.warnings).toHaveLength(0);
        expect(result.errors).toHaveLength(0);
      });
    });

    describe("reset", () => {
      it("should clear all snapshots", () => {
        monitor.snapshot("one");
        monitor.snapshot("two");
        expect(monitor.getSnapshots()).toHaveLength(2);

        monitor.reset();
        expect(monitor.getSnapshots()).toHaveLength(0);
      });
    });

    describe("report", () => {
      it("should generate summary report", () => {
        monitor.snapshot("start");
        monitor.snapshot("end");

        const report = monitor.generateReport();

        expect(report).toContain("Memory Report");
        expect(report).toContain("start");
        expect(report).toContain("end");
      });

      it("should include formatted memory values", () => {
        monitor.snapshot("test");
        const report = monitor.generateReport();

        // Should contain formatted byte values (KB or MB)
        expect(report).toMatch(/\d+\.\d+ [KMG]B/);
      });
    });

    describe("enabled flag", () => {
      it("should skip operations when disabled", () => {
        monitor = new MemoryMonitor({ enabled: false });
        monitor.snapshot("test");
        expect(monitor.getSnapshots()).toHaveLength(0);
      });

      it("should work normally when enabled", () => {
        monitor = new MemoryMonitor({ enabled: true });
        monitor.snapshot("test");
        expect(monitor.getSnapshots()).toHaveLength(1);
      });
    });

    describe("environment variable configuration", () => {
      const originalEnv = process.env;

      beforeEach(() => {
        // Reset environment for each test
        process.env = { ...originalEnv };
      });

      afterEach(() => {
        process.env = originalEnv;
      });

      it("should use default thresholds when env vars not set", () => {
        delete process.env.VITEST_MEMORY_WARNING_MB;
        delete process.env.VITEST_MEMORY_ERROR_MB;
        delete process.env.VITEST_MEMORY_DELTA_MB;

        monitor = new MemoryMonitor({ enabled: true });
        const thresholds = monitor.getThresholds();

        expect(thresholds.heapUsedWarningMB).toBe(512);
        expect(thresholds.heapUsedErrorMB).toBe(1024);
        expect(thresholds.deltaWarningMB).toBe(50);
      });

      it("should read warning threshold from VITEST_MEMORY_WARNING_MB", () => {
        process.env.VITEST_MEMORY_WARNING_MB = "256";

        monitor = new MemoryMonitor({ enabled: true });
        const thresholds = monitor.getThresholds();

        expect(thresholds.heapUsedWarningMB).toBe(256);
      });

      it("should read error threshold from VITEST_MEMORY_ERROR_MB", () => {
        process.env.VITEST_MEMORY_ERROR_MB = "2048";

        monitor = new MemoryMonitor({ enabled: true });
        const thresholds = monitor.getThresholds();

        expect(thresholds.heapUsedErrorMB).toBe(2048);
      });

      it("should read delta threshold from VITEST_MEMORY_DELTA_MB", () => {
        process.env.VITEST_MEMORY_DELTA_MB = "100";

        monitor = new MemoryMonitor({ enabled: true });
        const thresholds = monitor.getThresholds();

        expect(thresholds.deltaWarningMB).toBe(100);
      });

      it("should prioritize explicit options over environment variables", () => {
        process.env.VITEST_MEMORY_WARNING_MB = "256";
        process.env.VITEST_MEMORY_ERROR_MB = "512";

        monitor = new MemoryMonitor({
          enabled: true,
          thresholds: {
            heapUsedWarningMB: 100,
            heapUsedErrorMB: 200,
          },
        });
        const thresholds = monitor.getThresholds();

        expect(thresholds.heapUsedWarningMB).toBe(100);
        expect(thresholds.heapUsedErrorMB).toBe(200);
      });

      it("should ignore invalid (non-numeric) environment values", () => {
        process.env.VITEST_MEMORY_WARNING_MB = "invalid";
        process.env.VITEST_MEMORY_ERROR_MB = "";

        monitor = new MemoryMonitor({ enabled: true });
        const thresholds = monitor.getThresholds();

        // Should fall back to defaults
        expect(thresholds.heapUsedWarningMB).toBe(512);
        expect(thresholds.heapUsedErrorMB).toBe(1024);
      });

      it("should handle zero values from environment", () => {
        process.env.VITEST_MEMORY_WARNING_MB = "0";

        monitor = new MemoryMonitor({ enabled: true });
        const thresholds = monitor.getThresholds();

        // Zero is valid but unusual - should fall back to default
        expect(thresholds.heapUsedWarningMB).toBe(512);
      });

      it("should handle negative values from environment", () => {
        process.env.VITEST_MEMORY_WARNING_MB = "-100";

        monitor = new MemoryMonitor({ enabled: true });
        const thresholds = monitor.getThresholds();

        // Negative is invalid - should fall back to default
        expect(thresholds.heapUsedWarningMB).toBe(512);
      });
    });
  });
});
