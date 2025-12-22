/**
 * Memory Trend Reporter Tests
 *
 * TDD tests for utility that generates CI-compatible memory trend data
 * for publishing to the gh-pages dashboard.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  MemoryTrendReporter,
  type MemoryTrendEntry,
  type MemoryTrendReport,
  type MemoryTrendRunEntry,
  type MemoryRegressionResult,
  type MemoryRegressionThresholds,
  formatMemoryForCI,
  parseExistingTrends,
  mergeTrendData,
  detectMemoryRegression,
  calculateRollingAverage,
  DEFAULT_REGRESSION_THRESHOLDS,
} from "./memoryTrendReporter";

describe("memoryTrendReporter", () => {
  // ===========================================================================
  // MemoryTrendReporter Class
  // ===========================================================================

  describe("MemoryTrendReporter", () => {
    let reporter: MemoryTrendReporter;

    beforeEach(() => {
      reporter = new MemoryTrendReporter();
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    describe("constructor", () => {
      it("should initialize with empty entries", () => {
        expect(reporter.getEntries()).toEqual([]);
        expect(reporter.getEntryCount()).toBe(0);
      });

      it("should accept optional metadata", () => {
        const reporterWithMeta = new MemoryTrendReporter({
          commit: "abc123",
          branch: "main",
          testSuite: "frontend",
        });

        const report = reporterWithMeta.generateReport();
        expect(report.metadata.commit).toBe("abc123");
        expect(report.metadata.branch).toBe("main");
        expect(report.metadata.testSuite).toBe("frontend");
      });
    });

    describe("recordEntry", () => {
      it("should record a memory entry with timestamp", () => {
        const before = Date.now();
        reporter.recordEntry("suite-start", {
          heapUsed: 50 * 1024 * 1024,
          heapTotal: 100 * 1024 * 1024,
          external: 5 * 1024 * 1024,
          rss: 150 * 1024 * 1024,
        });
        const after = Date.now();

        const entries = reporter.getEntries();
        expect(entries).toHaveLength(1);
        expect(entries[0].label).toBe("suite-start");
        expect(entries[0].heapUsedMB).toBeCloseTo(50, 0);
        expect(entries[0].heapTotalMB).toBeCloseTo(100, 0);
        expect(entries[0].timestamp).toBeGreaterThanOrEqual(before);
        expect(entries[0].timestamp).toBeLessThanOrEqual(after);
      });

      it("should calculate delta from previous entry", () => {
        reporter.recordEntry("start", {
          heapUsed: 50 * 1024 * 1024,
          heapTotal: 100 * 1024 * 1024,
          external: 5 * 1024 * 1024,
          rss: 150 * 1024 * 1024,
        });

        reporter.recordEntry("end", {
          heapUsed: 80 * 1024 * 1024,
          heapTotal: 120 * 1024 * 1024,
          external: 8 * 1024 * 1024,
          rss: 180 * 1024 * 1024,
        });

        const entries = reporter.getEntries();
        expect(entries[1].deltaMB).toBeCloseTo(30, 0); // 80 - 50 = 30MB delta
      });

      it("should handle multiple entries correctly", () => {
        reporter.recordEntry("phase1", { heapUsed: 50 * 1024 * 1024, heapTotal: 100 * 1024 * 1024, external: 0, rss: 0 });
        reporter.recordEntry("phase2", { heapUsed: 60 * 1024 * 1024, heapTotal: 110 * 1024 * 1024, external: 0, rss: 0 });
        reporter.recordEntry("phase3", { heapUsed: 55 * 1024 * 1024, heapTotal: 105 * 1024 * 1024, external: 0, rss: 0 });

        expect(reporter.getEntryCount()).toBe(3);
        expect(reporter.getEntries()[2].deltaMB).toBeCloseTo(-5, 0); // 55 - 60 = -5MB (memory freed)
      });
    });

    describe("generateReport", () => {
      it("should generate a complete report with metadata", () => {
        reporter.recordEntry("start", { heapUsed: 50 * 1024 * 1024, heapTotal: 100 * 1024 * 1024, external: 0, rss: 0 });
        reporter.recordEntry("end", { heapUsed: 80 * 1024 * 1024, heapTotal: 120 * 1024 * 1024, external: 0, rss: 0 });

        const report = reporter.generateReport();

        expect(report.metadata.generatedAt).toBeDefined();
        expect(report.entries).toHaveLength(2);
        expect(report.summary).toBeDefined();
      });

      it("should include summary statistics", () => {
        reporter.recordEntry("start", { heapUsed: 50 * 1024 * 1024, heapTotal: 100 * 1024 * 1024, external: 0, rss: 0 });
        reporter.recordEntry("mid", { heapUsed: 100 * 1024 * 1024, heapTotal: 150 * 1024 * 1024, external: 0, rss: 0 });
        reporter.recordEntry("end", { heapUsed: 70 * 1024 * 1024, heapTotal: 120 * 1024 * 1024, external: 0, rss: 0 });

        const report = reporter.generateReport();

        expect(report.summary.peakHeapUsedMB).toBeCloseTo(100, 0);
        expect(report.summary.finalHeapUsedMB).toBeCloseTo(70, 0);
        expect(report.summary.totalDeltaMB).toBeCloseTo(20, 0); // 70 - 50 = 20MB
        expect(report.summary.entryCount).toBe(3);
      });

      it("should handle empty entries gracefully", () => {
        const report = reporter.generateReport();

        expect(report.entries).toEqual([]);
        expect(report.summary.peakHeapUsedMB).toBe(0);
        expect(report.summary.finalHeapUsedMB).toBe(0);
        expect(report.summary.totalDeltaMB).toBe(0);
      });
    });

    describe("toJSON", () => {
      it("should return JSON-serializable output", () => {
        reporter.recordEntry("test", { heapUsed: 50 * 1024 * 1024, heapTotal: 100 * 1024 * 1024, external: 0, rss: 0 });

        const json = reporter.toJSON();
        const parsed = JSON.parse(JSON.stringify(json));

        expect(parsed.entries).toHaveLength(1);
        expect(parsed.metadata).toBeDefined();
        expect(parsed.summary).toBeDefined();
      });
    });

    describe("reset", () => {
      it("should clear all entries", () => {
        reporter.recordEntry("test", { heapUsed: 50 * 1024 * 1024, heapTotal: 100 * 1024 * 1024, external: 0, rss: 0 });
        expect(reporter.getEntryCount()).toBe(1);

        reporter.reset();
        expect(reporter.getEntryCount()).toBe(0);
        expect(reporter.getEntries()).toEqual([]);
      });
    });
  });

  // ===========================================================================
  // formatMemoryForCI Helper
  // ===========================================================================

  describe("formatMemoryForCI", () => {
    it("should format bytes to MB with 2 decimal places", () => {
      expect(formatMemoryForCI(52428800)).toBe(50); // 50 * 1024 * 1024
      expect(formatMemoryForCI(104857600)).toBe(100); // 100 * 1024 * 1024
    });

    it("should handle zero bytes", () => {
      expect(formatMemoryForCI(0)).toBe(0);
    });

    it("should round to 2 decimal places", () => {
      const bytes = 52_500_000; // ~50.07 MB
      const result = formatMemoryForCI(bytes);
      expect(result).toBeCloseTo(50.07, 1);
    });
  });

  // ===========================================================================
  // parseExistingTrends Helper
  // ===========================================================================

  describe("parseExistingTrends", () => {
    it("should parse valid JSON trend data", () => {
      const json = JSON.stringify({
        runs: [
          { timestamp: "2025-01-01T00:00:00Z", peakHeapMB: 100, commit: "abc123" },
        ],
        metadata: { created: "2025-01-01T00:00:00Z" },
      });

      const result = parseExistingTrends(json);
      expect(result.runs).toHaveLength(1);
      expect(result.runs[0].peakHeapMB).toBe(100);
    });

    it("should return empty structure for invalid JSON", () => {
      const result = parseExistingTrends("not valid json");
      expect(result.runs).toEqual([]);
      expect(result.metadata).toBeDefined();
    });

    it("should return empty structure for null/undefined", () => {
      const result = parseExistingTrends(null as unknown as string);
      expect(result.runs).toEqual([]);
    });
  });

  // ===========================================================================
  // mergeTrendData Helper
  // ===========================================================================

  describe("mergeTrendData", () => {
    it("should add new run to existing trends", () => {
      const existing = {
        runs: [{ timestamp: "2025-01-01T00:00:00Z", peakHeapMB: 100, commit: "abc123", finalHeapMB: 80, deltaMB: -20 }],
        metadata: { created: "2025-01-01T00:00:00Z", updated: "2025-01-01T00:00:00Z" },
      };

      const newRun = {
        timestamp: "2025-01-02T00:00:00Z",
        peakHeapMB: 120,
        finalHeapMB: 90,
        deltaMB: 10,
        commit: "def456",
      };

      const result = mergeTrendData(existing, newRun);
      expect(result.runs).toHaveLength(2);
      expect(result.runs[1].commit).toBe("def456");
    });

    it("should limit to last 100 runs", () => {
      const runs = Array.from({ length: 105 }, (_, i) => ({
        timestamp: `2025-01-${String(i + 1).padStart(2, "0")}T00:00:00Z`,
        peakHeapMB: 100 + i,
        finalHeapMB: 80 + i,
        deltaMB: 0,
        commit: `commit${i}`,
      }));

      const existing = {
        runs,
        metadata: { created: "2025-01-01T00:00:00Z", updated: "2025-01-01T00:00:00Z" },
      };

      const newRun = {
        timestamp: "2025-04-20T00:00:00Z",
        peakHeapMB: 150,
        finalHeapMB: 130,
        deltaMB: 10,
        commit: "newcommit",
      };

      const result = mergeTrendData(existing, newRun);
      expect(result.runs).toHaveLength(100);
      expect(result.runs[99].commit).toBe("newcommit");
    });

    it("should update metadata timestamp", () => {
      const existing = {
        runs: [],
        metadata: { created: "2025-01-01T00:00:00Z", updated: "2025-01-01T00:00:00Z" },
      };

      const before = new Date().toISOString();
      const result = mergeTrendData(existing, {
        timestamp: "2025-01-02T00:00:00Z",
        peakHeapMB: 100,
        finalHeapMB: 80,
        deltaMB: 10,
        commit: "test",
      });
      const after = new Date().toISOString();

      expect(result.metadata.updated >= before).toBe(true);
      expect(result.metadata.updated <= after).toBe(true);
    });
  });

  // ===========================================================================
  // Integration: MemoryTrendEntry Type
  // ===========================================================================

  describe("MemoryTrendEntry type", () => {
    it("should have all required fields", () => {
      const entry: MemoryTrendEntry = {
        label: "test",
        timestamp: Date.now(),
        heapUsedMB: 50,
        heapTotalMB: 100,
        externalMB: 5,
        rssMB: 150,
        deltaMB: 10,
      };

      expect(entry.label).toBe("test");
      expect(entry.heapUsedMB).toBe(50);
      expect(entry.deltaMB).toBe(10);
    });
  });

  describe("MemoryTrendReport type", () => {
    it("should have entries, summary, and metadata", () => {
      const report: MemoryTrendReport = {
        entries: [],
        summary: {
          peakHeapUsedMB: 100,
          finalHeapUsedMB: 80,
          totalDeltaMB: 20,
          entryCount: 5,
        },
        metadata: {
          generatedAt: new Date().toISOString(),
          commit: "abc123",
          branch: "main",
        },
      };

      expect(report.entries).toEqual([]);
      expect(report.summary.peakHeapUsedMB).toBe(100);
      expect(report.metadata.commit).toBe("abc123");
    });
  });

  // ===========================================================================
  // Memory Regression Detection
  // ===========================================================================

  describe("calculateRollingAverage", () => {
    it("should calculate average of peak heap values", () => {
      const runs: MemoryTrendRunEntry[] = [
        { timestamp: "2025-01-01", peakHeapMB: 100, finalHeapMB: 80, deltaMB: 0, commit: "a" },
        { timestamp: "2025-01-02", peakHeapMB: 120, finalHeapMB: 90, deltaMB: 10, commit: "b" },
        { timestamp: "2025-01-03", peakHeapMB: 110, finalHeapMB: 85, deltaMB: 5, commit: "c" },
      ];

      const avg = calculateRollingAverage(runs);
      expect(avg).toBeCloseTo(110, 0); // (100 + 120 + 110) / 3 = 110
    });

    it("should return 0 for empty runs", () => {
      expect(calculateRollingAverage([])).toBe(0);
    });

    it("should handle single run", () => {
      const runs: MemoryTrendRunEntry[] = [
        { timestamp: "2025-01-01", peakHeapMB: 100, finalHeapMB: 80, deltaMB: 0, commit: "a" },
      ];

      expect(calculateRollingAverage(runs)).toBe(100);
    });

    it("should limit to last N runs when specified", () => {
      const runs: MemoryTrendRunEntry[] = [
        { timestamp: "2025-01-01", peakHeapMB: 200, finalHeapMB: 80, deltaMB: 0, commit: "a" },
        { timestamp: "2025-01-02", peakHeapMB: 100, finalHeapMB: 90, deltaMB: 10, commit: "b" },
        { timestamp: "2025-01-03", peakHeapMB: 100, finalHeapMB: 85, deltaMB: 5, commit: "c" },
        { timestamp: "2025-01-04", peakHeapMB: 100, finalHeapMB: 85, deltaMB: 5, commit: "d" },
      ];

      // Only use last 3 runs (excludes the 200MB outlier)
      const avg = calculateRollingAverage(runs, 3);
      expect(avg).toBeCloseTo(100, 0); // (100 + 100 + 100) / 3 = 100
    });
  });

  describe("detectMemoryRegression", () => {
    const createRun = (peakHeapMB: number, commit: string): MemoryTrendRunEntry => ({
      timestamp: new Date().toISOString(),
      peakHeapMB,
      finalHeapMB: peakHeapMB * 0.8,
      deltaMB: 0,
      commit,
    });

    describe("status determination", () => {
      it("should return 'ok' when memory is stable", () => {
        const previousRuns = [
          createRun(100, "a"),
          createRun(102, "b"),
          createRun(98, "c"),
        ];
        const currentRun = createRun(100, "d");

        const result = detectMemoryRegression(currentRun, previousRuns);

        expect(result.status).toBe("ok");
        expect(result.message).toContain("stable");
      });

      it("should return 'warning' when memory increases moderately (10-20%)", () => {
        const previousRuns = [
          createRun(100, "a"),
          createRun(100, "b"),
          createRun(100, "c"),
        ];
        const currentRun = createRun(115, "d"); // 15% increase

        const result = detectMemoryRegression(currentRun, previousRuns);

        expect(result.status).toBe("warning");
        expect(result.percentChangeFromLast).toBeCloseTo(15, 0);
      });

      it("should return 'error' when memory increases significantly (>20%)", () => {
        const previousRuns = [
          createRun(100, "a"),
          createRun(100, "b"),
          createRun(100, "c"),
        ];
        const currentRun = createRun(130, "d"); // 30% increase

        const result = detectMemoryRegression(currentRun, previousRuns);

        expect(result.status).toBe("error");
        expect(result.percentChangeFromLast).toBeCloseTo(30, 0);
      });

      it("should handle memory decrease gracefully", () => {
        const previousRuns = [
          createRun(100, "a"),
          createRun(100, "b"),
          createRun(100, "c"),
        ];
        const currentRun = createRun(80, "d"); // 20% decrease

        const result = detectMemoryRegression(currentRun, previousRuns);

        expect(result.status).toBe("ok");
        expect(result.percentChangeFromLast).toBeCloseTo(-20, 0);
        expect(result.message).toContain("improved");
      });
    });

    describe("calculations", () => {
      it("should calculate percent change from last run", () => {
        const previousRuns = [createRun(100, "a")];
        const currentRun = createRun(110, "b");

        const result = detectMemoryRegression(currentRun, previousRuns);

        expect(result.percentChangeFromLast).toBeCloseTo(10, 0);
      });

      it("should calculate percent change from rolling average", () => {
        const previousRuns = [
          createRun(100, "a"),
          createRun(110, "b"),
          createRun(90, "c"),
        ];
        const currentRun = createRun(120, "d");

        const result = detectMemoryRegression(currentRun, previousRuns);

        // Average of previous: (100 + 110 + 90) / 3 = 100
        // Change: (120 - 100) / 100 * 100 = 20%
        expect(result.percentChangeFromAverage).toBeCloseTo(20, 0);
      });

      it("should include current and previous values in result", () => {
        const previousRuns = [createRun(100, "a")];
        const currentRun = createRun(110, "b");

        const result = detectMemoryRegression(currentRun, previousRuns);

        expect(result.currentPeakMB).toBe(110);
        expect(result.previousPeakMB).toBe(100);
        expect(result.rollingAverageMB).toBe(100);
      });
    });

    describe("edge cases", () => {
      it("should handle no previous runs gracefully", () => {
        const currentRun = createRun(100, "a");

        const result = detectMemoryRegression(currentRun, []);

        expect(result.status).toBe("ok");
        expect(result.message).toContain("baseline");
        expect(result.percentChangeFromLast).toBe(0);
        expect(result.percentChangeFromAverage).toBe(0);
      });

      it("should handle single previous run", () => {
        const previousRuns = [createRun(100, "a")];
        const currentRun = createRun(110, "b");

        const result = detectMemoryRegression(currentRun, previousRuns);

        expect(result.status).toBe("warning");
        expect(result.percentChangeFromLast).toBeCloseTo(10, 0);
      });

      it("should handle zero previous memory (avoid division by zero)", () => {
        const previousRuns = [createRun(0, "a")];
        const currentRun = createRun(100, "b");

        const result = detectMemoryRegression(currentRun, previousRuns);

        // Should not throw, should handle gracefully
        expect(result.status).toBeDefined();
      });
    });

    describe("custom thresholds", () => {
      it("should use custom warning threshold", () => {
        const previousRuns = [createRun(100, "a")];
        const currentRun = createRun(105, "b"); // 5% increase

        const customThresholds: MemoryRegressionThresholds = {
          warningPercentIncrease: 3, // Lower than default
          errorPercentIncrease: 10,
          rollingAverageWindow: 5,
        };

        const result = detectMemoryRegression(currentRun, previousRuns, customThresholds);

        expect(result.status).toBe("warning"); // 5% > 3% warning threshold
      });

      it("should use custom error threshold", () => {
        const previousRuns = [createRun(100, "a")];
        const currentRun = createRun(108, "b"); // 8% increase

        const customThresholds: MemoryRegressionThresholds = {
          warningPercentIncrease: 3,
          errorPercentIncrease: 5, // Lower than default
          rollingAverageWindow: 5,
        };

        const result = detectMemoryRegression(currentRun, previousRuns, customThresholds);

        expect(result.status).toBe("error"); // 8% > 5% error threshold
      });
    });

    describe("DEFAULT_REGRESSION_THRESHOLDS", () => {
      it("should have sensible default values", () => {
        expect(DEFAULT_REGRESSION_THRESHOLDS.warningPercentIncrease).toBe(10);
        expect(DEFAULT_REGRESSION_THRESHOLDS.errorPercentIncrease).toBe(20);
        expect(DEFAULT_REGRESSION_THRESHOLDS.rollingAverageWindow).toBe(5);
      });
    });
  });

  describe("MemoryRegressionResult type", () => {
    it("should have all required fields", () => {
      const result: MemoryRegressionResult = {
        status: "warning",
        message: "Memory increased by 15%",
        currentPeakMB: 115,
        previousPeakMB: 100,
        rollingAverageMB: 100,
        percentChangeFromLast: 15,
        percentChangeFromAverage: 15,
      };

      expect(result.status).toBe("warning");
      expect(result.currentPeakMB).toBe(115);
      expect(result.percentChangeFromLast).toBe(15);
    });
  });
});
