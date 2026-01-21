#!/usr/bin/env npx tsx
/**
 * Design System Compliance Check
 *
 * Scans the codebase and reports metrics on design system adoption.
 * Outputs JSON metrics for CI dashboards and tracking.
 *
 * Usage:
 *   npx tsx scripts/check-design-system-compliance.ts [options]
 *   npm run check:design-system
 *
 * Options:
 *   --json        Output JSON metrics (also enabled in CI)
 *   --strict      Exit non-zero on violations (for CI enforcement)
 *   --violations  Show detailed violation report with file paths
 *   --verbose     Show score breakdown weights
 *
 * Examples:
 *   npx tsx scripts/check-design-system-compliance.ts --violations
 *   npx tsx scripts/check-design-system-compliance.ts --strict --violations
 *
 * Metrics tracked:
 * - Raw HTML element usage vs design system components
 * - Button variant compliance (STYLE.md: ghost for nav, secondary for cancel, danger for destructive)
 * - Navigation context compliance (buttons in <nav>, sidebar, tabs should use variant="ghost")
 * - Form element adoption (Checkbox, RadioGroup, Toggle)
 * - Gray vs neutral color usage (Radix 1-12 scale)
 * - Storybook coverage for UI components
 * - Icon button size compliance (WCAG 2.2 touch targets)
 * - Field sizing compliance (size prop vs className overrides)
 *
 * Score weighting:
 *   Button adoption:     20%
 *   Form adoption:       20%
 *   Button variants:     20%
 *   Nav context:         15%
 *   Color adoption:      15%
 *   Storybook coverage:  10%
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
  navigationContext: {
    navButtonsWithGhost: number;
    navButtonsWithoutGhost: number;
    navButtonCompliancePercent: number;
    sidebarButtonsWithGhost: number;
    sidebarButtonsWithoutGhost: number;
    sidebarButtonCompliancePercent: number;
    tabButtonsWithGhost: number;
    tabButtonsWithoutGhost: number;
    tabButtonCompliancePercent: number;
    filesWithNavViolations: string[];
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
    navContextCompliancePercent: number;
    overallScore: number;
  };
}

function countRgMatches(pattern: string, glob?: string, excludePatterns?: string[], multiline = false): number {
  try {
    const globArg = glob ? `-g '${glob}'` : "";
    const excludeArgs = excludePatterns ? excludePatterns.map((p) => `-g '!${p}'`).join(" ") : "";
    // Use single quotes around pattern to prevent shell interpretation of regex chars
    const escapedPattern = pattern.replace(/'/g, "'\\''");
    // Use -U for multiline matching (allows patterns to span line breaks)
    const multilineArg = multiline ? "-U" : "";
    const cmd = `rg -c ${multilineArg} '${escapedPattern}' src/ ${globArg} ${excludeArgs} 2>/dev/null | awk -F: '{sum += \$2} END {print sum}'`;
    const result = execSync(cmd, { encoding: "utf-8", cwd: path.join(__dirname, "..") }).trim();
    return parseInt(result, 10) || 0;
  } catch {
    return 0;
  }
}

function findFilesWithPattern(pattern: string, glob?: string, excludePatterns?: string[]): string[] {
  try {
    const globArg = glob ? `-g '${glob}'` : "";
    const excludeArgs = excludePatterns ? excludePatterns.map((p) => `-g '!${p}'`).join(" ") : "";
    const escapedPattern = pattern.replace(/'/g, "'\\''");
    const cmd = `rg -l '${escapedPattern}' src/ ${globArg} ${excludeArgs} 2>/dev/null`;
    const result = execSync(cmd, { encoding: "utf-8", cwd: path.join(__dirname, "..") }).trim();
    return result ? result.split("\n").filter(Boolean) : [];
  } catch {
    return [];
  }
}

/**
 * Analyzes files for navigation context button compliance.
 * Per STYLE.md: Navigation buttons (inside <nav>, sidebar, tabs) should use variant="ghost"
 *
 * Detection strategy:
 * 1. Find files with navigation context patterns (nav, sidebar, tabs, menu)
 * 2. Check if Buttons in those contexts use variant="ghost"
 */
function isExemptFile(filePath: string): boolean {
  const fileName = path.basename(filePath);
  return NAV_CONTEXT_EXCEPTIONS.includes(fileName);
}

function analyzeNavigationContextCompliance(excludePatterns: string[]): {
  navWithGhost: number;
  navWithoutGhost: number;
  sidebarWithGhost: number;
  sidebarWithoutGhost: number;
  tabWithGhost: number;
  tabWithoutGhost: number;
  violationFiles: string[];
} {
  const violationFiles: string[] = [];

  // Pattern 1: Buttons inside <nav> elements
  // Files with <nav> containing Button - check for ghost variant
  const filesWithNav = findFilesWithPattern("<nav", "*.tsx", excludePatterns).filter(f => !isExemptFile(f));
  let navWithGhost = 0;
  let navWithoutGhost = 0;

  for (const file of filesWithNav) {
    try {
      const content = fs.readFileSync(path.join(__dirname, "..", file), "utf-8");
      // Find <nav> blocks and check buttons within
      const navRegex = /<nav[^>]*>[\s\S]*?<\/nav>/g;
      const matches = content.match(navRegex) || [];
      for (const navBlock of matches) {
        // Count buttons with ghost variant in nav
        const ghostButtons = (navBlock.match(/<Button[^>]*variant=["']ghost["']/g) || []).length;
        // Count buttons without ghost variant (missing variant or different variant)
        const allButtons = (navBlock.match(/<Button\b/g) || []).length;
        const nonGhostButtons = allButtons - ghostButtons;

        navWithGhost += ghostButtons;
        navWithoutGhost += nonGhostButtons;

        if (nonGhostButtons > 0 && !violationFiles.includes(file)) {
          violationFiles.push(file);
        }
      }
    } catch {
      // File read error, skip
    }
  }

  // Pattern 2: Sidebar navigation buttons
  // Look for common sidebar patterns: className containing "sidebar", "side-nav", "nav-menu"
  const filesWithSidebar = findFilesWithPattern("(sidebar|side-nav|sideNav|SideNav)", "*.tsx", excludePatterns).filter(f => !isExemptFile(f));
  let sidebarWithGhost = 0;
  let sidebarWithoutGhost = 0;

  for (const file of filesWithSidebar) {
    try {
      const content = fs.readFileSync(path.join(__dirname, "..", file), "utf-8");
      // Find sidebar-like blocks (divs with sidebar class or role="navigation")
      const sidebarRegex = /<(?:div|aside|section)[^>]*(?:className|role)=[^>]*(?:sidebar|navigation|side-nav)[^>]*>[\s\S]*?<\/(?:div|aside|section)>/gi;
      const matches = content.match(sidebarRegex) || [];
      for (const sidebarBlock of matches) {
        const ghostButtons = (sidebarBlock.match(/<Button[^>]*variant=["']ghost["']/g) || []).length;
        const allButtons = (sidebarBlock.match(/<Button\b/g) || []).length;
        const nonGhostButtons = allButtons - ghostButtons;

        sidebarWithGhost += ghostButtons;
        sidebarWithoutGhost += nonGhostButtons;

        if (nonGhostButtons > 0 && !violationFiles.includes(file)) {
          violationFiles.push(file);
        }
      }
    } catch {
      // File read error, skip
    }
  }

  // Pattern 3: Tab navigation buttons
  // Look for tabs patterns: role="tablist", className containing "tabs"
  const filesWithTabs = findFilesWithPattern('(role=["\\\'"]tablist["\\\'"]|className=[^>]*tabs)', "*.tsx", excludePatterns).filter(f => !isExemptFile(f));
  let tabWithGhost = 0;
  let tabWithoutGhost = 0;

  for (const file of filesWithTabs) {
    try {
      const content = fs.readFileSync(path.join(__dirname, "..", file), "utf-8");
      // Find tablist blocks
      const tablistRegex = /<[^>]*role=["']tablist["'][^>]*>[\s\S]*?<\/[^>]+>/g;
      const matches = content.match(tablistRegex) || [];
      for (const tabBlock of matches) {
        const ghostButtons = (tabBlock.match(/<Button[^>]*variant=["']ghost["']/g) || []).length;
        const allButtons = (tabBlock.match(/<Button\b/g) || []).length;
        const nonGhostButtons = allButtons - ghostButtons;

        tabWithGhost += ghostButtons;
        tabWithoutGhost += nonGhostButtons;

        if (nonGhostButtons > 0 && !violationFiles.includes(file)) {
          violationFiles.push(file);
        }
      }
    } catch {
      // File read error, skip
    }
  }

  return {
    navWithGhost,
    navWithoutGhost,
    sidebarWithGhost,
    sidebarWithoutGhost,
    tabWithGhost,
    tabWithoutGhost,
    violationFiles,
  };
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

// Components that are exempt from navigation button compliance
// These use specialized button patterns that are intentional
const NAV_CONTEXT_EXCEPTIONS = [
  "StepProgress.tsx",      // Specialized progress indicator with circular step buttons
  "Pagination.tsx",        // Pagination buttons have different semantics
  "SegmentedControl.tsx",  // Segment buttons are toggle-style, not navigation
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
  // Use multiline mode since variant may be on a separate line from <Button
  const buttonWithVariant = countRgMatches("<Button\\b[^>]*variant=", "*.tsx", PROD_EXCLUSIONS, true);
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

  // Analyze navigation context compliance (STYLE.md: nav/sidebar/tab buttons should use ghost)
  const navCompliance = analyzeNavigationContextCompliance(PROD_EXCLUSIONS);
  const totalNavButtons = Math.max(navCompliance.navWithGhost + navCompliance.navWithoutGhost, 1);
  const navButtonCompliancePercent = Math.round((navCompliance.navWithGhost / totalNavButtons) * 100);
  const totalSidebarButtons = Math.max(navCompliance.sidebarWithGhost + navCompliance.sidebarWithoutGhost, 1);
  const sidebarButtonCompliancePercent = Math.round((navCompliance.sidebarWithGhost / totalSidebarButtons) * 100);
  const totalTabButtons = Math.max(navCompliance.tabWithGhost + navCompliance.tabWithoutGhost, 1);
  const tabButtonCompliancePercent = Math.round((navCompliance.tabWithGhost / totalTabButtons) * 100);

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

  // Calculate navigation context compliance aggregate
  const totalNavContextButtons = (navCompliance.navWithGhost + navCompliance.navWithoutGhost) +
    (navCompliance.sidebarWithGhost + navCompliance.sidebarWithoutGhost) +
    (navCompliance.tabWithGhost + navCompliance.tabWithoutGhost);
  const navContextCompliantButtons = navCompliance.navWithGhost +
    navCompliance.sidebarWithGhost + navCompliance.tabWithGhost;
  const navContextCompliancePercent = totalNavContextButtons > 0
    ? Math.round((navContextCompliantButtons / totalNavContextButtons) * 100)
    : 100;

  // Overall score (weighted average - updated to include variant and navigation compliance)
  const overallScore = Math.round(
    buttonAdoptionPercent * 0.20 +
      formAdoptionPercent * 0.20 +
      colorAdoptionPercent * 0.15 +
      storybookCoveragePercent * 0.10 +
      buttonVariantCompliancePercent * 0.20 +
      navContextCompliancePercent * 0.15
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
    navigationContext: {
      navButtonsWithGhost: navCompliance.navWithGhost,
      navButtonsWithoutGhost: navCompliance.navWithoutGhost,
      navButtonCompliancePercent,
      sidebarButtonsWithGhost: navCompliance.sidebarWithGhost,
      sidebarButtonsWithoutGhost: navCompliance.sidebarWithoutGhost,
      sidebarButtonCompliancePercent,
      tabButtonsWithGhost: navCompliance.tabWithGhost,
      tabButtonsWithoutGhost: navCompliance.tabWithoutGhost,
      tabButtonCompliancePercent,
      filesWithNavViolations: navCompliance.violationFiles,
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
      navContextCompliancePercent,
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

  console.log("\nNavigation Context Compliance (STYLE.md: nav/sidebar/tab buttons should use variant='ghost'):");
  console.log(`  Nav buttons w/ ghost:     ${metrics.navigationContext.navButtonsWithGhost}`);
  console.log(`  Nav buttons w/o ghost:    ${metrics.navigationContext.navButtonsWithoutGhost}`);
  console.log(`  Nav compliance:           ${metrics.navigationContext.navButtonCompliancePercent}%`);
  console.log(`  Sidebar w/ ghost:         ${metrics.navigationContext.sidebarButtonsWithGhost}`);
  console.log(`  Sidebar w/o ghost:        ${metrics.navigationContext.sidebarButtonsWithoutGhost}`);
  console.log(`  Sidebar compliance:       ${metrics.navigationContext.sidebarButtonCompliancePercent}%`);
  console.log(`  Tab buttons w/ ghost:     ${metrics.navigationContext.tabButtonsWithGhost}`);
  console.log(`  Tab buttons w/o ghost:    ${metrics.navigationContext.tabButtonsWithoutGhost}`);
  console.log(`  Tab compliance:           ${metrics.navigationContext.tabButtonCompliancePercent}%`);
  if (metrics.navigationContext.filesWithNavViolations.length > 0) {
    console.log(`  Files with violations:`);
    for (const file of metrics.navigationContext.filesWithNavViolations.slice(0, 10)) {
      console.log(`    - ${file}`);
    }
    if (metrics.navigationContext.filesWithNavViolations.length > 10) {
      console.log(`    ... and ${metrics.navigationContext.filesWithNavViolations.length - 10} more`);
    }
  }

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
  console.log(`  Nav context:         ${metrics.adoption.navContextCompliancePercent}%`);
  console.log(`  Overall score:       ${metrics.adoption.overallScore}%`);
  console.log("----------------------------------------\n");

  // Show score breakdown when verbose
  if (process.argv.includes("--verbose")) {
    console.log("Score Breakdown (weights):");
    console.log("  Button adoption:     20%");
    console.log("  Form adoption:       20%");
    console.log("  Color adoption:      15%");
    console.log("  Storybook coverage:  10%");
    console.log("  Button variants:     20%");
    console.log("  Nav context:         15%");
    console.log("----------------------------------------\n");
  }

  // Output JSON for CI
  if (process.env.CI || process.argv.includes("--json")) {
    console.log("JSON Output:");
    console.log(JSON.stringify(metrics, null, 2));
  }
}

/**
 * Outputs detailed violation information for debugging
 */
function printViolations(metrics: ComplianceMetrics): void {
  console.log("\n========================================");
  console.log("   Detailed Violations Report");
  console.log("========================================\n");

  // Navigation context violations
  if (metrics.navigationContext.filesWithNavViolations.length > 0) {
    console.log("Navigation Context Violations (buttons in nav/sidebar/tabs without variant='ghost'):");
    console.log("Per STYLE.md: Navigation buttons should use variant='ghost'\n");
    for (const file of metrics.navigationContext.filesWithNavViolations) {
      console.log(`  ${file}`);
    }
    console.log("");
  }

  // Cancel/Close button violations
  if (metrics.componentVariants.cancelButtonsWithoutSecondary > 0) {
    console.log(`Cancel/Close Buttons Without variant='secondary': ${metrics.componentVariants.cancelButtonsWithoutSecondary}`);
    console.log("Per STYLE.md: Cancel, Close, Back, Dismiss, No buttons should use variant='secondary'\n");
  }

  // Destructive button violations
  if (metrics.componentVariants.destructiveButtonsWithoutDanger > 0) {
    console.log(`Destructive Buttons Without variant='danger': ${metrics.componentVariants.destructiveButtonsWithoutDanger}`);
    console.log("Per STYLE.md: Delete, Remove, Clear, Destroy, Discard buttons should use variant='danger'\n");
  }

  // Buttons without any variant
  if (metrics.componentVariants.buttonWithoutVariant > 0) {
    console.log(`Buttons Without Explicit Variant: ${metrics.componentVariants.buttonWithoutVariant}`);
    console.log("Consider adding explicit variant prop for clarity.\n");
  }

  // Color overrides
  if (metrics.componentVariants.buttonWithColorOverride > 0) {
    console.log(`Buttons With Color Class Overrides: ${metrics.componentVariants.buttonWithColorOverride}`);
    console.log("Per STYLE.md: Use variant prop instead of inline color classes.\n");
  }

  console.log("========================================\n");
}

// Main execution
const metrics = calculateMetrics();
printReport(metrics);

// Print detailed violations if requested
if (process.argv.includes("--violations")) {
  printViolations(metrics);
}

// Exit with non-zero if adoption is critically low (for CI enforcement)
if (process.argv.includes("--strict")) {
  let exitCode = 0;

  if (metrics.adoption.overallScore < 50) {
    console.error("ERROR: Design system adoption is below 50%");
    exitCode = 1;
  }

  // Additional strict checks
  if (metrics.navigationContext.filesWithNavViolations.length > 0) {
    console.error(`ERROR: ${metrics.navigationContext.filesWithNavViolations.length} files have navigation context violations`);
    console.error("  Run with --violations flag for details");
    exitCode = 1;
  }

  if (metrics.componentVariants.destructiveButtonsWithoutDanger > 0) {
    console.error(`ERROR: ${metrics.componentVariants.destructiveButtonsWithoutDanger} destructive buttons missing variant='danger'`);
    exitCode = 1;
  }

  if (exitCode !== 0) {
    process.exit(exitCode);
  }
}
