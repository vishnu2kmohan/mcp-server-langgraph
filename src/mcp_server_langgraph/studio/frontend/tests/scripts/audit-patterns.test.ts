/**
 * Unit Tests for Design System Audit Patterns
 *
 * TDD tests for the audit-patterns library used by the design system audit script.
 * Tests cover pattern matching, categorization, severity, and legitimate pattern filters.
 */

import { describe, it, expect } from "vitest";
import {
  RIPGREP_PATTERNS,
  EXCLUSION_PATTERNS,
  getSeverity,
  getSuggestion,
  categorizeViolation,
  isLegitimateSizing,
  isLegitimateSpacing,
  type ViolationCategory,
} from "../../scripts/lib/audit-patterns";

// =============================================================================
// RIPGREP_PATTERNS Tests
// =============================================================================

describe("RIPGREP_PATTERNS", () => {
  it("should have patterns for all categories", () => {
    const categories: ViolationCategory[] = [
      "sizing",
      "color",
      "spacing",
      "typography",
      "border",
      "shadow",
      "zindex",
      "animation",
    ];

    categories.forEach((category) => {
      expect(RIPGREP_PATTERNS[category]).toBeDefined();
      expect(RIPGREP_PATTERNS[category].length).toBeGreaterThan(0);
    });
  });

  describe("sizing patterns", () => {
    it("should match arbitrary height values", () => {
      const pattern = new RegExp(RIPGREP_PATTERNS.sizing[0]);
      expect(pattern.test("h-[42px]")).toBe(true);
      expect(pattern.test("h-[100rem]")).toBe(true);
      expect(pattern.test("h-10")).toBe(false); // Standard scale
    });

    it("should match arbitrary width values", () => {
      const pattern = new RegExp(RIPGREP_PATTERNS.sizing[1]);
      expect(pattern.test("w-[200px]")).toBe(true);
      expect(pattern.test("w-48")).toBe(false); // Standard scale
    });
  });

  describe("color patterns", () => {
    it("should match raw Tailwind colors", () => {
      const pattern = new RegExp(RIPGREP_PATTERNS.color[0]);
      expect(pattern.test("bg-blue-500")).toBe(true);
      expect(pattern.test("text-red-400")).toBe(true);
      expect(pattern.test("border-green-600")).toBe(true);
      expect(pattern.test("bg-primary-9")).toBe(false); // Semantic
    });

    it("should match legacy neutral scale", () => {
      const pattern = new RegExp(RIPGREP_PATTERNS.color[1]);
      expect(pattern.test("neutral-500")).toBe(true);
      expect(pattern.test("neutral-100")).toBe(true);
      expect(pattern.test("neutral-9")).toBe(false); // Radix scale
    });

    it("should match raw gray scale", () => {
      const pattern = new RegExp(RIPGREP_PATTERNS.color[2]);
      expect(pattern.test("bg-gray-500")).toBe(true);
      expect(pattern.test("text-slate-400")).toBe(true);
      expect(pattern.test("border-zinc-300")).toBe(true);
    });
  });

  describe("spacing patterns", () => {
    it("should match arbitrary margin/padding values", () => {
      const pattern = new RegExp(RIPGREP_PATTERNS.spacing[0]);
      expect(pattern.test("m-[20px]")).toBe(true);
      expect(pattern.test("px-[16rem]")).toBe(true);
      expect(pattern.test("mt-[8px]")).toBe(true);
      expect(pattern.test("p-4")).toBe(false); // Standard scale
    });

    it("should match arbitrary gap values", () => {
      const pattern = new RegExp(RIPGREP_PATTERNS.spacing[1]);
      expect(pattern.test("gap-[12px]")).toBe(true);
      expect(pattern.test("gap-4")).toBe(false); // Standard scale
    });
  });

  describe("typography patterns", () => {
    it("should match arbitrary font sizes", () => {
      const pattern = new RegExp(RIPGREP_PATTERNS.typography[0]);
      expect(pattern.test("text-[14px]")).toBe(true);
      expect(pattern.test("text-[1.5rem]")).toBe(true);
      expect(pattern.test("text-lg")).toBe(false); // Standard scale
    });
  });

  describe("zindex patterns", () => {
    it("should match arbitrary z-index values", () => {
      const pattern = new RegExp(RIPGREP_PATTERNS.zindex[0]);
      expect(pattern.test("z-[100]")).toBe(true);
      expect(pattern.test("z-[9999]")).toBe(true);
      expect(pattern.test("z-50")).toBe(false); // Standard scale
    });
  });

  describe("animation patterns", () => {
    it("should match arbitrary durations", () => {
      const pattern = new RegExp(RIPGREP_PATTERNS.animation[0]);
      expect(pattern.test("duration-[250ms]")).toBe(true);
      expect(pattern.test("duration-300")).toBe(false); // Standard scale
    });
  });
});

// =============================================================================
// EXCLUSION_PATTERNS Tests
// =============================================================================

describe("EXCLUSION_PATTERNS", () => {
  it("should exclude test files", () => {
    expect(EXCLUSION_PATTERNS).toContainEqual("**/*.test.tsx");
    expect(EXCLUSION_PATTERNS).toContainEqual("**/*.test.ts");
    expect(EXCLUSION_PATTERNS).toContainEqual("**/*.spec.tsx");
  });

  it("should exclude story files", () => {
    expect(EXCLUSION_PATTERNS).toContainEqual("**/*.stories.tsx");
    expect(EXCLUSION_PATTERNS).toContainEqual("**/*.stories.ts");
  });

  it("should exclude build artifacts", () => {
    expect(EXCLUSION_PATTERNS).toContainEqual("**/dist/**");
    expect(EXCLUSION_PATTERNS).toContainEqual("**/node_modules/**");
  });

  it("should exclude design system source files", () => {
    expect(EXCLUSION_PATTERNS).toContainEqual("**/design-system/**");
    expect(EXCLUSION_PATTERNS).toContainEqual("**/radix-colors.ts");
  });
});

// =============================================================================
// getSeverity Tests
// =============================================================================

describe("getSeverity", () => {
  it("should return error for color violations", () => {
    expect(getSeverity("color")).toBe("error");
  });

  it("should return warning for sizing violations", () => {
    expect(getSeverity("sizing")).toBe("warning");
  });

  it("should return warning for spacing violations", () => {
    expect(getSeverity("spacing")).toBe("warning");
  });

  it("should return warning for zindex violations", () => {
    expect(getSeverity("zindex")).toBe("warning");
  });

  it("should return info for shadow violations", () => {
    expect(getSeverity("shadow")).toBe("info");
  });

  it("should return info for border violations", () => {
    expect(getSeverity("border")).toBe("info");
  });

  it("should return info for animation violations", () => {
    expect(getSeverity("animation")).toBe("info");
  });
});

// =============================================================================
// getSuggestion Tests
// =============================================================================

describe("getSuggestion", () => {
  it("should return suggestion for color violations", () => {
    const suggestion = getSuggestion("bg-blue-500", "color");
    expect(suggestion).toContain("semantic");
  });

  it("should return suggestion for legacy neutral scale", () => {
    const suggestion = getSuggestion("neutral-500", "color");
    expect(suggestion).toContain("Radix");
  });

  it("should return suggestion for sizing violations", () => {
    const suggestion = getSuggestion("h-[42px]", "sizing");
    expect(suggestion).toContain("scale");
  });

  it("should return default suggestion when no specific match", () => {
    const suggestion = getSuggestion("some-unknown-pattern", "sizing");
    expect(suggestion).toContain("Tailwind");
  });

  it("should return suggestion for typography violations", () => {
    const suggestion = getSuggestion("text-[14px]", "typography");
    expect(suggestion).toContain("text-");
  });
});

// =============================================================================
// categorizeViolation Tests
// =============================================================================

describe("categorizeViolation", () => {
  it("should categorize sizing violations", () => {
    expect(categorizeViolation("h-[42px]")).toBe("sizing");
    expect(categorizeViolation("w-[200px]")).toBe("sizing");
    expect(categorizeViolation("size-[100]")).toBe("sizing");
    expect(categorizeViolation("min-h-[50px]")).toBe("sizing");
    expect(categorizeViolation("max-w-[300px]")).toBe("sizing");
  });

  it("should categorize color violations", () => {
    expect(categorizeViolation("bg-blue-500")).toBe("color");
    expect(categorizeViolation("text-red-400")).toBe("color");
    expect(categorizeViolation("neutral-500")).toBe("color");
    expect(categorizeViolation("border-gray-300")).toBe("color");
  });

  it("should categorize spacing violations", () => {
    expect(categorizeViolation("m-[20px]")).toBe("spacing");
    expect(categorizeViolation("px-[16rem]")).toBe("spacing");
    expect(categorizeViolation("gap-[12px]")).toBe("spacing");
  });

  it("should categorize typography violations", () => {
    expect(categorizeViolation("text-[14px]")).toBe("typography");
    expect(categorizeViolation("leading-[1.5]")).toBe("typography");
    expect(categorizeViolation("tracking-[0.05em]")).toBe("typography");
  });

  it("should categorize border violations", () => {
    expect(categorizeViolation("rounded-[8px]")).toBe("border");
    expect(categorizeViolation("border-[2px]")).toBe("border");
  });

  it("should categorize shadow violations", () => {
    expect(categorizeViolation("shadow-[0_2px_4px_rgba(0,0,0,0.1)]")).toBe("shadow");
  });

  it("should categorize zindex violations", () => {
    expect(categorizeViolation("z-[100]")).toBe("zindex");
    expect(categorizeViolation("z-index: 9999")).toBe("zindex");
  });

  it("should categorize animation violations", () => {
    expect(categorizeViolation("duration-[250ms]")).toBe("animation");
    expect(categorizeViolation("delay-[100ms]")).toBe("animation");
    expect(categorizeViolation("transition: all 300ms")).toBe("animation");
  });

  it("should return null for unknown patterns", () => {
    expect(categorizeViolation("flex")).toBeNull();
    expect(categorizeViolation("items-center")).toBeNull();
  });
});

// =============================================================================
// isLegitimateSizing Tests
// =============================================================================

describe("isLegitimateSizing", () => {
  it("should allow SVG viewBox sizing", () => {
    expect(isLegitimateSizing('viewBox="0 0 24 24"')).toBe(true);
  });

  it("should allow canvas/chart dimensions", () => {
    expect(isLegitimateSizing("canvas width")).toBe(true);
    expect(isLegitimateSizing("Chart component")).toBe(true);
    expect(isLegitimateSizing("<svg height")).toBe(true);
  });

  it("should allow image dimensions", () => {
    expect(isLegitimateSizing("<img src=")).toBe(true);
    expect(isLegitimateSizing("<Image src=")).toBe(true);
  });

  it("should allow video dimensions", () => {
    expect(isLegitimateSizing("<video src=")).toBe(true);
  });

  it("should allow component width/height props", () => {
    expect(isLegitimateSizing("width={100}")).toBe(true);
    expect(isLegitimateSizing("height={50}")).toBe(true);
  });

  it("should allow CSS custom properties", () => {
    expect(isLegitimateSizing("var(--custom-height)")).toBe(true);
  });

  it("should allow calc expressions", () => {
    expect(isLegitimateSizing("calc(100vh - 64px)")).toBe(true);
  });

  it("should allow viewport-based heights", () => {
    expect(isLegitimateSizing("h-[90vh]")).toBe(true);
    expect(isLegitimateSizing("max-h-[80vh]")).toBe(true);
    expect(isLegitimateSizing("w-[50vw]")).toBe(true);
  });

  it("should allow small functional widths for dividers", () => {
    expect(isLegitimateSizing("w-[1px]")).toBe(true);
    expect(isLegitimateSizing("h-[2px]")).toBe(true);
    expect(isLegitimateSizing("w-[4px]")).toBe(true);
  });

  it("should allow workflow node widths", () => {
    expect(isLegitimateSizing("LLMNode w-[180px]")).toBe(true);
    expect(isLegitimateSizing("ApprovalNode w-[180px]")).toBe(true);
  });

  it("should allow modal/dialog heights", () => {
    expect(isLegitimateSizing("Dialog h-[500px]")).toBe(true);
    expect(isLegitimateSizing("OnboardingModal h-[90vh]")).toBe(true);
  });

  it("should allow artifact viewer heights", () => {
    expect(isLegitimateSizing("MermaidArtifact h-[600px]")).toBe(true);
    expect(isLegitimateSizing("JSONViewer h-[400px]")).toBe(true);
  });

  it("should not allow regular arbitrary sizing", () => {
    expect(isLegitimateSizing('className="h-[42px]"')).toBe(false);
    // w-[200px] is now legitimate for common layout widths (panels, dialogs)
    // Use non-standard width to test violation detection
    expect(isLegitimateSizing("w-[175px] flex")).toBe(false);
  });
});

// =============================================================================
// isLegitimateSpacing Tests
// =============================================================================

describe("isLegitimateSpacing", () => {
  it("should allow negative margins", () => {
    expect(isLegitimateSpacing("-mt-[20px]")).toBe(true);
    expect(isLegitimateSpacing("-mx-[16px]")).toBe(true);
  });

  it("should allow CSS custom properties", () => {
    expect(isLegitimateSpacing("var(--spacing-custom)")).toBe(true);
  });

  it("should allow calc expressions", () => {
    expect(isLegitimateSpacing("calc(100% - 32px)")).toBe(true);
  });

  it("should allow transform/translate contexts", () => {
    expect(isLegitimateSpacing("transform: translateX")).toBe(true);
    expect(isLegitimateSpacing("translate-x-1/2")).toBe(true);
  });

  it("should allow viewport-based padding", () => {
    expect(isLegitimateSpacing("pt-[20vh]")).toBe(true);
    expect(isLegitimateSpacing("pb-[10vw]")).toBe(true);
  });

  it("should allow command palette padding", () => {
    expect(isLegitimateSpacing("AICommandPalette pt-[20vh]")).toBe(true);
    expect(isLegitimateSpacing("GenericCommandPalette pt-[20vh]")).toBe(true);
  });

  it("should not allow regular arbitrary spacing", () => {
    expect(isLegitimateSpacing('className="p-[20px]"')).toBe(false);
    expect(isLegitimateSpacing("m-[16px] flex")).toBe(false);
  });
});

// =============================================================================
// Auto-Fix Tests
// =============================================================================

import { AUTO_FIX_MAPPINGS, getAutoFix } from "../../scripts/lib/audit-patterns";

describe("AUTO_FIX_MAPPINGS", () => {
  it("should have mappings for legacy neutral scale", () => {
    const neutralMappings = AUTO_FIX_MAPPINGS.filter(
      (m) => m.description.includes("neutral-")
    );
    expect(neutralMappings.length).toBeGreaterThan(0);
  });

  it("should have mappings for gray scale", () => {
    const grayMappings = AUTO_FIX_MAPPINGS.filter(
      (m) => m.description.includes("gray-")
    );
    expect(grayMappings.length).toBeGreaterThan(0);
  });

  it("should have mappings for slate scale", () => {
    const slateMappings = AUTO_FIX_MAPPINGS.filter(
      (m) => m.description.includes("slate-")
    );
    expect(slateMappings.length).toBeGreaterThan(0);
  });

  it("should all be color category", () => {
    for (const mapping of AUTO_FIX_MAPPINGS) {
      expect(mapping.category).toBe("color");
    }
  });
});

describe("getAutoFix", () => {
  it("should fix legacy neutral-500 to neutral-8", () => {
    const result = getAutoFix("bg-neutral-500");
    expect(result).not.toBeNull();
    expect(result!.fixed).toBe("bg-neutral-8");
    expect(result!.description).toContain("neutral-500");
  });

  it("should fix legacy neutral-100 to neutral-2", () => {
    const result = getAutoFix("text-neutral-100");
    expect(result).not.toBeNull();
    expect(result!.fixed).toBe("text-neutral-2");
  });

  it("should fix gray-500 to neutral-8", () => {
    const result = getAutoFix("bg-gray-500");
    expect(result).not.toBeNull();
    expect(result!.fixed).toBe("bg-neutral-8");
  });

  it("should fix text-gray-700 to text-neutral-10", () => {
    const result = getAutoFix("text-gray-700");
    expect(result).not.toBeNull();
    expect(result!.fixed).toBe("text-neutral-10");
  });

  it("should fix slate-500 to neutral-8", () => {
    const result = getAutoFix("bg-slate-500");
    expect(result).not.toBeNull();
    expect(result!.fixed).toBe("bg-neutral-8");
  });

  it("should return null for patterns without auto-fix", () => {
    expect(getAutoFix("h-[42px]")).toBeNull();
    expect(getAutoFix("p-[20px]")).toBeNull();
    expect(getAutoFix("bg-primary-9")).toBeNull();
  });

  it("should preserve prefix in replacement", () => {
    const bgResult = getAutoFix("bg-gray-500");
    expect(bgResult!.fixed).toBe("bg-neutral-8");

    const textResult = getAutoFix("text-gray-500");
    expect(textResult!.fixed).toBe("text-neutral-8");

    const borderResult = getAutoFix("border-gray-500");
    expect(borderResult!.fixed).toBe("border-neutral-8");
  });
});
