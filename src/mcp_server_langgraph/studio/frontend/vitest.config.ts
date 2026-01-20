import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";
import os from "os";

// =============================================================================
// Adaptive Resource Configuration
// =============================================================================
// Similar to pytest-xdist's -n auto, but memory-aware for Node.js/jsdom
//
// Each fork worker with jsdom uses ~200-400MB. We calculate max workers based on:
// 1. Available CPUs (like pytest -n auto)
// 2. Available memory (unlike pytest, Node.js/jsdom is memory-hungry)
// 3. Environment overrides for CI/containers
//
// Environment variables (in priority order):
//   VITEST_MAX_FORKS=N          - Explicit worker count
//   VITEST_MAX_WORKERS=N        - Alias for max workers
//   CI=true                     - Use conservative settings for CI
//
// Memory Monitoring:
//   VITEST_MEMORY_MONITOR=true  - Enable memory snapshot tracking
//   VITEST_MEMORY_VERBOSE=true  - Print full memory report after tests
//   DEBUG=true                  - Also enables memory monitoring
//
// Memory Threshold Customization (all values in MB):
//   VITEST_MEMORY_WARNING_MB=512  - Heap usage warning threshold (default: 512)
//   VITEST_MEMORY_ERROR_MB=1024   - Heap usage error threshold (default: 1024)
//   VITEST_MEMORY_DELTA_MB=50     - Delta warning threshold (default: 50)
//
// Default thresholds (configured in src/test/memoryMonitor.ts):
//   - Warning at 512MB heap usage
//   - Error at 1GB heap usage
//   - Delta warning at 50MB growth between snapshots
// =============================================================================

function getOptimalWorkerCount(): number {
  // Priority 1: Explicit environment variable
  const envWorkers =
    process.env.VITEST_MAX_FORKS || process.env.VITEST_MAX_WORKERS;
  if (envWorkers) {
    const parsed = parseInt(envWorkers, 10);
    if (!isNaN(parsed) && parsed > 0) {
      return parsed;
    }
  }

  // Get system resources
  const cpuCount = os.availableParallelism?.() ?? os.cpus().length;
  const totalMemoryGB = os.totalmem() / 1024 / 1024 / 1024;
  const freeMemoryGB = os.freemem() / 1024 / 1024 / 1024;

  // Estimate ~300MB per fork worker (jsdom + React Testing Library overhead)
  const memoryPerWorkerGB = 0.3;

  // Calculate memory-based limit: use at most 50% of free memory for workers
  const memoryBasedLimit = Math.floor((freeMemoryGB * 0.5) / memoryPerWorkerGB);

  // CPU-based limit: use 50% of CPUs in watch mode, 75% otherwise
  const isWatch = !process.argv.includes("--run");
  const cpuBasedLimit = Math.floor(cpuCount * (isWatch ? 0.5 : 0.75));

  // CI environments: be more conservative
  const isCI =
    process.env.CI === "true" || process.env.GITHUB_ACTIONS === "true";
  const ciLimit = isCI ? Math.min(4, cpuCount) : Infinity;

  // Take the minimum of all limits, with a floor of 1 and ceiling of 2
  // Reduced from 4 to 2 to prevent heap OOM during test execution
  // Some test files create many mocks which accumulate and cause OOM
  const optimal = Math.max(
    1,
    Math.min(
      cpuBasedLimit,
      memoryBasedLimit,
      ciLimit,
      2, // Never use more than 2 workers regardless of resources (OOM prevention)
    ),
  );

  // Log for debugging (only in verbose mode)
  if (process.env.DEBUG || process.env.VITEST_DEBUG) {
    console.log(
      `[vitest-config] Resources: ${cpuCount} CPUs, ${totalMemoryGB.toFixed(1)}GB total, ${freeMemoryGB.toFixed(1)}GB free`,
    );
    console.log(
      `[vitest-config] Limits: CPU=${cpuBasedLimit}, Memory=${memoryBasedLimit}, CI=${ciLimit}`,
    );
    console.log(`[vitest-config] Using ${optimal} workers`);
  }

  return optimal;
}

const maxWorkers = getOptimalWorkerCount();

// =============================================================================
// Heap Size Configuration
// =============================================================================
// Get heap size from environment or use adaptive defaults:
// - CI (7GB runner): 4096MB per worker with 1-2 workers = ~8GB max
// - Local development: 8192MB per worker
//
// Environment variables:
//   VITEST_HEAP_SIZE=<MB>  - Explicit heap size in MB
// =============================================================================
function getHeapSizeMB(): string {
  // Priority 1: Explicit environment variable
  if (process.env.VITEST_HEAP_SIZE) {
    return process.env.VITEST_HEAP_SIZE;
  }

  // Priority 2: Infer from NODE_OPTIONS if --max-old-space-size is set
  // This allows sharding scripts to control heap via NODE_OPTIONS
  const nodeOptions = process.env.NODE_OPTIONS ?? "";
  const heapMatch = nodeOptions.match(/--max-old-space-size=(\d+)/);
  if (heapMatch?.[1]) {
    return heapMatch[1];
  }

  // Priority 3: CI environments use smaller heap to fit 7GB runner
  const isCI =
    process.env.CI === "true" || process.env.GITHUB_ACTIONS === "true";
  if (isCI) {
    return "4096"; // 4GB per worker - safe for 7GB runner with 1 worker
  }

  // Priority 4: Local development uses moderate heap
  // Reduced from 16GB to 8GB to fail faster on OOM during sharded runs
  return "8192"; // 8GB per worker for local development
}

const heapSizeMB = getHeapSizeMB();

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      // Mock PWA virtual modules for testing
      "virtual:pwa-register/react": path.resolve(
        __dirname,
        "./src/mocks/pwa-register-react.ts",
      ),
      "virtual:pwa-register": path.resolve(
        __dirname,
        "./src/mocks/pwa-register.ts",
      ),
      // Mock Sandpack to avoid Stitches CSS-in-JS incompatibility with jsdom 27
      // Stitches uses CSS syntax like '--sxs{--sxs:6}' that @acemir/cssom cannot parse
      "@codesandbox/sandpack-react": path.resolve(
        __dirname,
        "./src/mocks/components/sandpack-react.ts",
      ),
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    environmentOptions: {
      jsdom: {
        // Set base URL for jsdom to allow RTK Query's relative URL resolution
        url: "http://localhost:3000",
      },
    },
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}", "tests/**/*.{test,spec}.{ts,tsx}"],

    // =========================================================================
    // Pool Configuration - Adaptive Resource Management
    // =========================================================================
    // Use forks pool for better isolation and stability with jsdom.
    // Vitest 4 removed tinypool, eliminating the orphan process issue.
    pool: "forks",

    // Vitest 4: forks options are now top-level under test.forks
    // singleFork: true ensures only one fork runs at a time
    // This prevents OOM when running multiple test files together
    // Trade-off: slower execution but guaranteed memory safety
    // Override with VITEST_SINGLE_FORK=false to enable parallel forks
    forks: {
      singleFork: process.env.VITEST_SINGLE_FORK !== "false",
    },

    // Vitest 4: execArgv is a top-level option that applies to all worker processes
    // Per-worker heap limits to prevent OOM in individual workers
    // Heap size is environment-aware:
    //   - CI (7GB runner): 4GB per worker - fits 7GB runner with 1-2 workers
    //   - Local: 8GB per worker - allows complex test files with many mocks
    // Override with VITEST_HEAP_SIZE=<MB> environment variable
    execArgv: [`--max-old-space-size=${heapSizeMB}`],

    // Each test file gets its own environment (better isolation)
    isolate: true,

    // Limit parallel workers based on available resources
    // This is the key setting that controls resource usage!
    maxWorkers,
    minWorkers: 1, // Start with 1 worker, scale up as needed

    // Limit concurrent tests within a single file to reduce memory pressure
    maxConcurrency: 5,

    // Restart workers after running this many tests to prevent memory accumulation
    // This helps prevent OOM by recycling workers with fresh heap
    // Optimized from 1 to 3: Still safe with 4GB heap, but 3x less overhead
    // Memory calculation: 3 files × 400MB avg = 1.2GB max, well within 4GB limit
    restartWorkers: true,
    restartWorkersAfter: 3, // Restart after 3 test files (balance of safety + speed)

    // Teardown timeout - give workers time to clean up gracefully
    teardownTimeout: 10000, // Increased from 5s to 10s for GC time

    // Retry flaky tests once
    retry: 1,

    // Don't silence output
    silent: false,
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
      },
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.test.{ts,tsx}",
        "src/**/*.spec.{ts,tsx}",
        "src/test/**",
        "src/mocks/**",
        "src/main.tsx",
        "src/vite-env.d.ts",
        "src/types/**",
        "src/**/index.ts",
      ],
    },
    testTimeout: 10000,
    hookTimeout: 10000,
  },
});
