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
  componentVariants: {
    buttonWithVariant: number;
    buttonWithoutVariant: number;
    buttonVariantCompliancePercent: number;
    cancelButtonsWithSecondary: number;
    cancelButtonsWithoutSecondary: number;
    destructiveButtonsWithDanger: number;
    destructiveButtonsWithoutDanger: number;
    iconButtonWithSizeIcon: number;
    iconButtonWithoutSizeIcon: number;
    iconButtonSizeCompliancePercent: number;
    buttonWithColorOverride: number;
    colorOverrideCompliancePercent: number;
  };
  fieldSizing: {
    inputWithSizeProp: number;
    inputWithSizingOverride: number;
    selectWithSizeProp: number;
    selectWithSizingOverride: number;
    textareaWithSizeProp: number;
    textareaWithSizingOverride: number;
    fieldSizingCompliancePercent: number;
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
    buttonVariantCompliancePercent: number;
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

  // Count Button variant compliance
  const buttonWithVariant = countRgMatches("<Button[^>]*\\bvariant=", "*.tsx", PROD_EXCLUSIONS);
  const buttonWithoutVariant = buttonComponent - buttonWithVariant;
  const buttonVariantCompliancePercent = Math.round(
    (buttonWithVariant / Math.max(buttonComponent, 1)) * 100
  );

  // Count Cancel/Close buttons with/without secondary variant
  const cancelButtonsWithSecondary = countRgMatches(
    '<Button[^>]*variant=["\']secondary["\'][^>]*>\\s*(Cancel|Close|Back|Dismiss|No)',
    "*.tsx",
    PROD_EXCLUSIONS
  );
  const cancelButtonsWithoutSecondary = countRgMatches(
    '<Button\\b(?![^>]*variant=)[^>]*>\\s*(Cancel|Close|Back|Dismiss|No)',
    "*.tsx",
    PROD_EXCLUSIONS
  );

  // Count destructive buttons with/without danger variant
  const destructiveButtonsWithDanger = countRgMatches(
    '<Button[^>]*variant=["\']danger["\'][^>]*>\\s*(Delete|Remove|Clear|Destroy|Discard)',
    "*.tsx",
    PROD_EXCLUSIONS
  );
  const destructiveButtonsWithoutDanger = countRgMatches(
    '<Button\\b(?![^>]*variant=)[^>]*>\\s*(Delete|Remove|Clear|Destroy|Discard)',
    "*.tsx",
    PROD_EXCLUSIONS
  );

  // Count icon-only buttons with/without size="icon"
  // Icon buttons should use size="icon" for proper touch target sizing (WCAG 2.2)
  // Using simpler pattern that works with shell escaping
  const iconButtonWithSizeIcon = countRgMatches(
    'size="icon"',
    "*.tsx",
    PROD_EXCLUSIONS
  );
  // Count all potential icon buttons (Button followed by icon-like component)
  // Then subtract those with size="icon" to estimate violations
  const allPotentialIconButtons = countRgMatches(
    '<Button[^>]*>\\s*<[A-Z]',
    "*.tsx",
    PROD_EXCLUSIONS
  );
  // Estimate: icon buttons without size="icon" = potential icon buttons - properly sized ones
  // This is an approximation since pattern matching is imperfect
  const iconButtonWithoutSizeIcon = Math.max(0, allPotentialIconButtons - iconButtonWithSizeIcon);
  const totalIconButtons = Math.max(iconButtonWithSizeIcon + iconButtonWithoutSizeIcon, 1);
  const iconButtonSizeCompliancePercent = Math.round(
    (iconButtonWithSizeIcon / totalIconButtons) * 100
  );

  // Count Button components with inline color className overrides
  // These bypass the variant system and should be avoided
  // Pattern matches Button with className containing color utilities: bg-*, text-*, border-* with color names
  const buttonWithColorOverride = countRgMatches(
    '<Button[^>]*className=[^>]*(bg-(primary|error|success|warning|insight|neutral)-|text-(primary|error|success|warning|insight|neutral)-|border-(primary|error|success|warning|insight|neutral)-)',
    "*.tsx",
    PROD_EXCLUSIONS
  );
  const colorOverrideCompliancePercent = buttonComponent > 0
    ? Math.round(((buttonComponent - buttonWithColorOverride) / buttonComponent) * 100)
    : 100;

  // Count field sizing compliance
  // Fields using size prop (proper) vs className overrides (violation)
  const inputWithSizeProp = countRgMatches(
    '<Input[^>]*\\bsize=',
    "*.tsx",
    PROD_EXCLUSIONS
  );
  const inputWithSizingOverride = countRgMatches(
    '<Input[^>]*className=[^>]*(py-\\d|px-\\d|h-\\d|text-(xs|sm|base|lg))',
    "*.tsx",
    PROD_EXCLUSIONS
  );
  const selectWithSizeProp = countRgMatches(
    '<Select[^>]*\\bsize=',
    "*.tsx",
    PROD_EXCLUSIONS
  );
  const selectWithSizingOverride = countRgMatches(
    '<Select[^>]*className=[^>]*(py-\\d|px-\\d|h-\\d|text-(xs|sm|base|lg))',
    "*.tsx",
    PROD_EXCLUSIONS
  );
  const textareaWithSizeProp = countRgMatches(
    '<Textarea[^>]*\\bsize=',
    "*.tsx",
    PROD_EXCLUSIONS
  );
  const textareaWithSizingOverride = countRgMatches(
    '<Textarea[^>]*className=[^>]*(py-\\d|px-\\d|h-\\d|text-(xs|sm|base|lg))',
    "*.tsx",
    PROD_EXCLUSIONS
  );
  // Calculate field sizing compliance (fields with size prop and no override vs total)
  const totalFieldsWithSizing = inputWithSizeProp + selectWithSizeProp + textareaWithSizeProp;
  const totalFieldsWithOverrides = inputWithSizingOverride + selectWithSizingOverride + textareaWithSizingOverride;
  const fieldSizingCompliancePercent = totalFieldsWithOverrides === 0
    ? 100
    : Math.round((totalFieldsWithSizing / Math.max(totalFieldsWithSizing + totalFieldsWithOverrides, 1)) * 100);

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

  // Overall score (weighted average - updated to include variant compliance)
  const overallScore = Math.round(
    buttonAdoptionPercent * 0.25 +
      formAdoptionPercent * 0.25 +
      colorAdoptionPercent * 0.2 +
      storybookCoveragePercent * 0.15 +
      buttonVariantCompliancePercent * 0.15
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
    componentVariants: {
      buttonWithVariant,
      buttonWithoutVariant,
      buttonVariantCompliancePercent,
      cancelButtonsWithSecondary,
      cancelButtonsWithoutSecondary,
      destructiveButtonsWithDanger,
      destructiveButtonsWithoutDanger,
      iconButtonWithSizeIcon,
      iconButtonWithoutSizeIcon,
      iconButtonSizeCompliancePercent,
      buttonWithColorOverride,
      colorOverrideCompliancePercent,
    },
    fieldSizing: {
      inputWithSizeProp,
      inputWithSizingOverride,
      selectWithSizeProp,
      selectWithSizingOverride,
      textareaWithSizeProp,
      textareaWithSizingOverride,
      fieldSizingCompliancePercent,
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
      buttonVariantCompliancePercent,
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

  console.log("\nButton Variant Compliance:");
  console.log(`  With explicit variant:    ${metrics.componentVariants.buttonWithVariant}`);
  console.log(`  Without variant:          ${metrics.componentVariants.buttonWithoutVariant}`);
  console.log(`  Variant compliance:       ${metrics.componentVariants.buttonVariantCompliancePercent}%`);
  console.log(`  Cancel w/ secondary:      ${metrics.componentVariants.cancelButtonsWithSecondary}`);
  console.log(`  Cancel w/o secondary:     ${metrics.componentVariants.cancelButtonsWithoutSecondary}`);
  console.log(`  Destructive w/ danger:    ${metrics.componentVariants.destructiveButtonsWithDanger}`);
  console.log(`  Destructive w/o danger:   ${metrics.componentVariants.destructiveButtonsWithoutDanger}`);
  console.log(`  Icon w/ size="icon":      ${metrics.componentVariants.iconButtonWithSizeIcon}`);
  console.log(`  Icon w/o size="icon":     ${metrics.componentVariants.iconButtonWithoutSizeIcon}`);
  console.log(`  Icon size compliance:     ${metrics.componentVariants.iconButtonSizeCompliancePercent}%`);
  console.log(`  w/ color overrides:       ${metrics.componentVariants.buttonWithColorOverride}`);
  console.log(`  Color override compliance:${metrics.componentVariants.colorOverrideCompliancePercent}%`);

  console.log("\nField Sizing Compliance:");
  console.log(`  Input w/ size prop:       ${metrics.fieldSizing.inputWithSizeProp}`);
  console.log(`  Input w/ sizing override: ${metrics.fieldSizing.inputWithSizingOverride}`);
  console.log(`  Select w/ size prop:      ${metrics.fieldSizing.selectWithSizeProp}`);
  console.log(`  Select w/ sizing override:${metrics.fieldSizing.selectWithSizingOverride}`);
  console.log(`  Textarea w/ size prop:    ${metrics.fieldSizing.textareaWithSizeProp}`);
  console.log(`  Textarea w/ sizing override:${metrics.fieldSizing.textareaWithSizingOverride}`);
  console.log(`  Field sizing compliance:  ${metrics.fieldSizing.fieldSizingCompliancePercent}%`);

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
  console.log(`  Button variants:     ${metrics.adoption.buttonVariantCompliancePercent}%`);
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
