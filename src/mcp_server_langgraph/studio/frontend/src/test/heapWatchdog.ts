/**
 * Heap Watchdog - Worker-side V8 heap monitoring
 *
 * Polls v8.getHeapStatistics() at a configurable interval and kills the worker
 * process before V8 enters a GC death spiral. Runs in the Vitest worker process,
 * wired via setup.ts.
 *
 * Activation: Only when VITEST_SHARDED=1 or VITEST_HEAP_WATCHDOG=true.
 * No overhead for interactive `npm test`.
 *
 * Output format (stderr):
 *   [HEAP WATCHDOG] <path>: <used>MB / <limit>MB (<pct>%) - KILLING WORKER
 */

import { getHeapStatistics } from "v8";

export interface HeapStats {
  usedMB: number;
  limitMB: number;
  percentage: number;
}

export interface HeapWatchdogOptions {
  /** Fraction 0-1, default 0.85 */
  threshold?: number;
  /** Polling interval in ms, default 2000 */
  pollIntervalMs?: number;
  /** Test file being monitored */
  filePath: string;
  /** Callback when threshold is exceeded */
  onThresholdExceeded?: (stats: HeapStats, filePath: string) => void;
}

export class HeapWatchdog {
  private threshold: number;
  private pollIntervalMs: number;
  private filePath: string;
  private onThresholdExceeded?: (stats: HeapStats, filePath: string) => void;
  private intervalId: ReturnType<typeof setInterval> | null = null;

  constructor(options: HeapWatchdogOptions) {
    this.threshold = options.threshold ?? 0.85;
    this.pollIntervalMs = options.pollIntervalMs ?? 2000;
    this.filePath = options.filePath;
    this.onThresholdExceeded = options.onThresholdExceeded;
  }

  start(): void {
    if (this.intervalId !== null) {
      return; // Already started
    }

    this.intervalId = setInterval(() => {
      this.poll();
    }, this.pollIntervalMs);
  }

  stop(): void {
    if (this.intervalId !== null) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  getHeapStats(): HeapStats {
    const stats = getHeapStatistics();
    const usedMB = stats.used_heap_size / (1024 * 1024);
    const limitMB = stats.heap_size_limit / (1024 * 1024);
    const percentage = (stats.used_heap_size / stats.heap_size_limit) * 100;

    return { usedMB, limitMB, percentage };
  }

  private poll(): void {
    const stats = this.getHeapStats();
    const fraction = stats.percentage / 100;

    if (fraction >= this.threshold && this.onThresholdExceeded) {
      this.onThresholdExceeded(stats, this.filePath);
    }
  }
}

/**
 * Format the structured log message written to stderr when the watchdog triggers.
 */
export function formatHeapWatchdogMessage(
  filePath: string,
  stats: HeapStats,
): string {
  const pct = stats.percentage.toFixed(1);
  return `[HEAP WATCHDOG] ${filePath}: ${Math.round(stats.usedMB)}MB / ${Math.round(stats.limitMB)}MB (${pct}%) - KILLING WORKER\n`;
}

/**
 * Factory function that creates a HeapWatchdog only when appropriate env vars are set.
 * Returns null for interactive `npm test` runs (no overhead).
 */
export function createHeapWatchdog(filePath: string): HeapWatchdog | null {
  const isSharded = process.env.VITEST_SHARDED === "1";
  const isExplicit = process.env.VITEST_HEAP_WATCHDOG === "true";

  if (!isSharded && !isExplicit) {
    return null;
  }

  return new HeapWatchdog({
    filePath,
    onThresholdExceeded: (stats, path) => {
      const message = formatHeapWatchdogMessage(path, stats);
      process.stderr.write(message);
      process.exit(137);
    },
  });
}
