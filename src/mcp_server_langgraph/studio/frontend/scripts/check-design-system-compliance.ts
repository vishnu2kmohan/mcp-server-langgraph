#!/usr/bin/env npx tsx
/**
 * Design System Compliance Check
 *
 * Scans the codebase and reports metrics on design system adoption.
 * Outputs JSON metrics for CI dashboards and tracking.
 *
 * Usage:
 *   npx tsx scripts/check-design-system-compliance.ts
 *   npm run check:design-system
 *
 * Metrics tracked:
 * - Raw HTML element usage vs design system components
 * - Form element adoption (Checkbox, RadioGroup, Toggle)
 * - Gray vs neutral color usage
 * - Storybook coverage for UI components
 */

import { execSync } from "child_process";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const UI_DIR = path.join(__dirname, "../src/components/UI");

interface ComplianceMetrics {
  timestamp: string;
  rawElements: {
    button: number;
    input: number;
    select: number;
    textarea: number;
  };
  designSystemComponents: {
    Button: number;
    Input: number;
    SearchInput: number;
    Checkbox: number;
    RadioGroup: number;
    Toggle: number;
    Select: number;
    Textarea: number;
  };
  colors: {
    grayUsage: number;
    neutralUsage: number;
  };
  storybook: {
    totalComponents: number;
    withStories: number;
    coveragePercent: number;
  };
  adoption: {
    buttonAdoptionPercent: number;
    formAdoptionPercent: number;
    colorAdoptionPercent: number;
    storybookCoveragePercent: number;
    overallScore: number;
  };
}

function countRgMatches(pattern: string, glob?: string, excludePatterns?: string[]): number {
  try {
    const globArg = glob ? `-g '${glob}'` : "";
    const excludeArgs = excludePatterns ? excludePatterns.map((p) => `-g '!${p}'`).join(" ") : "";
    // Use single quotes around pattern to prevent shell interpretation of regex chars
    const escapedPattern = pattern.replace(/'/g, "'\\''");
    const cmd = `rg -c '${escapedPattern}' src/ ${globArg} ${excludeArgs} 2>/dev/null | awk -F: '{sum += \$2} END {print sum}'`;
    const result = execSync(cmd, { encoding: "utf-8", cwd: path.join(__dirname, "..") }).trim();
    return parseInt(result, 10) || 0;
  } catch {
    return 0;
  }
}

// Standard exclusions for production code metrics
// Excludes: tests, stories, UI component definitions, contexts (JSDoc examples), canvas (native handlers)
const PROD_EXCLUSIONS = [
  "*.test.tsx",
  "*.stories.tsx",
  "**/components/UI/**",
  "**/contexts/**",
  "**/canvas/**",
];

function countStorybookCoverage(): { total: number; covered: number } {
  try {
    const files = fs.readdirSync(UI_DIR);
    const components = files
      .filter((f) => f.endsWith(".tsx"))
      .filter((f) => !f.includes(".test."))
      .filter((f) => !f.includes(".stories."))
      .filter((f) => f !== "index.tsx")
      .map((f) => f.replace(".tsx", ""));

    const stories = files
      .filter((f) => f.endsWith(".stories.tsx"))
      .map((f) => f.replace(".stories.tsx", ""));

    const covered = components.filter((c) => stories.includes(c)).length;
    return { total: components.length, covered };
  } catch {
    return { total: 0, covered: 0 };
  }
}

function calculateMetrics(): ComplianceMetrics {
  // Count raw HTML elements (excluding test files, stories, and UI component definitions)
  const rawButton = countRgMatches("<button", "*.tsx", PROD_EXCLUSIONS);
  const rawInput = countRgMatches("<input", "*.tsx", PROD_EXCLUSIONS);
  const rawSelect = countRgMatches("<select", "*.tsx", PROD_EXCLUSIONS);
  const rawTextarea = countRgMatches("<textarea", "*.tsx", PROD_EXCLUSIONS);

  // Count design system component usage (same exclusions for fair comparison)
  // Use \b word boundary instead of [^a-zA-Z] for shell compatibility
  const buttonComponent = countRgMatches("<Button\\b", "*.tsx", PROD_EXCLUSIONS);
  const inputComponent = countRgMatches("<Input\\b", "*.tsx", PROD_EXCLUSIONS);
  const searchInputComponent = countRgMatches("<SearchInput\\b", "*.tsx", PROD_EXCLUSIONS);
  const checkboxComponent = countRgMatches("<Checkbox\\b", "*.tsx", PROD_EXCLUSIONS);
  const radioGroupComponent = countRgMatches("<RadioGroup\\b", "*.tsx", PROD_EXCLUSIONS);
  const toggleComponent = countRgMatches("<Toggle\\b", "*.tsx", PROD_EXCLUSIONS);
  const selectComponent = countRgMatches("<Select\\b", "*.tsx", PROD_EXCLUSIONS);
  const textareaComponent = countRgMatches("<Textarea\\b", "*.tsx", PROD_EXCLUSIONS);

  // Count color usage
  const grayUsage = countRgMatches("gray-\\d+", "*.tsx");
  const neutralUsage = countRgMatches("neutral-\\d+", "*.tsx");

  // Count Storybook coverage
  const storybookStats = countStorybookCoverage();

  // Calculate adoption percentages
  const totalButtons = Math.max(rawButton + buttonComponent, 1);
  const buttonAdoptionPercent = Math.round((buttonComponent / totalButtons) * 100);

  const totalFormElements = Math.max(
    rawInput +
      rawSelect +
      rawTextarea +
      inputComponent +
      checkboxComponent +
      radioGroupComponent +
      toggleComponent +
      selectComponent +
      textareaComponent,
    1
  );
  const adoptedFormElements =
    inputComponent + checkboxComponent + radioGroupComponent + toggleComponent + selectComponent + textareaComponent;
  const formAdoptionPercent = Math.round((adoptedFormElements / totalFormElements) * 100);

  const totalColors = Math.max(grayUsage + neutralUsage, 1);
  const colorAdoptionPercent = Math.round((neutralUsage / totalColors) * 100);

  const storybookCoveragePercent = storybookStats.total > 0
    ? Math.round((storybookStats.covered / storybookStats.total) * 100)
    : 0;

  // Overall score (weighted average)
  const overallScore = Math.round(
    buttonAdoptionPercent * 0.3 +
      formAdoptionPercent * 0.3 +
      colorAdoptionPercent * 0.2 +
      storybookCoveragePercent * 0.2
  );

  return {
    timestamp: new Date().toISOString(),
    rawElements: {
      button: Math.max(rawButton, 0),
      input: Math.max(rawInput, 0),
      select: Math.max(rawSelect, 0),
      textarea: Math.max(rawTextarea, 0),
    },
    designSystemComponents: {
      Button: buttonComponent,
      Input: inputComponent,
      SearchInput: searchInputComponent,
      Checkbox: checkboxComponent,
      RadioGroup: radioGroupComponent,
      Toggle: toggleComponent,
      Select: selectComponent,
      Textarea: textareaComponent,
    },
    colors: {
      grayUsage,
      neutralUsage,
    },
    storybook: {
      totalComponents: storybookStats.total,
      withStories: storybookStats.covered,
      coveragePercent: storybookCoveragePercent,
    },
    adoption: {
      buttonAdoptionPercent,
      formAdoptionPercent,
      colorAdoptionPercent,
      storybookCoveragePercent,
      overallScore,
    },
  };
}

function printReport(metrics: ComplianceMetrics): void {
  console.log("\n========================================");
  console.log("   Design System Compliance Report");
  console.log("========================================\n");

  console.log("Raw HTML Elements (should decrease):");
  console.log(`  <button>:   ${metrics.rawElements.button}`);
  console.log(`  <input>:    ${metrics.rawElements.input}`);
  console.log(`  <select>:   ${metrics.rawElements.select}`);
  console.log(`  <textarea>: ${metrics.rawElements.textarea}`);

  console.log("\nDesign System Components (should increase):");
  console.log(`  <Button>:      ${metrics.designSystemComponents.Button}`);
  console.log(`  <Input>:       ${metrics.designSystemComponents.Input}`);
  console.log(`  <SearchInput>: ${metrics.designSystemComponents.SearchInput}`);
  console.log(`  <Checkbox>:    ${metrics.designSystemComponents.Checkbox}`);
  console.log(`  <RadioGroup>:  ${metrics.designSystemComponents.RadioGroup}`);
  console.log(`  <Toggle>:      ${metrics.designSystemComponents.Toggle}`);
  console.log(`  <Select>:      ${metrics.designSystemComponents.Select}`);
  console.log(`  <Textarea>:    ${metrics.designSystemComponents.Textarea}`);

  console.log("\nColor Usage:");
  console.log(`  gray-*:    ${metrics.colors.grayUsage}`);
  console.log(`  neutral-*: ${metrics.colors.neutralUsage}`);

  console.log("\nStorybook Coverage:");
  console.log(`  Components:  ${metrics.storybook.withStories}/${metrics.storybook.totalComponents}`);
  console.log(`  Coverage:    ${metrics.storybook.coveragePercent}%`);

  console.log("\n----------------------------------------");
  console.log("Adoption Metrics:");
  console.log(`  Button adoption:     ${metrics.adoption.buttonAdoptionPercent}%`);
  console.log(`  Form adoption:       ${metrics.adoption.formAdoptionPercent}%`);
  console.log(`  Color adoption:      ${metrics.adoption.colorAdoptionPercent}%`);
  console.log(`  Storybook coverage:  ${metrics.adoption.storybookCoveragePercent}%`);
  console.log(`  Overall score:       ${metrics.adoption.overallScore}%`);
  console.log("----------------------------------------\n");

  // Output JSON for CI
  if (process.env.CI || process.argv.includes("--json")) {
    console.log("JSON Output:");
    console.log(JSON.stringify(metrics, null, 2));
  }
}

// Main execution
const metrics = calculateMetrics();
printReport(metrics);

// Exit with non-zero if adoption is critically low (for CI enforcement)
if (process.argv.includes("--strict") && metrics.adoption.overallScore < 50) {
  console.error("ERROR: Design system adoption is below 50%");
  process.exit(1);
}
