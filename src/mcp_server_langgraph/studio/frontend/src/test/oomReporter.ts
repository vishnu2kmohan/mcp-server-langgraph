/**
 * OOM Reporter - Main-process Vitest reporter for OOM detection
 *
 * Runs in the main/coordinator process as a custom Vitest reporter.
 * Tracks module lifecycle via onTestModuleStart/onTestModuleEnd to detect:
 *   1. High-memory files — per-file heap from diagnostic().heap
 *   2. OOM suspects — modules that started but never ended (worker died)
 *
 * Complements (not replaces) memoryMonitor.ts (worker-side per-test snapshots)
 * and memoryTrendReporter.ts (CI trend tracking). This reporter runs in the
 * main process and provides module-level granularity.
 *
 * Output format:
 *   [MEMORY] <path>: <heap>MB heap (duration: <s>s)
 *   [MEMORY] <path>: <heap>MB heap (duration: <s>s) ⚠ HIGH
 *   [OOM-SUSPECT] <path>: started but never completed (likely OOM/timeout)
 *   [MEMORY-SUMMARY] N file(s) exceeded <threshold>MB heap threshold
 */

export interface OomReporterOptions {
  /** Min heap (MB) to log [MEMORY] line, default 256 */
  reportThresholdMB?: number;
  /** Threshold (MB) for ⚠ HIGH marker, default 500 */
  highMemoryThresholdMB?: number;
}

export interface CompletedModule {
  path: string;
  heapMB: number;
  durationS: number;
  isHigh: boolean;
}

/**
 * Minimal interface for the TestModule methods we use.
 * Avoids importing vitest/node in the worker (this file runs in main process).
 */
interface TestModuleLike {
  moduleId: string;
  relativeModuleId: string;
  diagnostic: () => {
    heap?: number;
    duration?: number;
  };
}

export default class OomReporter {
  private reportThresholdMB: number;
  private highMemoryThresholdMB: number;
  private startedModules = new Map<string, string>(); // moduleId -> relativePath
  private completedModules: CompletedModule[] = [];

  constructor(options?: OomReporterOptions) {
    this.reportThresholdMB = options?.reportThresholdMB ?? 256;
    this.highMemoryThresholdMB = options?.highMemoryThresholdMB ?? 500;
  }

  /**
   * Reset state at the start of each test run.
   * Prevents accumulation across watch-mode re-runs.
   */
  onTestRunStart(): void {
    this.startedModules.clear();
    this.completedModules = [];
  }

  onTestModuleStart(testModule: TestModuleLike): void {
    const path = testModule.relativeModuleId;
    this.startedModules.set(testModule.moduleId, path);
  }

  onTestModuleEnd(testModule: TestModuleLike): void {
    const path = testModule.relativeModuleId;
    const diag = testModule.diagnostic();

    // Remove from started (it completed)
    this.startedModules.delete(testModule.moduleId);

    // Compute heap in MB (0 if logHeapUsage not enabled)
    const heapMB = diag.heap ? diag.heap / (1024 * 1024) : 0;
    const durationS = (diag.duration ?? 0) / 1000;
    const isHigh = heapMB >= this.highMemoryThresholdMB;

    this.completedModules.push({ path, heapMB, durationS, isHigh });

    // Log [MEMORY] line if above threshold or in verbose mode
    const shouldLog =
      heapMB >= this.reportThresholdMB ||
      process.env.VITEST_MEMORY_VERBOSE === "true";

    if (shouldLog) {
      const line = formatMemoryLine(
        path,
        Math.round(heapMB),
        parseFloat(durationS.toFixed(1)),
        isHigh,
      );
      console.log(line);
    }
  }

  onTestRunEnd(
    _testModules: unknown,
    _unhandledErrors: unknown,
    _reason: unknown,
  ): void {
    // Log OOM suspects: modules that started but never completed
    const suspects = Array.from(this.startedModules.values());
    for (const path of suspects) {
      console.log(formatOomSuspectLine(path));
    }

    // Log summary of high-memory files
    const highMemFiles = this.completedModules.filter((m) => m.isHigh);
    if (highMemFiles.length > 0) {
      console.log(
        `[MEMORY-SUMMARY] ${highMemFiles.length} file(s) exceeded ${this.highMemoryThresholdMB}MB heap threshold`,
      );
    }
  }

  getReport(): { completed: CompletedModule[]; suspects: string[] } {
    return {
      completed: [...this.completedModules],
      suspects: Array.from(this.startedModules.values()),
    };
  }
}

/**
 * Format a [MEMORY] line for a completed module.
 */
export function formatMemoryLine(
  path: string,
  heapMB: number,
  durationS: number,
  isHigh: boolean,
): string {
  const base = `[MEMORY] ${path}: ${heapMB}MB heap (duration: ${durationS.toFixed(1)}s)`;
  return isHigh ? `${base} ⚠ HIGH` : base;
}

/**
 * Format an [OOM-SUSPECT] line for a module that started but never completed.
 */
export function formatOomSuspectLine(path: string): string {
  return `[OOM-SUSPECT] ${path}: started but never completed (likely OOM/timeout)`;
}
