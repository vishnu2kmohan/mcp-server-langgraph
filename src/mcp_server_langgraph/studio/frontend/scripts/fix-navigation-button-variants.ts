#!/usr/bin/env npx tsx
/**
 * Fix Navigation Button Variants
 *
 * Automatically adds variant="ghost" to Button components inside navigation contexts
 * that are missing the variant prop.
 *
 * Per STYLE.md: Navigation buttons (inside <nav>, sidebar, tabs) should use variant="ghost"
 *
 * Usage:
 *   npx tsx scripts/fix-navigation-button-variants.ts [options]
 *
 * Options:
 *   --dry-run     Show what would be changed without modifying files
 *   --verbose     Show detailed output for each fix
 *   --file <path> Fix only a specific file
 *
 * Examples:
 *   npx tsx scripts/fix-navigation-button-variants.ts --dry-run
 *   npx tsx scripts/fix-navigation-button-variants.ts --verbose
 *   npx tsx scripts/fix-navigation-button-variants.ts --file src/layout/MobileDrawer.tsx
 */

import * as fs from "fs";
import * as path from "path";
import { execSync } from "child_process";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_DIR = path.join(__dirname, "../src");

// =============================================================================
// Configuration
// =============================================================================

interface FixConfig {
  dryRun: boolean;
  verbose: boolean;
  targetFile?: string;
}

interface FixResult {
  file: string;
  fixes: number;
  details: string[];
}

// Files/patterns to exclude from fixes (specialized components)
const EXCLUSIONS = [
  "StepProgress.tsx",      // Specialized progress indicator
  "Pagination.tsx",        // Pagination has different semantics
  "SegmentedControl.tsx",  // Segment buttons are not navigation
  "*.test.tsx",
  "*.stories.tsx",
  "**/components/UI/**",
];

// =============================================================================
// Fix Patterns
// =============================================================================

/**
 * Pattern 1: Buttons inside <nav> elements without variant
 * Adds variant="ghost" after the opening <Button
 */
function fixButtonsInNav(content: string, verbose: boolean): { content: string; fixes: number; details: string[] } {
  let fixes = 0;
  const details: string[] = [];

  // Match <nav> blocks and fix buttons inside them
  const navBlockRegex = /(<nav[^>]*>)([\s\S]*?)(<\/nav>)/g;

  const newContent = content.replace(navBlockRegex, (match, openTag, innerContent, closeTag) => {
    // Find Button components without variant prop inside nav
    const buttonRegex = /<Button\b(?![^>]*\bvariant=)([^>]*?)(\s*(?:>|$))/g;

    const fixedInner = innerContent.replace(buttonRegex, (buttonMatch: string, attrs: string, ending: string) => {
      // Skip if already has variant (shouldn't match but safety check)
      if (attrs.includes("variant=")) {
        return buttonMatch;
      }

      fixes++;
      if (verbose) {
        const preview = buttonMatch.slice(0, 60).replace(/\n/g, " ");
        details.push(`  Nav button: ${preview}...`);
      }

      // Add variant="ghost" after <Button
      return `<Button variant="ghost"${attrs}${ending}`;
    });

    return openTag + fixedInner + closeTag;
  });

  return { content: newContent, fixes, details };
}

/**
 * Pattern 2: Buttons inside role="tablist" without variant
 */
function fixButtonsInTablist(content: string, verbose: boolean): { content: string; fixes: number; details: string[] } {
  let fixes = 0;
  const details: string[] = [];

  // Match tablist blocks
  const tablistRegex = /(<[^>]*role=["']tablist["'][^>]*>)([\s\S]*?)(<\/[^>]+>)/g;

  const newContent = content.replace(tablistRegex, (match, openTag, innerContent, closeTag) => {
    const buttonRegex = /<Button\b(?![^>]*\bvariant=)([^>]*?)(\s*(?:>|$))/g;

    const fixedInner = innerContent.replace(buttonRegex, (buttonMatch: string, attrs: string, ending: string) => {
      if (attrs.includes("variant=")) {
        return buttonMatch;
      }

      fixes++;
      if (verbose) {
        const preview = buttonMatch.slice(0, 60).replace(/\n/g, " ");
        details.push(`  Tablist button: ${preview}...`);
      }

      return `<Button variant="ghost"${attrs}${ending}`;
    });

    return openTag + fixedInner + closeTag;
  });

  return { content: newContent, fixes, details };
}

/**
 * Pattern 3: Primary CTA buttons with bg-primary styling but no variant
 * These should have variant="primary"
 */
function fixPrimaryCtaButtons(content: string, verbose: boolean): { content: string; fixes: number; details: string[] } {
  let fixes = 0;
  const details: string[] = [];

  // Match Button with bg-primary-9/10/11 in className but no variant
  // This pattern finds: <Button ... className="... bg-primary-9 ..." ...>
  const ctaButtonRegex = /<Button\b(?![^>]*\bvariant=)([^>]*className=["'][^"']*bg-primary-(?:9|10|11)[^"']*["'][^>]*)>/g;

  const newContent = content.replace(ctaButtonRegex, (match, attrs) => {
    fixes++;
    if (verbose) {
      const preview = match.slice(0, 60).replace(/\n/g, " ");
      details.push(`  Primary CTA: ${preview}...`);
    }

    return `<Button variant="primary"${attrs}>`;
  });

  return { content: newContent, fixes, details };
}

/**
 * Pattern 4: Danger buttons with bg-error styling but no variant
 */
function fixDangerButtons(content: string, verbose: boolean): { content: string; fixes: number; details: string[] } {
  let fixes = 0;
  const details: string[] = [];

  // Match Button with bg-error in className but no variant
  const dangerButtonRegex = /<Button\b(?![^>]*\bvariant=)([^>]*className=["'][^"']*bg-error-[^"']*["'][^>]*)>/g;

  const newContent = content.replace(dangerButtonRegex, (match, attrs) => {
    fixes++;
    if (verbose) {
      const preview = match.slice(0, 60).replace(/\n/g, " ");
      details.push(`  Danger button: ${preview}...`);
    }

    return `<Button variant="danger"${attrs}>`;
  });

  return { content: newContent, fixes, details };
}

// =============================================================================
// File Processing
// =============================================================================

function shouldProcessFile(filePath: string): boolean {
  const fileName = path.basename(filePath);

  for (const exclusion of EXCLUSIONS) {
    if (exclusion.startsWith("**/")) {
      // Directory pattern
      const dirPattern = exclusion.slice(3);
      if (filePath.includes(dirPattern)) {
        return false;
      }
    } else if (exclusion.startsWith("*.")) {
      // Extension pattern
      if (fileName.endsWith(exclusion.slice(1))) {
        return false;
      }
    } else {
      // Exact filename
      if (fileName === exclusion) {
        return false;
      }
    }
  }

  return true;
}

function findTsxFiles(dir: string): string[] {
  const files: string[] = [];

  try {
    const cmd = `find ${dir} -name "*.tsx" -type f 2>/dev/null`;
    const result = execSync(cmd, { encoding: "utf-8" }).trim();
    if (result) {
      files.push(...result.split("\n").filter(Boolean));
    }
  } catch {
    // Fallback: manual directory traversal
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        files.push(...findTsxFiles(fullPath));
      } else if (entry.name.endsWith(".tsx")) {
        files.push(fullPath);
      }
    }
  }

  return files;
}

function processFile(filePath: string, config: FixConfig): FixResult | null {
  if (!shouldProcessFile(filePath)) {
    return null;
  }

  const content = fs.readFileSync(filePath, "utf-8");
  let currentContent = content;
  let totalFixes = 0;
  const allDetails: string[] = [];

  // Apply all fix patterns
  const patterns = [
    fixButtonsInNav,
    fixButtonsInTablist,
    fixPrimaryCtaButtons,
    fixDangerButtons,
  ];

  for (const pattern of patterns) {
    const result = pattern(currentContent, config.verbose);
    currentContent = result.content;
    totalFixes += result.fixes;
    allDetails.push(...result.details);
  }

  if (totalFixes === 0) {
    return null;
  }

  // Write changes if not dry run
  if (!config.dryRun) {
    fs.writeFileSync(filePath, currentContent, "utf-8");
  }

  const relativePath = path.relative(path.join(__dirname, ".."), filePath);
  return {
    file: relativePath,
    fixes: totalFixes,
    details: allDetails,
  };
}

// =============================================================================
// Main
// =============================================================================

function parseArgs(): FixConfig {
  const args = process.argv.slice(2);
  const config: FixConfig = {
    dryRun: args.includes("--dry-run"),
    verbose: args.includes("--verbose"),
  };

  const fileIndex = args.indexOf("--file");
  if (fileIndex !== -1 && args[fileIndex + 1]) {
    config.targetFile = args[fileIndex + 1];
  }

  return config;
}

function main() {
  const config = parseArgs();

  console.log("\n========================================");
  console.log("   Fix Navigation Button Variants");
  console.log("========================================\n");

  if (config.dryRun) {
    console.log("🔍 DRY RUN MODE - No files will be modified\n");
  }

  let filesToProcess: string[];

  if (config.targetFile) {
    const targetPath = path.resolve(config.targetFile);
    if (!fs.existsSync(targetPath)) {
      console.error(`ERROR: File not found: ${config.targetFile}`);
      process.exit(1);
    }
    filesToProcess = [targetPath];
  } else {
    filesToProcess = findTsxFiles(SRC_DIR);
  }

  console.log(`Scanning ${filesToProcess.length} files...\n`);

  const results: FixResult[] = [];
  let totalFixes = 0;

  for (const file of filesToProcess) {
    const result = processFile(file, config);
    if (result) {
      results.push(result);
      totalFixes += result.fixes;

      console.log(`✓ ${result.file}: ${result.fixes} fix(es)`);
      if (config.verbose && result.details.length > 0) {
        for (const detail of result.details) {
          console.log(detail);
        }
      }
    }
  }

  console.log("\n----------------------------------------");
  console.log("Summary:");
  console.log(`  Files fixed:   ${results.length}`);
  console.log(`  Total fixes:   ${totalFixes}`);
  console.log("----------------------------------------\n");

  if (config.dryRun && totalFixes > 0) {
    console.log("Run without --dry-run to apply these fixes.\n");
  }

  if (totalFixes > 0) {
    console.log("Next steps:");
    console.log("  1. Run: npm run check:design-system");
    console.log("  2. Run: npm test");
    console.log("  3. Review changes: git diff\n");
  }
}

main();
