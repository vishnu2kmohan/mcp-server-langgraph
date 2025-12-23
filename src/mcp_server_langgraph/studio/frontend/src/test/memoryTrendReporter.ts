/**
 * Memory Trend Reporter
 *
 * Utility for generating CI-compatible memory trend data that can be
 * published to the gh-pages dashboard for tracking memory usage over time.
 *
 * Usage:
 *   import { MemoryTrendReporter } from './memoryTrendReporter';
 *
 *   const reporter = new MemoryTrendReporter({ commit: 'abc123', branch: 'main' });
 *   reporter.recordEntry('suite-start', process.memoryUsage());
 *   reporter.recordEntry('suite-end', process.memoryUsage());
 *   const report = reporter.generateReport();
 *   console.log(JSON.stringify(report, null, 2));
 */

// =============================================================================
// Types
// =============================================================================

/**
 * Raw memory stats from Node.js process.memoryUsage()
 */
export interface RawMemoryStats {
  heapUsed: number;
  heapTotal: number;
  external: number;
  rss: number;
}

/**
 * A single memory trend entry (converted to MB for readability)
 */
export interface MemoryTrendEntry {
  /** Label for this measurement point */
  label: string;
  /** Timestamp in milliseconds */
  timestamp: number;
  /** Heap used in MB */
  heapUsedMB: number;
  /** Total heap size in MB */
  heapTotalMB: number;
  /** External memory in MB */
  externalMB: number;
  /** Resident set size in MB */
  rssMB: number;
  /** Change from previous entry in MB (undefined for first entry) */
  deltaMB?: number;
}

/**
 * Summary statistics for a memory trend report
 */
export interface MemoryTrendSummary {
  /** Peak heap used across all entries */
  peakHeapUsedMB: number;
  /** Final heap used (last entry) */
  finalHeapUsedMB: number;
  /** Total change from first to last entry */
  totalDeltaMB: number;
  /** Number of entries recorded */
  entryCount: number;
}

/**
 * Metadata for the memory trend report
 */
export interface MemoryTrendMetadata {
  /** When the report was generated */
  generatedAt: string;
  /** Git commit hash */
  commit?: string;
  /** Git branch name */
  branch?: string;
  /** Test suite name (e.g., 'frontend', 'backend') */
  testSuite?: string;
}

/**
 * Complete memory trend report
 */
export interface MemoryTrendReport {
  /** All recorded entries */
  entries: MemoryTrendEntry[];
  /** Summary statistics */
  summary: MemoryTrendSummary;
  /** Report metadata */
  metadata: MemoryTrendMetadata;
}

/**
 * A single run entry for the trends JSON file
 */
export interface MemoryTrendRunEntry {
  timestamp: string;
  peakHeapMB: number;
  finalHeapMB: number;
  deltaMB: number;
  commit: string;
  branch?: string;
  testSuite?: string;
}

/**
 * Structure of the memory-trends.json file on gh-pages
 */
export interface MemoryTrendsFile {
  runs: MemoryTrendRunEntry[];
  metadata: {
    created: string;
    updated: string;
  };
}

/**
 * Options for creating a MemoryTrendReporter
 */
export interface MemoryTrendReporterOptions {
  commit?: string;
  branch?: string;
  testSuite?: string;
}

/**
 * Thresholds for memory regression detection
 */
export interface MemoryRegressionThresholds {
  /** Percentage increase that triggers a warning (default: 10) */
  warningPercentIncrease: number;
  /** Percentage increase that triggers an error (default: 20) */
  errorPercentIncrease: number;
  /** Number of runs to include in rolling average (default: 5) */
  rollingAverageWindow: number;
}

/**
 * Result of memory regression detection
 */
export interface MemoryRegressionResult {
  /** Status: 'ok', 'warning', or 'error' */
  status: "ok" | "warning" | "error";
  /** Human-readable message */
  message: string;
  /** Current run's peak heap in MB */
  currentPeakMB: number;
  /** Previous run's peak heap in MB */
  previousPeakMB: number;
  /** Rolling average of previous runs in MB */
  rollingAverageMB: number;
  /** Percent change from last run */
  percentChangeFromLast: number;
  /** Percent change from rolling average */
  percentChangeFromAverage: number;
}

// =============================================================================
// Constants
// =============================================================================

const BYTES_TO_MB = 1 / (1024 * 1024);
const MAX_TREND_RUNS = 100;

/**
 * Default thresholds for memory regression detection
 */
export const DEFAULT_REGRESSION_THRESHOLDS: MemoryRegressionThresholds = {
  warningPercentIncrease: 10,
  errorPercentIncrease: 20,
  rollingAverageWindow: 5,
};

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Convert bytes to MB with 2 decimal places
 */
export function formatMemoryForCI(bytes: number): number {
  return Math.round(bytes * BYTES_TO_MB * 100) / 100;
}

/**
 * Parse existing trends JSON, returning empty structure if invalid
 */
export function parseExistingTrends(
  json: string | null | undefined,
): MemoryTrendsFile {
  const emptyResult: MemoryTrendsFile = {
    runs: [],
    metadata: {
      created: new Date().toISOString(),
      updated: new Date().toISOString(),
    },
  };

  if (!json) {
    return emptyResult;
  }

  try {
    const parsed = JSON.parse(json) as MemoryTrendsFile;
    if (!parsed.runs || !Array.isArray(parsed.runs)) {
      return emptyResult;
    }
    return parsed;
  } catch {
    return emptyResult;
  }
}

/**
 * Merge new run data with existing trends, keeping last MAX_TREND_RUNS entries
 */
export function mergeTrendData(
  existing: MemoryTrendsFile,
  newRun: MemoryTrendRunEntry,
): MemoryTrendsFile {
  const runs = [...existing.runs, newRun];

  // Keep only the last MAX_TREND_RUNS entries
  const trimmedRuns = runs.slice(-MAX_TREND_RUNS);

  return {
    runs: trimmedRuns,
    metadata: {
      created: existing.metadata.created,
      updated: new Date().toISOString(),
    },
  };
}

/**
 * Calculate rolling average of peak heap memory from runs
 * @param runs - Array of memory trend run entries
 * @param windowSize - Number of runs to include (defaults to all runs)
 * @returns Average peak heap in MB
 */
export function calculateRollingAverage(
  runs: MemoryTrendRunEntry[],
  windowSize?: number,
): number {
  if (runs.length === 0) {
    return 0;
  }

  // Use window size if specified, otherwise use all runs
  const effectiveRuns = windowSize ? runs.slice(-windowSize) : runs;

  const sum = effectiveRuns.reduce((acc, run) => acc + run.peakHeapMB, 0);
  return sum / effectiveRuns.length;
}

/**
 * Detect memory regression by comparing current run to previous runs
 * @param currentRun - The current test run's memory data
 * @param previousRuns - Array of previous runs to compare against
 * @param thresholds - Optional custom thresholds (defaults to DEFAULT_REGRESSION_THRESHOLDS)
 * @returns Regression detection result with status, message, and metrics
 */
export function detectMemoryRegression(
  currentRun: MemoryTrendRunEntry,
  previousRuns: MemoryTrendRunEntry[],
  thresholds: MemoryRegressionThresholds = DEFAULT_REGRESSION_THRESHOLDS,
): MemoryRegressionResult {
  const currentPeakMB = currentRun.peakHeapMB;

  // Handle case with no previous runs (first run / baseline)
  if (previousRuns.length === 0) {
    return {
      status: "ok",
      message: `First run establishing baseline at ${currentPeakMB.toFixed(1)}MB`,
      currentPeakMB,
      previousPeakMB: 0,
      rollingAverageMB: 0,
      percentChangeFromLast: 0,
      percentChangeFromAverage: 0,
    };
  }

  // Get the most recent previous run
  const lastRun = previousRuns[previousRuns.length - 1];
  const previousPeakMB = lastRun.peakHeapMB;

  // Calculate rolling average
  const rollingAverageMB = calculateRollingAverage(
    previousRuns,
    thresholds.rollingAverageWindow,
  );

  // Calculate percent changes (handle division by zero)
  const percentChangeFromLast =
    previousPeakMB > 0
      ? Math.round(
          ((currentPeakMB - previousPeakMB) / previousPeakMB) * 100 * 100,
        ) / 100
      : 0;

  const percentChangeFromAverage =
    rollingAverageMB > 0
      ? Math.round(
          ((currentPeakMB - rollingAverageMB) / rollingAverageMB) * 100 * 100,
        ) / 100
      : 0;

  // Determine status based on percent change from last run
  let status: "ok" | "warning" | "error";
  let message: string;

  if (percentChangeFromLast < 0) {
    // Memory decreased - this is good
    status = "ok";
    message = `Memory improved by ${Math.abs(percentChangeFromLast).toFixed(1)}% (${previousPeakMB.toFixed(1)}MB → ${currentPeakMB.toFixed(1)}MB)`;
  } else if (percentChangeFromLast >= thresholds.errorPercentIncrease) {
    status = "error";
    message = `Memory regression detected: +${percentChangeFromLast.toFixed(1)}% (${previousPeakMB.toFixed(1)}MB → ${currentPeakMB.toFixed(1)}MB). Exceeds error threshold of ${thresholds.errorPercentIncrease}%`;
  } else if (percentChangeFromLast >= thresholds.warningPercentIncrease) {
    status = "warning";
    message = `Memory increased by ${percentChangeFromLast.toFixed(1)}% (${previousPeakMB.toFixed(1)}MB → ${currentPeakMB.toFixed(1)}MB). Exceeds warning threshold of ${thresholds.warningPercentIncrease}%`;
  } else {
    status = "ok";
    message = `Memory stable at ${currentPeakMB.toFixed(1)}MB (${percentChangeFromLast >= 0 ? "+" : ""}${percentChangeFromLast.toFixed(1)}% from last run)`;
  }

  return {
    status,
    message,
    currentPeakMB,
    previousPeakMB,
    rollingAverageMB,
    percentChangeFromLast,
    percentChangeFromAverage,
  };
}

// =============================================================================
// MemoryTrendReporter Class
// =============================================================================

/**
 * Reporter for collecting and formatting memory trend data for CI
 */
export class MemoryTrendReporter {
  private entries: MemoryTrendEntry[] = [];
  private options: MemoryTrendReporterOptions;

  constructor(options: MemoryTrendReporterOptions = {}) {
    this.options = options;
  }

  /**
   * Record a memory entry at a labeled point
   */
  recordEntry(label: string, stats: RawMemoryStats): void {
    const heapUsedMB = formatMemoryForCI(stats.heapUsed);
    const heapTotalMB = formatMemoryForCI(stats.heapTotal);
    const externalMB = formatMemoryForCI(stats.external);
    const rssMB = formatMemoryForCI(stats.rss);

    // Calculate delta from previous entry
    let deltaMB: number | undefined;
    if (this.entries.length > 0) {
      const prevHeapUsed = this.entries[this.entries.length - 1].heapUsedMB;
      deltaMB = Math.round((heapUsedMB - prevHeapUsed) * 100) / 100;
    }

    const entry: MemoryTrendEntry = {
      label,
      timestamp: Date.now(),
      heapUsedMB,
      heapTotalMB,
      externalMB,
      rssMB,
      deltaMB,
    };

    this.entries.push(entry);
  }

  /**
   * Get all recorded entries
   */
  getEntries(): MemoryTrendEntry[] {
    return [...this.entries];
  }

  /**
   * Get the number of recorded entries
   */
  getEntryCount(): number {
    return this.entries.length;
  }

  /**
   * Generate a complete report with summary and metadata
   */
  generateReport(): MemoryTrendReport {
    const summary = this.calculateSummary();
    const metadata: MemoryTrendMetadata = {
      generatedAt: new Date().toISOString(),
      ...this.options,
    };

    return {
      entries: [...this.entries],
      summary,
      metadata,
    };
  }

  /**
   * Get the report as a JSON-serializable object
   */
  toJSON(): MemoryTrendReport {
    return this.generateReport();
  }

  /**
   * Reset the reporter, clearing all entries
   */
  reset(): void {
    this.entries = [];
  }

  /**
   * Convert the report to a run entry for the trends file
   */
  toRunEntry(): MemoryTrendRunEntry {
    const summary = this.calculateSummary();
    return {
      timestamp: new Date().toISOString(),
      peakHeapMB: summary.peakHeapUsedMB,
      finalHeapMB: summary.finalHeapUsedMB,
      deltaMB: summary.totalDeltaMB,
      commit: this.options.commit || "unknown",
      branch: this.options.branch,
      testSuite: this.options.testSuite,
    };
  }

  // ===========================================================================
  // Private Methods
  // ===========================================================================

  private calculateSummary(): MemoryTrendSummary {
    if (this.entries.length === 0) {
      return {
        peakHeapUsedMB: 0,
        finalHeapUsedMB: 0,
        totalDeltaMB: 0,
        entryCount: 0,
      };
    }

    const peakHeapUsedMB = Math.max(...this.entries.map((e) => e.heapUsedMB));
    const finalHeapUsedMB = this.entries[this.entries.length - 1].heapUsedMB;
    const firstHeapUsedMB = this.entries[0].heapUsedMB;
    const totalDeltaMB =
      Math.round((finalHeapUsedMB - firstHeapUsedMB) * 100) / 100;

    return {
      peakHeapUsedMB,
      finalHeapUsedMB,
      totalDeltaMB,
      entryCount: this.entries.length,
    };
  }
}

export default MemoryTrendReporter;
