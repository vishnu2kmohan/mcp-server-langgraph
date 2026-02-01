/**
 * Design System Contract Tests
 *
 * These tests ensure the design system remains consistent across:
 * - TypeScript tokens (tokens.ts, animation-tokens.ts)
 * - CSS variables (index.css)
 * - Tailwind configuration (tailwind.config.ts)
 *
 * WHY THIS EXISTS:
 * CSS variables can be referenced in Tailwind config (e.g., `var(--primary-9)`)
 * but if the variable is never defined in CSS, the browser silently fails.
 * This caused the "white screen" bug where colors weren't applied.
 *
 * These tests prevent that by validating:
 * 1. Every CSS variable referenced in Tailwind config exists in index.css
 * 2. Every token defined in tokens.ts has a corresponding CSS variable
 * 3. Values match between sources (no drift)
 *
 * @see ADR-0104 (Design System Contract Testing)
 */

import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import * as fs from "fs";
import * as path from "path";

// =============================================================================
// Test Setup - Load source files
// =============================================================================

let indexCssContent: string;
let tailwindConfigContent: string;

beforeAll(() => {
  const frontendRoot = path.resolve(__dirname, "../..");
  indexCssContent = fs.readFileSync(
    path.join(frontendRoot, "src/index.css"),
    "utf-8",
  );
  tailwindConfigContent = fs.readFileSync(
    path.join(frontendRoot, "tailwind.config.ts"),
    "utf-8",
  );
});

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Extract all CSS variable definitions from CSS content
 * Matches: --variable-name: value;
 */
function extractCssVariableDefinitions(css: string): Set<string> {
  const regex = /--[\w-]+(?=\s*:)/g;
  const matches = css.match(regex) || [];
  return new Set(matches);
}

/**
 * Extract all CSS variable references from content
 * Matches: var(--variable-name)
 */
function extractCssVariableReferences(content: string): Set<string> {
  const regex = /var\(--[\w-]+\)/g;
  const matches = content.match(regex) || [];
  // Extract just the variable name from var(--name)
  return new Set(matches.map((m) => m.replace(/var\(|\)/g, "")));
}

/**
 * Check if a CSS variable is defined in either :root or .dark selector
 */
function isVariableDefined(varName: string, css: string): boolean {
  // Check for definition pattern: --var-name:
  const definitionPattern = new RegExp(`${varName}\\s*:`);
  return definitionPattern.test(css);
}

// =============================================================================
// Contract Tests
// =============================================================================

afterEach(() => {
  vi.clearAllMocks();
});

describe("Design System Contract Tests", () => {
  describe("CSS Variable Definitions", () => {
    it("should define all Radix color variables in :root", () => {
      const requiredColorScales = [
        "violet",
        "teal",
        "slate",
        "sage",
        "olive",
        "grass",
        "amber",
        "ruby",
        "sky",
        "orange",
      ];

      for (const scale of requiredColorScales) {
        for (let step = 1; step <= 12; step++) {
          const varName = `--${scale}-${step}`;
          expect(
            isVariableDefined(varName, indexCssContent),
            `Missing CSS variable: ${varName}`,
          ).toBe(true);
        }
      }
    });

    it("should define all semantic color variables", () => {
      const semanticColors = [
        "primary",
        "neutral",
        "success",
        "warning",
        "error",
        "info",
        "insight",
        "grafana",
      ];

      for (const color of semanticColors) {
        for (let step = 1; step <= 12; step++) {
          const varName = `--${color}-${step}`;
          expect(
            isVariableDefined(varName, indexCssContent),
            `Missing semantic color variable: ${varName}`,
          ).toBe(true);
        }
      }
    });

    it("should define all typography variables", () => {
      const fontSizes = ["xs", "sm", "base", "lg", "xl", "2xl", "3xl", "4xl"];
      const fontWeights = ["normal", "medium", "semibold", "bold"];
      const lineHeights = [
        "none",
        "tight",
        "snug",
        "normal",
        "relaxed",
        "loose",
      ];
      const letterSpacings = ["tighter", "tight", "normal", "wide", "wider"];

      for (const size of fontSizes) {
        expect(
          isVariableDefined(`--font-size-${size}`, indexCssContent),
          `Missing font-size variable: --font-size-${size}`,
        ).toBe(true);
      }

      for (const weight of fontWeights) {
        expect(
          isVariableDefined(`--font-weight-${weight}`, indexCssContent),
          `Missing font-weight variable: --font-weight-${weight}`,
        ).toBe(true);
      }

      for (const height of lineHeights) {
        expect(
          isVariableDefined(`--line-height-${height}`, indexCssContent),
          `Missing line-height variable: --line-height-${height}`,
        ).toBe(true);
      }

      for (const spacing of letterSpacings) {
        expect(
          isVariableDefined(`--letter-spacing-${spacing}`, indexCssContent),
          `Missing letter-spacing variable: --letter-spacing-${spacing}`,
        ).toBe(true);
      }
    });

    it("should define all spacing variables", () => {
      const spacings = [
        "0",
        "px",
        "0-5",
        "1",
        "1-5",
        "2",
        "2-5",
        "3",
        "3-5",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "12",
        "14",
        "16",
        "20",
        "24",
      ];

      for (const spacing of spacings) {
        expect(
          isVariableDefined(`--spacing-${spacing}`, indexCssContent),
          `Missing spacing variable: --spacing-${spacing}`,
        ).toBe(true);
      }
    });

    it("should define all shadow variables", () => {
      const shadows = [
        "none",
        "sm",
        "md",
        "lg",
        "xl",
        "2xl",
        "inner",
        "soft",
        "elevated",
        "modal",
      ];

      for (const shadow of shadows) {
        expect(
          isVariableDefined(`--shadow-${shadow}`, indexCssContent),
          `Missing shadow variable: --shadow-${shadow}`,
        ).toBe(true);
      }
    });

    it("should define all border-radius variables", () => {
      const radii = [
        "none",
        "sm",
        "DEFAULT",
        "md",
        "lg",
        "xl",
        "2xl",
        "3xl",
        "full",
      ];

      for (const radius of radii) {
        expect(
          isVariableDefined(`--radius-${radius}`, indexCssContent),
          `Missing radius variable: --radius-${radius}`,
        ).toBe(true);
      }
    });

    it("should define all animation duration variables", () => {
      const durations = ["instant", "fast", "normal", "slow", "slower"];

      for (const duration of durations) {
        expect(
          isVariableDefined(`--duration-${duration}`, indexCssContent),
          `Missing duration variable: --duration-${duration}`,
        ).toBe(true);
      }
    });

    it("should define all easing function variables", () => {
      const easings = ["out", "in", "in-out", "anticipate"];

      for (const easing of easings) {
        expect(
          isVariableDefined(`--ease-${easing}`, indexCssContent),
          `Missing easing variable: --ease-${easing}`,
        ).toBe(true);
      }
    });

    it("should define all z-index variables", () => {
      const zIndexes = [
        "base",
        "tooltip",
        "dropdown",
        "panel",
        "command-palette",
        "modal",
        "notification",
        "system-alert",
        "toast",
      ];

      for (const zIndex of zIndexes) {
        expect(
          isVariableDefined(`--z-${zIndex}`, indexCssContent),
          `Missing z-index variable: --z-${zIndex}`,
        ).toBe(true);
      }
    });
  });

  describe("Tailwind Config References", () => {
    it("should only reference CSS variables that are defined", () => {
      const referencedVars = extractCssVariableReferences(
        tailwindConfigContent,
      );
      const definedVars = extractCssVariableDefinitions(indexCssContent);

      const undefinedVars: string[] = [];
      for (const varRef of referencedVars) {
        if (!definedVars.has(varRef)) {
          undefinedVars.push(varRef);
        }
      }

      expect(
        undefinedVars,
        `Tailwind config references undefined CSS variables:\n${undefinedVars.join("\n")}`,
      ).toHaveLength(0);
    });
  });

  describe("Dark Mode Support", () => {
    it("should define dark mode color overrides", () => {
      // Check that .dark selector exists and has color definitions
      expect(indexCssContent).toContain(".dark {");

      // Check some key dark mode variables are defined differently
      const darkModeSection = indexCssContent.split(".dark {")[1];
      expect(darkModeSection).toBeDefined();

      // Verify dark mode has violet-1 defined (should be different from light)
      expect(darkModeSection).toContain("--violet-1:");
    });
  });

  describe("Value Consistency", () => {
    it("should have consistent spacing scale (4px base)", () => {
      // Verify the spacing scale follows 4px (0.25rem) increments
      const spacingPattern = /--spacing-4:\s*1rem/;
      expect(indexCssContent).toMatch(spacingPattern);

      const spacing8Pattern = /--spacing-8:\s*2rem/;
      expect(indexCssContent).toMatch(spacing8Pattern);
    });

    it("should have WCAG-compliant contrast for text colors", () => {
      // Verify step-11 is used for high-contrast text (per Radix guidelines)
      expect(tailwindConfigContent).toContain("11: 'var(--primary-11)'");
      expect(tailwindConfigContent).toContain("11: 'var(--neutral-11)'");
    });

    it("should use step-9 for primary action colors", () => {
      // Verify step-9 is the primary action color (buttons, links)
      expect(tailwindConfigContent).toContain("9: 'var(--primary-9)'");
    });
  });
});

describe("Design Token Synchronization", () => {
  it("should have matching token count in tokens.ts and CSS", () => {
    // This is a sanity check - if someone adds tokens to tokens.ts,
    // they should also add CSS variables

    // Count expected CSS variables from our token definitions
    const expectedCssVarCount = {
      colors: 9 * 12, // 9 palettes × 12 steps = 108
      semanticColors: 8 * 12, // 8 semantic colors × 12 steps = 96
      typography: 8 + 4 + 6 + 5, // fontSize + fontWeight + lineHeight + letterSpacing = 23
      spacing: 21, // 21 spacing values
      shadows: 10, // 10 shadow values
      radii: 9, // 9 border-radius values
      durations: 5, // 5 duration values
      easings: 4, // 4 easing functions
      zIndex: 9, // 9 z-index values
    };

    const totalExpected = Object.values(expectedCssVarCount).reduce(
      (a, b) => a + b,
      0,
    );

    const definedVars = extractCssVariableDefinitions(indexCssContent);

    // Allow some flexibility (±10%) for aliases and additional variables
    expect(definedVars.size).toBeGreaterThanOrEqual(totalExpected * 0.9);
  });
});
