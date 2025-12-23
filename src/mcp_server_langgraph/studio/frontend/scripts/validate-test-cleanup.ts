#!/usr/bin/env npx tsx
/**
 * Test Cleanup Validation Script
 *
 * Validates that all frontend test files have proper memory safety cleanup patterns.
 * Run as part of pre-commit hook to prevent memory leaks in the test suite.
 *
 * Usage:
 *   npx tsx scripts/validate-test-cleanup.ts
 *   npx tsx scripts/validate-test-cleanup.ts --fix  # Auto-fix issues (not yet implemented)
 *
 * Exit codes:
 *   0 - All tests have proper cleanup
 *   1 - Some tests are missing cleanup patterns
 */

import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";
import { glob } from "glob";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

interface ValidationResult {
  file: string;
  issues: string[];
  hasAfterEach: boolean;
  hasCleanup: boolean;
  hasClearMocks: boolean;
  usesFakeTimers: boolean;
  hasTimerCleanup: boolean;
}

interface ValidationSummary {
  total: number;
  passed: number;
  failed: number;
  issues: ValidationResult[];
}

const SRC_DIR = path.resolve(__dirname, "../src");

/**
 * Check if a test file has proper cleanup patterns
 */
function validateTestFile(filePath: string): ValidationResult {
  const content = fs.readFileSync(filePath, "utf-8");
  const issues: string[] = [];

  // Check for afterEach block
  const hasAfterEach = /afterEach\s*\(/.test(content);

  // Check for cleanup() call (RTL cleanup)
  const hasCleanup = /cleanup\s*\(\s*\)/.test(content);

  // Check for vi.clearAllMocks() or vi.restoreAllMocks()
  const hasClearMocks =
    /vi\.clearAllMocks\s*\(\s*\)/.test(content) ||
    /vi\.restoreAllMocks\s*\(\s*\)/.test(content);

  // Check if file uses fake timers
  const usesFakeTimers = /vi\.useFakeTimers\s*\(\s*\)/.test(content);

  // Check for timer cleanup (vi.useRealTimers)
  const hasTimerCleanup = /vi\.useRealTimers\s*\(\s*\)/.test(content);

  // Determine issues
  if (!hasAfterEach) {
    issues.push("Missing afterEach block");
  }

  // For .tsx files (React components), check for cleanup()
  if (filePath.endsWith(".tsx") && !hasCleanup) {
    issues.push("Missing cleanup() call for React component tests");
  }

  if (!hasClearMocks) {
    issues.push("Missing vi.clearAllMocks() or vi.restoreAllMocks()");
  }

  if (usesFakeTimers && !hasTimerCleanup) {
    issues.push("Uses vi.useFakeTimers() but missing vi.useRealTimers() cleanup");
  }

  return {
    file: path.relative(SRC_DIR, filePath),
    issues,
    hasAfterEach,
    hasCleanup,
    hasClearMocks,
    usesFakeTimers,
    hasTimerCleanup,
  };
}

/**
 * Find all test files in the frontend src directory
 */
async function findTestFiles(): Promise<string[]> {
  const pattern = path.join(SRC_DIR, "**/*.{test,spec}.{ts,tsx}");
  return glob(pattern, { ignore: ["**/node_modules/**"] });
}

/**
 * Main validation function
 */
async function validateAll(): Promise<ValidationSummary> {
  const testFiles = await findTestFiles();
  const results: ValidationResult[] = [];

  for (const file of testFiles) {
    const result = validateTestFile(file);
    if (result.issues.length > 0) {
      results.push(result);
    }
  }

  return {
    total: testFiles.length,
    passed: testFiles.length - results.length,
    failed: results.length,
    issues: results,
  };
}

/**
 * Print validation report
 */
function printReport(summary: ValidationSummary): void {
  console.log("\n=== Frontend Test Cleanup Validation ===\n");
  console.log(`Total files: ${summary.total}`);
  console.log(`Passed: ${summary.passed}`);
  console.log(`Failed: ${summary.failed}`);
  console.log(`Compliance: ${((summary.passed / summary.total) * 100).toFixed(1)}%\n`);

  if (summary.issues.length > 0) {
    console.log("=== Issues Found ===\n");

    // Group by issue type
    const byIssue: Record<string, string[]> = {};
    for (const result of summary.issues) {
      for (const issue of result.issues) {
        if (!byIssue[issue]) {
          byIssue[issue] = [];
        }
        byIssue[issue].push(result.file);
      }
    }

    for (const [issue, files] of Object.entries(byIssue)) {
      console.log(`${issue} (${files.length} files):`);
      for (const file of files) {
        console.log(`  - ${file}`);
      }
      console.log();
    }

    console.log("=== Required Pattern ===\n");
    console.log(`For .tsx files (React components):

  import { cleanup } from "@testing-library/react";
  import { vi, afterEach } from "vitest";

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

For .ts files (non-React):

  import { vi, afterEach } from "vitest";

  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

If using fake timers, add:

  vi.useRealTimers();
`);
  }
}

/**
 * Main entry point
 */
async function main(): Promise<void> {
  try {
    const summary = await validateAll();
    printReport(summary);

    if (summary.failed > 0) {
      console.log("\nValidation FAILED: Some test files are missing cleanup patterns.");
      console.log("Please fix the issues above to prevent memory leaks.\n");
      process.exit(1);
    } else {
      console.log("\nValidation PASSED: All test files have proper cleanup patterns.\n");
      process.exit(0);
    }
  } catch (error) {
    console.error("Error running validation:", error);
    process.exit(1);
  }
}

main();
