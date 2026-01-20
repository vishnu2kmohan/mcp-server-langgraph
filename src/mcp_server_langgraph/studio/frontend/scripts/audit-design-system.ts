#!/usr/bin/env npx tsx
/**
 * Design System Consistency Audit
 *
 * Comprehensive audit tool that scans the frontend codebase for design system
 * violations. Uses ripgrep for efficient pattern matching.
 *
 * Usage:
 *   npx tsx scripts/audit-design-system.ts
 *   npm run audit:design-system
 *   npm run audit:design-system -- --json
 *   npm run audit:design-system -- --strict
 *   npm run audit:design-system -- --category=color
 *   npm run audit:design-system -- --auto-fix --dry-run
 *   npm run audit:design-system -- --auto-fix
 *
 * Categories:
 *   sizing, color, spacing, typography, border, shadow, zindex, animation
 *
 * Options:
 *   --json       Output JSON report for CI integration
 *   --strict     Exit with code 1 if any errors found
 *   --category   Audit only specified category
 *   --verbose    Show all matches with context
 *   --fix        Show suggested fixes (no auto-fix)
 *   --auto-fix   Automatically fix color violations (legacy neutrals, raw grays)
 *   --dry-run    Preview auto-fix changes without modifying files
 */

import { execSync } from "child_process";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";
import {
  RIPGREP_PATTERNS,
  EXCLUSION_PATTERNS,
  AUTO_FIX_MAPPINGS,
  type ViolationCategory,
  type ViolationSeverity,
  getSeverity,
  getSuggestion,
  categorizeViolation,
  isLegitimateSizing,
  isLegitimateSpacing,
  isLegitimateBorder,
  isLegitimateComponent,
  getAutoFix,
} from "./lib/audit-patterns";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_DIR = path.join(__dirname, "../src");

// =============================================================================
// Types
// =============================================================================

interface ViolationMatch {
  file: string;
  line: number;
  column: number;
  match: string;
  context: string;
}

interface CategoryReport {
  category: ViolationCategory;
  severity: ViolationSeverity;
  count: number;
  matches: ViolationMatch[];
}

interface AuditReport {
  timestamp: string;
  summary: {
    totalViolations: number;
    bySeverity: Record<ViolationSeverity, number>;
    byCategory: Record<ViolationCategory, number>;
  };
  categories: CategoryReport[];
  filesAffected: string[];
}

// =============================================================================
// CLI Argument Parsing
// =============================================================================

const args = process.argv.slice(2);
const flags = {
  json: args.includes("--json"),
  strict: args.includes("--strict"),
  verbose: args.includes("--verbose"),
  fix: args.includes("--fix"),
  autoFix: args.includes("--auto-fix"),
  dryRun: args.includes("--dry-run"),
  category: args.find((a) => a.startsWith("--category="))?.split("=")[1] as
    | ViolationCategory
    | undefined,
};

// =============================================================================
// Ripgrep Execution
// =============================================================================

/**
 * Execute ripgrep with a pattern and return matches
 */
function searchPattern(pattern: string): ViolationMatch[] {
  const exclusions = EXCLUSION_PATTERNS.map((p) => `-g "!${p}"`).join(" ");

  try {
    // Use ripgrep with JSON output for structured parsing
    // Escape single quotes in pattern for shell safety
    const escapedPattern = pattern.replace(/'/g, "'\"'\"'");
    const cmd = `rg --json -e '${escapedPattern}' ${exclusions} ${SRC_DIR} 2>/dev/null`;
    const output = execSync(cmd, { encoding: "utf-8", maxBuffer: 50 * 1024 * 1024 });

    const matches: ViolationMatch[] = [];
    const lines = output.trim().split("\n").filter(Boolean);

    for (const line of lines) {
      try {
        const json = JSON.parse(line);
        if (json.type === "match") {
          const data = json.data;
          const relativePath = path.relative(SRC_DIR, data.path.text);

          // Extract matched text
          const matchText =
            data.submatches?.[0]?.match?.text ||
            data.lines?.text?.trim() ||
            "";

          matches.push({
            file: relativePath,
            line: data.line_number,
            column: data.submatches?.[0]?.start || 0,
            match: matchText,
            context: data.lines?.text?.trim() || "",
          });
        }
      } catch {
        // Skip malformed JSON lines
      }
    }

    return matches;
  } catch {
    // No matches or error
    return [];
  }
}

/**
 * Run audit for a specific category
 */
function auditCategory(category: ViolationCategory): CategoryReport {
  const patterns = RIPGREP_PATTERNS[category];
  const allMatches: ViolationMatch[] = [];

  for (const pattern of patterns) {
    const matches = searchPattern(pattern);
    allMatches.push(...matches);
  }

  // Deduplicate by file:line
  const seen = new Set<string>();
  let uniqueMatches = allMatches.filter((m) => {
    const key = `${m.file}:${m.line}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  // Filter out legitimate patterns by category
  if (category === "sizing") {
    uniqueMatches = uniqueMatches.filter((m) => !isLegitimateSizing(m.context));
  }
  if (category === "spacing") {
    uniqueMatches = uniqueMatches.filter((m) => !isLegitimateSpacing(m.context));
  }
  if (category === "border") {
    uniqueMatches = uniqueMatches.filter((m) => !isLegitimateBorder(m.context));
  }
  if (category === "component") {
    uniqueMatches = uniqueMatches.filter((m) => !isLegitimateComponent(m.context));
  }

  return {
    category,
    severity: getSeverity(category),
    count: uniqueMatches.length,
    matches: uniqueMatches,
  };
}

/**
 * Run full audit across all categories
 */
function runAudit(): AuditReport {
  const categories: ViolationCategory[] = flags.category
    ? [flags.category]
    : ["sizing", "color", "spacing", "typography", "border", "shadow", "zindex", "animation", "component"];

  const categoryReports: CategoryReport[] = [];
  const allFiles = new Set<string>();

  for (const category of categories) {
    const report = auditCategory(category);
    categoryReports.push(report);
    report.matches.forEach((m) => allFiles.add(m.file));
  }

  // Calculate summary
  const bySeverity: Record<ViolationSeverity, number> = {
    error: 0,
    warning: 0,
    info: 0,
  };
  const byCategory: Record<ViolationCategory, number> = {
    sizing: 0,
    color: 0,
    spacing: 0,
    typography: 0,
    border: 0,
    shadow: 0,
    zindex: 0,
    animation: 0,
    component: 0,
  };

  let totalViolations = 0;
  for (const report of categoryReports) {
    totalViolations += report.count;
    bySeverity[report.severity] += report.count;
    byCategory[report.category] = report.count;
  }

  return {
    timestamp: new Date().toISOString(),
    summary: {
      totalViolations,
      bySeverity,
      byCategory,
    },
    categories: categoryReports,
    filesAffected: Array.from(allFiles).sort(),
  };
}

// =============================================================================
// Output Formatting
// =============================================================================

const COLORS = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  dim: "\x1b[2m",
  red: "\x1b[31m",
  yellow: "\x1b[33m",
  blue: "\x1b[34m",
  cyan: "\x1b[36m",
  green: "\x1b[32m",
  magenta: "\x1b[35m",
};

function severityColor(severity: ViolationSeverity): string {
  switch (severity) {
    case "error":
      return COLORS.red;
    case "warning":
      return COLORS.yellow;
    case "info":
      return COLORS.blue;
  }
}

function printConsoleReport(report: AuditReport): void {
  console.log("\n" + "=".repeat(60));
  console.log(`${COLORS.bold}   Design System Consistency Audit${COLORS.reset}`);
  console.log("=".repeat(60) + "\n");

  // Summary
  console.log(`${COLORS.bold}Summary:${COLORS.reset}`);
  console.log(`  Total violations: ${report.summary.totalViolations}`);
  console.log(
    `  ${COLORS.red}Errors:${COLORS.reset} ${report.summary.bySeverity.error}  ` +
    `${COLORS.yellow}Warnings:${COLORS.reset} ${report.summary.bySeverity.warning}  ` +
    `${COLORS.blue}Info:${COLORS.reset} ${report.summary.bySeverity.info}`
  );
  console.log(`  Files affected: ${report.filesAffected.length}\n`);

  // By category
  console.log(`${COLORS.bold}By Category:${COLORS.reset}`);
  for (const category of report.categories) {
    if (category.count === 0) continue;
    const color = severityColor(category.severity);
    const icon = category.severity === "error" ? "X" : category.severity === "warning" ? "!" : "i";
    console.log(
      `  ${color}[${icon}]${COLORS.reset} ${category.category}: ${category.count} violations`
    );
  }

  // Detailed matches (verbose mode or small count)
  const showDetails = flags.verbose || report.summary.totalViolations <= 20;
  if (showDetails && report.summary.totalViolations > 0) {
    console.log(`\n${COLORS.bold}Violations:${COLORS.reset}`);

    for (const category of report.categories) {
      if (category.count === 0) continue;

      console.log(`\n${COLORS.cyan}── ${category.category.toUpperCase()} ──${COLORS.reset}`);

      for (const match of category.matches.slice(0, flags.verbose ? Infinity : 10)) {
        const color = severityColor(category.severity);
        console.log(
          `  ${color}${match.file}:${match.line}${COLORS.reset} - ${COLORS.dim}${match.match}${COLORS.reset}`
        );

        if (flags.fix) {
          const catType = categorizeViolation(match.match);
          if (catType) {
            const suggestion = getSuggestion(match.match, catType);
            console.log(`    ${COLORS.green}Fix: ${suggestion}${COLORS.reset}`);
          }
        }
      }

      if (!flags.verbose && category.matches.length > 10) {
        console.log(
          `  ${COLORS.dim}... and ${category.matches.length - 10} more${COLORS.reset}`
        );
      }
    }
  } else if (report.summary.totalViolations > 20) {
    console.log(`\n${COLORS.dim}(Use --verbose to see all violations)${COLORS.reset}`);
  }

  // Top affected files
  if (report.filesAffected.length > 0) {
    console.log(`\n${COLORS.bold}Top Affected Files:${COLORS.reset}`);
    const fileCounts = new Map<string, number>();
    for (const cat of report.categories) {
      for (const match of cat.matches) {
        fileCounts.set(match.file, (fileCounts.get(match.file) || 0) + 1);
      }
    }
    const sorted = Array.from(fileCounts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10);

    for (const [file, count] of sorted) {
      console.log(`  ${file}: ${count} violations`);
    }
  }

  console.log("\n" + "-".repeat(60));

  // Exit guidance
  if (report.summary.bySeverity.error > 0) {
    console.log(
      `${COLORS.red}${COLORS.bold}Errors found.${COLORS.reset} ${COLORS.red}These should be fixed before merging.${COLORS.reset}`
    );
  } else if (report.summary.bySeverity.warning > 0) {
    console.log(
      `${COLORS.yellow}Warnings found.${COLORS.reset} Consider addressing these for consistency.`
    );
  } else if (report.summary.totalViolations === 0) {
    console.log(`${COLORS.green}No design system violations found!${COLORS.reset}`);
  }

  console.log("");
}

function printJsonReport(report: AuditReport): void {
  // Slim down for JSON output
  const slimReport = {
    ...report,
    categories: report.categories.map((c) => ({
      category: c.category,
      severity: c.severity,
      count: c.count,
      // Include first 100 matches to keep output manageable
      matches: c.matches.slice(0, 100).map((m) => ({
        file: m.file,
        line: m.line,
        match: m.match,
      })),
    })),
  };
  console.log(JSON.stringify(slimReport, null, 2));
}

// =============================================================================
// Main
// =============================================================================

const report = runAudit();

if (flags.json) {
  printJsonReport(report);
} else {
  printConsoleReport(report);
}

// =============================================================================
// Auto-Fix Execution
// =============================================================================

if (flags.autoFix) {
  console.log(`\n${COLORS.bold}Auto-Fix Mode${COLORS.reset}`);
  console.log("-".repeat(60));

  // Collect files that need fixing
  const filesToFix = new Map<string, Set<string>>();

  for (const category of report.categories) {
    for (const match of category.matches) {
      const autoFix = getAutoFix(match.context);
      if (autoFix) {
        if (!filesToFix.has(match.file)) {
          filesToFix.set(match.file, new Set());
        }
        filesToFix.get(match.file)!.add(autoFix.description);
      }
    }
  }

  if (filesToFix.size === 0) {
    console.log(`${COLORS.yellow}No auto-fixable violations found.${COLORS.reset}`);
    console.log("Only color violations (legacy neutrals, raw grays) can be auto-fixed.\n");
  } else {
    console.log(`Found ${filesToFix.size} files with auto-fixable violations:\n`);

    let totalFixes = 0;
    let filesFixed = 0;

    for (const [relativeFile, fixes] of filesToFix) {
      const absolutePath = path.join(SRC_DIR, relativeFile);

      if (!fs.existsSync(absolutePath)) {
        console.log(`  ${COLORS.yellow}Skip: ${relativeFile} (file not found)${COLORS.reset}`);
        continue;
      }

      let content = fs.readFileSync(absolutePath, "utf-8");
      let fixCount = 0;

      // Apply all auto-fix mappings
      for (const mapping of AUTO_FIX_MAPPINGS) {
        const before = content;
        content = content.replace(mapping.pattern, mapping.replacement);
        if (content !== before) {
          fixCount++;
        }
      }

      if (fixCount > 0) {
        if (flags.dryRun) {
          console.log(`  ${COLORS.cyan}Would fix: ${relativeFile}${COLORS.reset} (${fixCount} patterns)`);
        } else {
          fs.writeFileSync(absolutePath, content, "utf-8");
          console.log(`  ${COLORS.green}Fixed: ${relativeFile}${COLORS.reset} (${fixCount} patterns)`);
        }
        totalFixes += fixCount;
        filesFixed++;
      }
    }

    console.log("");
    if (flags.dryRun) {
      console.log(`${COLORS.cyan}Dry run complete.${COLORS.reset} Would fix ${totalFixes} patterns in ${filesFixed} files.`);
      console.log("Run without --dry-run to apply fixes.\n");
    } else {
      console.log(`${COLORS.green}Auto-fix complete.${COLORS.reset} Fixed ${totalFixes} patterns in ${filesFixed} files.`);
      console.log("Run the audit again to verify fixes.\n");
    }
  }
}

// Exit with error code if strict mode and errors found
if (flags.strict && report.summary.bySeverity.error > 0) {
  process.exit(1);
}
