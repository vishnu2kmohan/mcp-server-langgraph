/**
 * Memory Monitor for Vitest
 *
 * Provides utilities for tracking heap memory usage during test runs
 * to detect memory leaks and excessive allocation.
 *
 * Usage:
 *   import { memoryMonitor } from './memoryMonitor';
 *
 *   beforeAll(() => memoryMonitor.snapshot('suite-start'));
 *   afterAll(() => {
 *     memoryMonitor.snapshot('suite-end');
 *     console.log(memoryMonitor.generateReport());
 *   });
 */

// =============================================================================
// Types
// =============================================================================

export interface MemoryStats {
  heapUsed: number;
  heapTotal: number;
  external: number;
  rss: number;
  arrayBuffers: number;
}

export interface MemorySnapshot {
  label: string;
  timestamp: number;
  heapUsed: number;
  heapTotal: number;
  external: number;
  rss: number;
}

export interface MemoryDelta {
  fromLabel: string;
  toLabel: string;
  heapUsedDelta: number;
  heapTotalDelta: number;
  externalDelta: number;
  rssDelta: number;
  durationMs: number;
}

export interface MemoryThresholds {
  /** Heap used warning threshold in MB */
  heapUsedWarningMB: number;
  /** Heap used error threshold in MB */
  heapUsedErrorMB: number;
  /** Delta warning threshold in MB (for leak detection) */
  deltaWarningMB?: number;
}

export interface ThresholdCheckResult {
  warnings: string[];
  errors: string[];
  passed: boolean;
}

export interface MemoryMonitorOptions {
  /** Enable/disable monitoring (default: true in DEBUG mode) */
  enabled?: boolean;
  /** Threshold configuration */
  thresholds?: MemoryThresholds;
  /** Whether to log snapshots as they're taken */
  verbose?: boolean;
}

// =============================================================================
// Utilities
// =============================================================================

const BYTES_UNITS = ["B", "KB", "MB", "GB", "TB"];

/**
 * Format bytes to human-readable string
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";

  const isNegative = bytes < 0;
  const absBytes = Math.abs(bytes);

  const k = 1024;
  const i = Math.floor(Math.log(absBytes) / Math.log(k));
  const value = absBytes / Math.pow(k, i);

  const formatted = `${value.toFixed(2)} ${BYTES_UNITS[i]}`;
  return isNegative ? `-${formatted}` : formatted;
}

/**
 * Get current memory statistics from Node.js
 */
export function getMemoryStats(): MemoryStats {
  const memUsage = process.memoryUsage();
  return {
    heapUsed: memUsage.heapUsed,
    heapTotal: memUsage.heapTotal,
    external: memUsage.external,
    rss: memUsage.rss,
    arrayBuffers: memUsage.arrayBuffers,
  };
}

// =============================================================================
// Memory Monitor Class
// =============================================================================

const DEFAULT_THRESHOLDS: MemoryThresholds = {
  heapUsedWarningMB: 512, // 512MB warning
  heapUsedErrorMB: 1024, // 1GB error
  deltaWarningMB: 50, // 50MB delta between snapshots
};

/**
 * Parse a positive number from environment variable
 * Returns undefined if invalid, empty, zero, or negative
 */
function parseEnvNumber(value: string | undefined): number | undefined {
  if (!value || value.trim() === "") return undefined;
  const num = parseFloat(value);
  if (isNaN(num) || num <= 0) return undefined;
  return num;
}

/**
 * Get thresholds from environment variables
 * Environment variables:
 *   VITEST_MEMORY_WARNING_MB - Heap usage warning threshold in MB
 *   VITEST_MEMORY_ERROR_MB - Heap usage error threshold in MB
 *   VITEST_MEMORY_DELTA_MB - Delta warning threshold in MB
 */
function getThresholdsFromEnv(): Partial<MemoryThresholds> {
  return {
    heapUsedWarningMB: parseEnvNumber(process.env.VITEST_MEMORY_WARNING_MB),
    heapUsedErrorMB: parseEnvNumber(process.env.VITEST_MEMORY_ERROR_MB),
    deltaWarningMB: parseEnvNumber(process.env.VITEST_MEMORY_DELTA_MB),
  };
}

export class MemoryMonitor {
  private snapshots: MemorySnapshot[] = [];
  private enabled: boolean;
  private thresholds: MemoryThresholds;
  private verbose: boolean;

  constructor(options: MemoryMonitorOptions = {}) {
    // Enable by default in debug mode or when explicitly enabled
    this.enabled =
      options.enabled ??
      (process.env.DEBUG === "true" ||
        process.env.VITEST_MEMORY_MONITOR === "true");

    // Priority: explicit options > environment variables > defaults
    if (options.thresholds) {
      this.thresholds = options.thresholds;
    } else {
      const envThresholds = getThresholdsFromEnv();
      this.thresholds = {
        heapUsedWarningMB:
          envThresholds.heapUsedWarningMB ??
          DEFAULT_THRESHOLDS.heapUsedWarningMB,
        heapUsedErrorMB:
          envThresholds.heapUsedErrorMB ?? DEFAULT_THRESHOLDS.heapUsedErrorMB,
        deltaWarningMB:
          envThresholds.deltaWarningMB ?? DEFAULT_THRESHOLDS.deltaWarningMB,
      };
    }

    this.verbose = options.verbose ?? false;
  }

  /**
   * Get current threshold configuration
   */
  getThresholds(): MemoryThresholds {
    return { ...this.thresholds };
  }

  /**
   * Take a memory snapshot with a label
   */
  snapshot(label: string): MemorySnapshot | null {
    if (!this.enabled) return null;

    const stats = getMemoryStats();
    const snap: MemorySnapshot = {
      label,
      timestamp: Date.now(),
      heapUsed: stats.heapUsed,
      heapTotal: stats.heapTotal,
      external: stats.external,
      rss: stats.rss,
    };

    this.snapshots.push(snap);

    if (this.verbose) {
      console.log(
        `[MemoryMonitor] ${label}: heap=${formatBytes(snap.heapUsed)}, ` +
          `total=${formatBytes(snap.heapTotal)}, rss=${formatBytes(snap.rss)}`,
      );
    }

    return snap;
  }

  /**
   * Get all recorded snapshots
   */
  getSnapshots(): MemorySnapshot[] {
    return [...this.snapshots];
  }

  /**
   * Calculate delta between two labeled snapshots
   */
  getDelta(fromLabel: string, toLabel: string): MemoryDelta | null {
    const from = this.snapshots.find((s) => s.label === fromLabel);
    const to = this.snapshots.find((s) => s.label === toLabel);

    if (!from || !to) return null;

    return {
      fromLabel,
      toLabel,
      heapUsedDelta: to.heapUsed - from.heapUsed,
      heapTotalDelta: to.heapTotal - from.heapTotal,
      externalDelta: to.external - from.external,
      rssDelta: to.rss - from.rss,
      durationMs: to.timestamp - from.timestamp,
    };
  }

  /**
   * Check current memory against thresholds
   */
  checkThresholds(): ThresholdCheckResult {
    const stats = getMemoryStats();
    const warnings: string[] = [];
    const errors: string[] = [];

    const heapUsedMB = stats.heapUsed / (1024 * 1024);

    if (heapUsedMB >= this.thresholds.heapUsedErrorMB) {
      errors.push(
        `Heap used (${heapUsedMB.toFixed(1)}MB) exceeds error threshold ` +
          `(${this.thresholds.heapUsedErrorMB}MB)`,
      );
    } else if (heapUsedMB >= this.thresholds.heapUsedWarningMB) {
      warnings.push(
        `Heap used (${heapUsedMB.toFixed(1)}MB) exceeds warning threshold ` +
          `(${this.thresholds.heapUsedWarningMB}MB)`,
      );
    }

    // Check delta if we have multiple snapshots
    if (this.snapshots.length >= 2 && this.thresholds.deltaWarningMB) {
      const first = this.snapshots[0];
      const last = this.snapshots[this.snapshots.length - 1];
      const deltaMB = (last.heapUsed - first.heapUsed) / (1024 * 1024);

      if (deltaMB >= this.thresholds.deltaWarningMB) {
        warnings.push(
          `Heap grew by ${deltaMB.toFixed(1)}MB from "${first.label}" to ` +
            `"${last.label}" (threshold: ${this.thresholds.deltaWarningMB}MB)`,
        );
      }
    }

    return {
      warnings,
      errors,
      passed: errors.length === 0,
    };
  }

  /**
   * Reset all snapshots
   */
  reset(): void {
    this.snapshots = [];
  }

  /**
   * Generate a text report of all snapshots
   */
  generateReport(): string {
    if (this.snapshots.length === 0) {
      return "Memory Report: No snapshots recorded";
    }

    const lines: string[] = [];
    lines.push("=".repeat(60));
    lines.push("Memory Report");
    lines.push("=".repeat(60));
    lines.push("");

    // Snapshot details
    lines.push("Snapshots:");
    lines.push("-".repeat(40));

    for (const snap of this.snapshots) {
      lines.push(
        `  ${snap.label}:`,
        `    Heap Used:  ${formatBytes(snap.heapUsed)}`,
        `    Heap Total: ${formatBytes(snap.heapTotal)}`,
        `    RSS:        ${formatBytes(snap.rss)}`,
        `    External:   ${formatBytes(snap.external)}`,
        "",
      );
    }

    // Overall delta
    if (this.snapshots.length >= 2) {
      const first = this.snapshots[0];
      const last = this.snapshots[this.snapshots.length - 1];
      const delta = this.getDelta(first.label, last.label);

      if (delta) {
        lines.push("Overall Change:");
        lines.push("-".repeat(40));
        lines.push(`  From: ${delta.fromLabel} → To: ${delta.toLabel}`);
        lines.push(`  Heap Used Delta:  ${formatBytes(delta.heapUsedDelta)}`);
        lines.push(`  Heap Total Delta: ${formatBytes(delta.heapTotalDelta)}`);
        lines.push(`  RSS Delta:        ${formatBytes(delta.rssDelta)}`);
        lines.push(`  Duration:         ${delta.durationMs}ms`);
      }
    }

    lines.push("");
    lines.push("=".repeat(60));

    return lines.join("\n");
  }

  /**
   * Enable or disable monitoring
   */
  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
  }

  /**
   * Check if monitoring is enabled
   */
  isEnabled(): boolean {
    return this.enabled;
  }
}

// =============================================================================
// Global Instance
// =============================================================================

/**
 * Global memory monitor instance for use across test files
 * Enable with: VITEST_MEMORY_MONITOR=true or DEBUG=true
 */
export const memoryMonitor = new MemoryMonitor();

// =============================================================================
// Vitest Integration Helpers
// =============================================================================

/**
 * Create a beforeAll/afterAll pair for automatic memory monitoring
 * @example
 * const { beforeAllHook, afterAllHook } = createMemoryHooks('MyTestSuite');
 * beforeAll(beforeAllHook);
 * afterAll(afterAllHook);
 */
export function createMemoryHooks(suiteName: string) {
  const startLabel = `${suiteName}-start`;
  const endLabel = `${suiteName}-end`;

  return {
    beforeAllHook: () => {
      memoryMonitor.snapshot(startLabel);
    },
    afterAllHook: () => {
      memoryMonitor.snapshot(endLabel);
      const delta = memoryMonitor.getDelta(startLabel, endLabel);
      if (delta && Math.abs(delta.heapUsedDelta) > 10 * 1024 * 1024) {
        // Log if delta > 10MB
        console.log(
          `[MemoryMonitor] ${suiteName}: heap delta = ${formatBytes(delta.heapUsedDelta)}`,
        );
      }
    },
  };
}
