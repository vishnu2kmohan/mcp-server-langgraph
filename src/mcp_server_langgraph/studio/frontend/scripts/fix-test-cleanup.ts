#!/usr/bin/env npx tsx
/**
 * Test Cleanup Fix Script
 *
 * Auto-fix for missing test cleanup patterns.
 *
 * Usage:
 *   npx tsx scripts/fix-test-cleanup.ts
 *   npx tsx scripts/fix-test-cleanup.ts --dry-run
 *   npx tsx scripts/fix-test-cleanup.ts --verbose
 *
 * Patterns added:
 *   - For .tsx files: import { cleanup } from "@testing-library/react"
 *   - For all test files: import { vi, afterEach } from "vitest"
 *   - afterEach(() => { cleanup(); vi.clearAllMocks(); })
 *
 * Security:
 *   - Only processes files in src directory
 *   - Path validation prevents directory traversal
 */

import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";
import { glob } from "glob";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Configuration
const SRC_DIR = path.resolve(__dirname, "../src");
const FRONTEND_ROOT = path.resolve(__dirname, "..");

// Parse command line arguments
const args = process.argv.slice(2);
const DRY_RUN = args.includes("--dry-run");
const VERBOSE = args.includes("--verbose");

// =============================================================================
// Path Security
// =============================================================================

function isPathSafe(filePath: string): boolean {
  // Resolve symlinks to prevent escaping src directory
  let realPath: string;
  let realSrcDir: string;

  try {
    realPath = fs.realpathSync(filePath);
    realSrcDir = fs.realpathSync(SRC_DIR) + path.sep;
  } catch {
    // File doesn't exist or can't be resolved - not safe
    return false;
  }

  // Ensure resolved path is strictly within SRC_DIR (with separator boundary)
  if (!realPath.startsWith(realSrcDir)) {
    return false;
  }

  if (!realPath.match(/\.test\.(ts|tsx)$/)) {
    return false;
  }

  // Extra check for path traversal attempts in original input
  if (filePath.includes("..")) {
    return false;
  }

  return true;
}

// =============================================================================
// Detection Helpers
// =============================================================================

interface TestFileState {
  hasAfterEach: boolean;
  hasCleanupImport: boolean;
  hasCleanupCall: boolean;
  hasViImport: boolean;
  hasAfterEachImport: boolean;
  hasClearMocks: boolean;
  isTsxFile: boolean;
}

function analyzeFile(content: string, filePath: string): TestFileState {
  const isTsxFile = filePath.endsWith(".tsx");

  return {
    hasAfterEach: /afterEach\s*\(/.test(content),
    hasCleanupImport:
      /@testing-library\/react/.test(content) && /\bcleanup\b/.test(content),
    hasCleanupCall: /cleanup\s*\(\s*\)/.test(content),
    hasViImport:
      /from\s+["']vitest["']/.test(content) && /\bvi\b/.test(content),
    hasAfterEachImport:
      /from\s+["']vitest["']/.test(content) && /\bafterEach\b/.test(content),
    hasClearMocks:
      /vi\.clearAllMocks\s*\(\s*\)/.test(content) ||
      /vi\.restoreAllMocks\s*\(\s*\)/.test(content),
    isTsxFile,
  };
}

function needsFix(state: TestFileState): boolean {
  if (!state.hasAfterEach || !state.hasClearMocks) {
    return true;
  }

  if (state.isTsxFile && (!state.hasCleanupImport || !state.hasCleanupCall)) {
    return true;
  }

  return false;
}

// =============================================================================
// Import Helpers
// =============================================================================

/**
 * Add or merge named imports to an existing import statement
 */
function mergeNamedImports(importLine: string, newNames: string[]): string {
  const match = importLine.match(/import\s*\{([^}]+)\}/);
  if (!match) return importLine;

  const existingNames = match[1]
    .split(",")
    .map((n) => n.trim())
    .filter(Boolean);

  const allNames = new Set([...existingNames, ...newNames]);
  const sortedNames = Array.from(allNames).sort();

  return importLine.replace(/\{[^}]+\}/, `{ ${sortedNames.join(", ")} }`);
}

/**
 * Find the position to insert new imports (after last import)
 * Handles multi-line imports by tracking import blocks until semicolon
 */
function findImportInsertPosition(content: string): number {
  let lastImportEnd = 0;
  let offset = 0;
  let inImport = false;

  for (const line of content.split("\n")) {
    if (/^import\b/.test(line)) {
      inImport = true;
    }
    if (inImport && /;\s*$/.test(line)) {
      lastImportEnd = offset + line.length;
      inImport = false;
    }
    offset += line.length + 1; // +1 for newline
  }

  return lastImportEnd;
}

/**
 * Find the position to insert afterEach (after imports, before first describe/it/test)
 */
function findAfterEachInsertPosition(content: string): number {
  const importPos = findImportInsertPosition(content);

  const testBlockRegex = /^(describe|it|test)\s*\(/gm;
  testBlockRegex.lastIndex = importPos;
  const match = testBlockRegex.exec(content);

  if (match) {
    const beforeMatch = content.substring(0, match.index);
    const lastNewline = beforeMatch.lastIndexOf("\n");
    return lastNewline >= importPos ? lastNewline : importPos;
  }

  return importPos;
}

// =============================================================================
// Fix Application
// =============================================================================

function applyFixes(content: string, filePath: string): string | null {
  const state = analyzeFile(content, filePath);

  if (!needsFix(state)) {
    return null;
  }

  let result = content;
  const changes: string[] = [];

  // Fix vitest imports
  const vitestImportMatch = result.match(
    /^(import\s*\{[^}]+\}\s*from\s*["']vitest["'];?)$/m,
  );

  if (vitestImportMatch) {
    const neededNames: string[] = [];
    if (!state.hasViImport) neededNames.push("vi");
    if (!state.hasAfterEachImport) neededNames.push("afterEach");

    if (neededNames.length > 0) {
      const updatedImport = mergeNamedImports(
        vitestImportMatch[0],
        neededNames,
      );
      result = result.replace(vitestImportMatch[0], updatedImport);
      changes.push(`Added ${neededNames.join(", ")} to vitest import`);
    }
  } else if (!state.hasViImport || !state.hasAfterEachImport) {
    const insertPos = findImportInsertPosition(result);
    const newImport = '\nimport { afterEach, vi } from "vitest";';
    result =
      result.substring(0, insertPos) + newImport + result.substring(insertPos);
    changes.push("Added vitest import");
  }

  // Fix @testing-library/react import for TSX files
  if (state.isTsxFile && !state.hasCleanupImport) {
    const rtlImportMatch = result.match(
      /^(import\s*\{[^}]+\}\s*from\s*["']@testing-library\/react["'];?)$/m,
    );

    if (rtlImportMatch) {
      const updatedImport = mergeNamedImports(rtlImportMatch[0], ["cleanup"]);
      result = result.replace(rtlImportMatch[0], updatedImport);
      changes.push("Added cleanup to @testing-library/react import");
    } else {
      const insertPos = findImportInsertPosition(result);
      const newImport = '\nimport { cleanup } from "@testing-library/react";';
      result =
        result.substring(0, insertPos) +
        newImport +
        result.substring(insertPos);
      changes.push("Added @testing-library/react import");
    }
  }

  // Add afterEach block if missing
  if (!state.hasAfterEach) {
    const insertPos = findAfterEachInsertPosition(result);

    const afterEachBlock = state.isTsxFile
      ? `

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
`
      : `

afterEach(() => {
  vi.clearAllMocks();
});
`;

    result =
      result.substring(0, insertPos) +
      afterEachBlock +
      result.substring(insertPos);
    changes.push("Added afterEach block");
  } else if (
    !state.hasClearMocks ||
    (state.isTsxFile && !state.hasCleanupCall)
  ) {
    // File has afterEach but missing cleanup() or vi.clearAllMocks()
    // Add a supplementary afterEach block with the missing calls
    const insertPos = findAfterEachInsertPosition(result);
    const supplementaryBlock = state.isTsxFile
      ? `

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
`
      : `

afterEach(() => {
  vi.clearAllMocks();
});
`;
    result =
      result.substring(0, insertPos) +
      supplementaryBlock +
      result.substring(insertPos);
    changes.push(
      "Added supplementary afterEach for missing cleanup/clearAllMocks",
    );
  }

  if (changes.length === 0) {
    return null;
  }

  return result;
}

// =============================================================================
// Main Execution
// =============================================================================

interface FixResult {
  file: string;
  fixed: boolean;
  changes: string[];
  error?: string;
}

async function findTestFiles(): Promise<string[]> {
  const tsxPattern = path.join(SRC_DIR, "**/*.test.tsx");
  const tsPattern = path.join(SRC_DIR, "**/*.test.ts");

  const [tsxFiles, tsFiles] = await Promise.all([
    glob(tsxPattern, { ignore: ["**/node_modules/**"] }),
    glob(tsPattern, { ignore: ["**/node_modules/**"] }),
  ]);

  return [...tsxFiles, ...tsFiles].filter(isPathSafe);
}

async function fixFiles(): Promise<FixResult[]> {
  const files = await findTestFiles();
  const results: FixResult[] = [];

  for (const file of files) {
    const result: FixResult = {
      file: path.relative(FRONTEND_ROOT, file),
      fixed: false,
      changes: [],
    };

    try {
      const content = fs.readFileSync(file, "utf-8");
      const state = analyzeFile(content, file);

      if (!needsFix(state)) {
        continue;
      }

      if (!state.hasAfterEach) result.changes.push("Add afterEach block");
      if (!state.hasViImport) result.changes.push("Add vi import");
      if (!state.hasAfterEachImport)
        result.changes.push("Add afterEach import");
      if (state.isTsxFile && !state.hasCleanupImport) {
        result.changes.push("Add cleanup import");
      }
      if (!state.hasClearMocks) result.changes.push("Add vi.clearAllMocks()");
      if (state.isTsxFile && !state.hasCleanupCall) {
        result.changes.push("Add cleanup()");
      }

      const fixedContent = applyFixes(content, file);

      if (fixedContent && fixedContent !== content) {
        if (!DRY_RUN) {
          fs.writeFileSync(file, fixedContent, "utf-8");
        }
        result.fixed = true;
        results.push(result);
      }
    } catch (error) {
      result.error = String(error);
      results.push(result);
    }
  }

  return results;
}

async function main(): Promise<void> {
  console.log("\n=== Frontend Test Cleanup Fix ===\n");

  if (DRY_RUN) {
    console.log("Mode: DRY RUN (no files will be modified)\n");
  }

  const results = await fixFiles();

  if (results.length === 0) {
    console.log("No files need fixing. All test files have proper cleanup.\n");
    process.exit(0);
  }

  const fixed = results.filter((r) => r.fixed);
  const errors = results.filter((r) => r.error);

  if (fixed.length > 0) {
    console.log(`${DRY_RUN ? "Would fix" : "Fixed"} ${fixed.length} files:\n`);
    for (const result of fixed) {
      console.log(`  ${result.file}`);
      if (VERBOSE) {
        for (const change of result.changes) {
          console.log(`    - ${change}`);
        }
      }
    }
    console.log();
  }

  if (errors.length > 0) {
    console.log(`Errors in ${errors.length} files:\n`);
    for (const result of errors) {
      console.log(`  ${result.file}: ${result.error}`);
    }
    console.log();
    process.exit(1);
  }

  if (DRY_RUN) {
    console.log("Run without --dry-run to apply fixes.\n");
  } else {
    console.log("Done! Run validate:test-cleanup to verify.\n");
  }

  process.exit(0);
}

main().catch((error) => {
  console.error("Error:", error);
  process.exit(1);
});
