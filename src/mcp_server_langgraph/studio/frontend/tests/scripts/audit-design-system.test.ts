/**
 * Tests for Design System Audit Script
 *
 * Validates that the audit script correctly identifies design system violations.
 * Tests are organized by audit category.
 *
 * NOTE: This test file uses the RIPGREP_PATTERNS from audit-patterns.ts.
 * Patterns are accessed by category (sizing, color, spacing, etc.) and index.
 */

import { describe, it, expect } from "vitest";
import {
  RIPGREP_PATTERNS,
  categorizeViolation,
  getSuggestion,
  isLegitimateSizing,
  isLegitimateSpacing,
  type ViolationCategory,
} from "../../scripts/lib/audit-patterns";

// =============================================================================
// Pattern Helpers - Create named patterns from RIPGREP_PATTERNS arrays
// =============================================================================

// Convert pattern strings to RegExp for testing
function toRegex(pattern: string): RegExp {
  return new RegExp(pattern);
}

// Sizing patterns (from RIPGREP_PATTERNS.sizing)
const SIZING_PATTERNS = {
  arbitraryHeight: toRegex(RIPGREP_PATTERNS.sizing[0]), // \bh-\[\d+
  arbitraryWidth: toRegex(RIPGREP_PATTERNS.sizing[1]), // \bw-\[\d+
  arbitrarySize: toRegex(RIPGREP_PATTERNS.sizing[2]), // \bsize-\[\d+
};

// Color patterns (from RIPGREP_PATTERNS.color)
const COLOR_PATTERNS = {
  rawTailwindColor: toRegex(RIPGREP_PATTERNS.color[0]), // bg-red-500, text-blue-600
  legacyNeutral: toRegex(RIPGREP_PATTERNS.color[1]), // neutral-50, neutral-100
};

// Spacing patterns (from RIPGREP_PATTERNS.spacing)
const SPACING_PATTERNS = {
  arbitrarySpacing: toRegex(RIPGREP_PATTERNS.spacing[0]), // p-[20px], m-[1.5rem]
  gapArbitrary: toRegex(RIPGREP_PATTERNS.spacing[1]), // gap-[20px]
};

// Typography patterns (from RIPGREP_PATTERNS.typography)
// [0] = text-\[[0-9.]+(?:px|rem)\]  (font size)
// [1] = leading-\[[0-9.]+\]          (line-height, no unit required)
// [2] = tracking-\[[0-9.]+(?:em|rem)\] (letter-spacing, em or rem)
const TYPOGRAPHY_PATTERNS = {
  arbitraryFontSize: toRegex(RIPGREP_PATTERNS.typography[0]),
  arbitraryLineHeight: toRegex(RIPGREP_PATTERNS.typography[1]),
  arbitraryLetterSpacing: toRegex(RIPGREP_PATTERNS.typography[2]),
};

// Border patterns (from RIPGREP_PATTERNS.border)
const BORDER_PATTERNS = {
  arbitraryRadius: toRegex(RIPGREP_PATTERNS.border[0]), // rounded-[10px]
  arbitraryWidth: toRegex(RIPGREP_PATTERNS.border[1]), // border-[2px]
};

// Shadow patterns (from RIPGREP_PATTERNS.shadow)
const SHADOW_PATTERNS = {
  arbitraryShadow: toRegex(RIPGREP_PATTERNS.shadow[0]), // shadow-[*]
  inlineBoxShadow: /box-shadow:/,
};

// Z-index patterns (from RIPGREP_PATTERNS.zindex)
const ZINDEX_PATTERNS = {
  arbitraryZIndex: toRegex(RIPGREP_PATTERNS.zindex[0]), // z-[100]
  nonTokenZIndex: /z-(?:100|999|[3-9]\d{2,})/,
};

// Animation patterns (from RIPGREP_PATTERNS.animation)
const ANIMATION_PATTERNS = {
  arbitraryDuration: toRegex(RIPGREP_PATTERNS.animation[0]), // duration-[200ms]
  inlineTransition: /transition:/,
};

// Opacity patterns (not in RIPGREP_PATTERNS, create manually)
const OPACITY_PATTERNS = {
  arbitraryOpacity: /opacity-\[\d*\.?\d+\]/,
  bgOpacity: /(?:bg|text)-[a-z]+-\d+\/\[\d*\.?\d+\]/,
};

// =============================================================================
// Sizing Pattern Tests
// =============================================================================

describe("Sizing Patterns", () => {
  describe("SIZING_PATTERNS.arbitraryHeight", () => {
    it("should match hardcoded height values with units", () => {
      expect("h-[42px]").toMatch(SIZING_PATTERNS.arbitraryHeight);
      expect("h-[2rem]").toMatch(SIZING_PATTERNS.arbitraryHeight);
      expect("h-[100px]").toMatch(SIZING_PATTERNS.arbitraryHeight);
    });

    it("should not match values without units", () => {
      // Pattern requires px or rem unit
      expect("h-[100]").not.toMatch(SIZING_PATTERNS.arbitraryHeight);
    });

    it("should not match design token heights", () => {
      expect("h-10").not.toMatch(SIZING_PATTERNS.arbitraryHeight);
      expect("h-full").not.toMatch(SIZING_PATTERNS.arbitraryHeight);
      expect("h-screen").not.toMatch(SIZING_PATTERNS.arbitraryHeight);
    });
  });

  describe("SIZING_PATTERNS.arbitraryWidth", () => {
    it("should match hardcoded width values with units", () => {
      expect("w-[200px]").toMatch(SIZING_PATTERNS.arbitraryWidth);
      expect("w-[50px]").toMatch(SIZING_PATTERNS.arbitraryWidth);
    });

    it("should not match values without units", () => {
      // Pattern requires px or rem unit
      expect("w-[50]").not.toMatch(SIZING_PATTERNS.arbitraryWidth);
    });

    it("should not match design token widths", () => {
      expect("w-full").not.toMatch(SIZING_PATTERNS.arbitraryWidth);
      expect("w-1/2").not.toMatch(SIZING_PATTERNS.arbitraryWidth);
    });
  });

  describe("SIZING_PATTERNS.arbitrarySize", () => {
    it("should match arbitrary size classes (no unit required)", () => {
      expect("size-[24]").toMatch(SIZING_PATTERNS.arbitrarySize);
      expect("size-[100]").toMatch(SIZING_PATTERNS.arbitrarySize);
    });

    it("should not match size with units (pattern only matches digits)", () => {
      // The size pattern is size-\[[0-9]+\] - only bare numbers
      // "size-[100px]" contains "size-[100" which matches [0-9]+ but then
      // expects \] but finds "p", so it does not match
      expect("size-[100px]").not.toMatch(SIZING_PATTERNS.arbitrarySize);
    });

    it("should not match token size classes", () => {
      expect("size-4").not.toMatch(SIZING_PATTERNS.arbitrarySize);
      expect("size-full").not.toMatch(SIZING_PATTERNS.arbitrarySize);
    });
  });
});

// =============================================================================
// Color Pattern Tests
// =============================================================================

describe("Color Patterns", () => {
  describe("COLOR_PATTERNS.rawTailwindColor", () => {
    it("should match raw Tailwind colors", () => {
      expect("bg-red-500").toMatch(COLOR_PATTERNS.rawTailwindColor);
      expect("text-blue-600").toMatch(COLOR_PATTERNS.rawTailwindColor);
      expect("border-green-400").toMatch(COLOR_PATTERNS.rawTailwindColor);
      // Note: gray/slate/zinc/stone are handled by a separate pattern, not rawTailwindColor
      expect("text-purple-700").toMatch(COLOR_PATTERNS.rawTailwindColor);
    });

    it("should not match non-bg/text/border prefixes", () => {
      // Pattern only matches bg|text|border prefixes, not ring
      expect("ring-yellow-300").not.toMatch(COLOR_PATTERNS.rawTailwindColor);
    });

    it("should not match semantic colors", () => {
      expect("bg-primary-9").not.toMatch(COLOR_PATTERNS.rawTailwindColor);
      expect("text-neutral-11").not.toMatch(COLOR_PATTERNS.rawTailwindColor);
      expect("border-success-9").not.toMatch(COLOR_PATTERNS.rawTailwindColor);
      expect("ring-error-7").not.toMatch(COLOR_PATTERNS.rawTailwindColor);
    });
  });

  describe("COLOR_PATTERNS.legacyNeutral", () => {
    it("should match legacy neutral patterns (50-950)", () => {
      expect("neutral-50").toMatch(COLOR_PATTERNS.legacyNeutral);
      expect("neutral-100").toMatch(COLOR_PATTERNS.legacyNeutral);
      expect("neutral-500").toMatch(COLOR_PATTERNS.legacyNeutral);
      expect("neutral-950").toMatch(COLOR_PATTERNS.legacyNeutral);
    });

    it("should not match Radix 1-12 scale", () => {
      expect("neutral-1").not.toMatch(COLOR_PATTERNS.legacyNeutral);
      expect("neutral-9").not.toMatch(COLOR_PATTERNS.legacyNeutral);
      expect("neutral-12").not.toMatch(COLOR_PATTERNS.legacyNeutral);
    });
  });
});

// =============================================================================
// Spacing Pattern Tests
// =============================================================================

describe("Spacing Patterns", () => {
  describe("SPACING_PATTERNS.arbitrarySpacing", () => {
    it("should match arbitrary spacing values with units", () => {
      expect("p-[20px]").toMatch(SPACING_PATTERNS.arbitrarySpacing);
      expect("m-[1rem]").toMatch(SPACING_PATTERNS.arbitrarySpacing);
      expect("px-[10px]").toMatch(SPACING_PATTERNS.arbitrarySpacing);
      expect("mt-[5px]").toMatch(SPACING_PATTERNS.arbitrarySpacing);
    });

    it("should not match values without units", () => {
      // Pattern requires px or rem unit
      expect("m-[1]").not.toMatch(SPACING_PATTERNS.arbitrarySpacing);
      expect("px-[10]").not.toMatch(SPACING_PATTERNS.arbitrarySpacing);
      expect("mt-[5]").not.toMatch(SPACING_PATTERNS.arbitrarySpacing);
    });

    it("should not match design token spacing", () => {
      expect("p-4").not.toMatch(SPACING_PATTERNS.arbitrarySpacing);
      expect("m-2").not.toMatch(SPACING_PATTERNS.arbitrarySpacing);
      expect("px-6").not.toMatch(SPACING_PATTERNS.arbitrarySpacing);
    });
  });

  describe("SPACING_PATTERNS.gapArbitrary", () => {
    it("should match arbitrary gap values with units", () => {
      expect("gap-[20px]").toMatch(SPACING_PATTERNS.gapArbitrary);
      expect("gap-[10rem]").toMatch(SPACING_PATTERNS.gapArbitrary);
    });

    it("should not match gap values without units", () => {
      // Pattern requires px or rem unit
      expect("gap-[10]").not.toMatch(SPACING_PATTERNS.gapArbitrary);
    });
  });
});

// =============================================================================
// Typography Pattern Tests
// =============================================================================

describe("Typography Patterns", () => {
  describe("TYPOGRAPHY_PATTERNS.arbitraryFontSize", () => {
    it("should match arbitrary font sizes with units", () => {
      expect("text-[14px]").toMatch(TYPOGRAPHY_PATTERNS.arbitraryFontSize);
      expect("text-[1.5rem]").toMatch(TYPOGRAPHY_PATTERNS.arbitraryFontSize);
    });

    it("should not match font sizes without units", () => {
      // Pattern requires px or rem unit
      expect("text-[1]").not.toMatch(TYPOGRAPHY_PATTERNS.arbitraryFontSize);
    });

    it("should not match design token font sizes", () => {
      expect("text-sm").not.toMatch(TYPOGRAPHY_PATTERNS.arbitraryFontSize);
      expect("text-base").not.toMatch(TYPOGRAPHY_PATTERNS.arbitraryFontSize);
      expect("text-lg").not.toMatch(TYPOGRAPHY_PATTERNS.arbitraryFontSize);
    });
  });

  describe("TYPOGRAPHY_PATTERNS.arbitraryLineHeight", () => {
    it("should match arbitrary line-height values (no unit required)", () => {
      // Pattern is leading-\[[0-9.]+\] - matches bare numbers only
      expect("leading-[1]").toMatch(TYPOGRAPHY_PATTERNS.arbitraryLineHeight);
      expect("leading-[1.5]").toMatch(TYPOGRAPHY_PATTERNS.arbitraryLineHeight);
      expect("leading-[24]").toMatch(TYPOGRAPHY_PATTERNS.arbitraryLineHeight);
    });

    it("should not match leading with units (pattern expects closing bracket after digits)", () => {
      // "leading-[24px]" - after "24", pattern expects "]" but finds "p"
      expect("leading-[24px]").not.toMatch(TYPOGRAPHY_PATTERNS.arbitraryLineHeight);
    });

    it("should not match design token line-heights", () => {
      expect("leading-none").not.toMatch(TYPOGRAPHY_PATTERNS.arbitraryLineHeight);
      expect("leading-tight").not.toMatch(TYPOGRAPHY_PATTERNS.arbitraryLineHeight);
      expect("leading-normal").not.toMatch(TYPOGRAPHY_PATTERNS.arbitraryLineHeight);
      expect("leading-relaxed").not.toMatch(TYPOGRAPHY_PATTERNS.arbitraryLineHeight);
    });
  });

  describe("TYPOGRAPHY_PATTERNS.arbitraryLetterSpacing", () => {
    it("should match arbitrary letter-spacing values with em or rem", () => {
      // Pattern requires em or rem unit (not px)
      expect("tracking-[0.02em]").toMatch(TYPOGRAPHY_PATTERNS.arbitraryLetterSpacing);
      expect("tracking-[0.5rem]").toMatch(TYPOGRAPHY_PATTERNS.arbitraryLetterSpacing);
    });

    it("should not match letter-spacing with px unit", () => {
      // Pattern only accepts em or rem, not px
      expect("tracking-[0.5px]").not.toMatch(
        TYPOGRAPHY_PATTERNS.arbitraryLetterSpacing
      );
    });

    it("should not match design token letter-spacing", () => {
      expect("tracking-tighter").not.toMatch(
        TYPOGRAPHY_PATTERNS.arbitraryLetterSpacing
      );
      expect("tracking-tight").not.toMatch(TYPOGRAPHY_PATTERNS.arbitraryLetterSpacing);
      expect("tracking-normal").not.toMatch(
        TYPOGRAPHY_PATTERNS.arbitraryLetterSpacing
      );
      expect("tracking-wide").not.toMatch(TYPOGRAPHY_PATTERNS.arbitraryLetterSpacing);
    });
  });
});

// =============================================================================
// Opacity Pattern Tests
// =============================================================================

describe("Opacity Patterns", () => {
  describe("OPACITY_PATTERNS.arbitraryOpacity", () => {
    it("should match arbitrary opacity values", () => {
      expect("opacity-[0.5]").toMatch(OPACITY_PATTERNS.arbitraryOpacity);
      expect("opacity-[0.8]").toMatch(OPACITY_PATTERNS.arbitraryOpacity);
      expect("opacity-[.75]").toMatch(OPACITY_PATTERNS.arbitraryOpacity);
    });

    it("should not match design token opacity", () => {
      expect("opacity-0").not.toMatch(OPACITY_PATTERNS.arbitraryOpacity);
      expect("opacity-50").not.toMatch(OPACITY_PATTERNS.arbitraryOpacity);
      expect("opacity-100").not.toMatch(OPACITY_PATTERNS.arbitraryOpacity);
    });
  });

  describe("OPACITY_PATTERNS.bgOpacity", () => {
    it("should match background opacity modifiers", () => {
      expect("bg-primary-9/[0.5]").toMatch(OPACITY_PATTERNS.bgOpacity);
      expect("text-neutral-12/[.8]").toMatch(OPACITY_PATTERNS.bgOpacity);
    });

    it("should not match token opacity modifiers", () => {
      expect("bg-primary-9/50").not.toMatch(OPACITY_PATTERNS.bgOpacity);
      expect("text-neutral-12/80").not.toMatch(OPACITY_PATTERNS.bgOpacity);
    });
  });
});

// =============================================================================
// Border Pattern Tests
// =============================================================================

describe("Border Patterns", () => {
  describe("BORDER_PATTERNS.arbitraryRadius", () => {
    it("should match arbitrary border-radius with units", () => {
      expect("rounded-[10px]").toMatch(BORDER_PATTERNS.arbitraryRadius);
      expect("rounded-[8rem]").toMatch(BORDER_PATTERNS.arbitraryRadius);
    });

    it("should not match border-radius without units", () => {
      // Pattern requires px or rem unit
      expect("rounded-[0]").not.toMatch(BORDER_PATTERNS.arbitraryRadius);
    });

    it("should not match design token radius", () => {
      expect("rounded-md").not.toMatch(BORDER_PATTERNS.arbitraryRadius);
      expect("rounded-lg").not.toMatch(BORDER_PATTERNS.arbitraryRadius);
      expect("rounded-full").not.toMatch(BORDER_PATTERNS.arbitraryRadius);
    });
  });
});

// =============================================================================
// Shadow Pattern Tests
// =============================================================================

describe("Shadow Patterns", () => {
  describe("SHADOW_PATTERNS.arbitraryShadow", () => {
    it("should match arbitrary shadow values with rgba", () => {
      expect("shadow-[0_2px_4px_rgba(0,0,0,0.1)]").toMatch(
        SHADOW_PATTERNS.arbitraryShadow
      );
    });

    it("should not match shadow values with hex colors (pattern requires rgba)", () => {
      // Pattern specifically requires rgba(...), not hex colors
      expect("shadow-[0_4px_6px_#00000026]").not.toMatch(
        SHADOW_PATTERNS.arbitraryShadow
      );
    });

    it("should not match shadow values with rgb (pattern requires rgba)", () => {
      // Pattern specifically requires rgba(...), not rgb(...)
      expect(
        "shadow-[0_1px_2px_0_rgb(0,0,0,0.05),0_1px_3px_0_rgb(0,0,0,0.1)]"
      ).not.toMatch(SHADOW_PATTERNS.arbitraryShadow);
    });

    it("should match inset shadows with rgba", () => {
      expect("shadow-[inset_0_2px_4px_rgba(0,0,0,0.1)]").toMatch(
        SHADOW_PATTERNS.arbitraryShadow
      );
    });

    it("should not match shadow-none override attempts (no rgba)", () => {
      // Pattern requires rgba(...) content
      expect("shadow-[none]").not.toMatch(SHADOW_PATTERNS.arbitraryShadow);
    });

    it("should not match standard Tailwind shadow tokens", () => {
      expect("shadow-sm").not.toMatch(SHADOW_PATTERNS.arbitraryShadow);
      expect("shadow-md").not.toMatch(SHADOW_PATTERNS.arbitraryShadow);
      expect("shadow-lg").not.toMatch(SHADOW_PATTERNS.arbitraryShadow);
      expect("shadow-xl").not.toMatch(SHADOW_PATTERNS.arbitraryShadow);
      expect("shadow-2xl").not.toMatch(SHADOW_PATTERNS.arbitraryShadow);
      expect("shadow-none").not.toMatch(SHADOW_PATTERNS.arbitraryShadow);
    });

    it("should not match custom design token shadows", () => {
      expect("shadow-soft").not.toMatch(SHADOW_PATTERNS.arbitraryShadow);
      expect("shadow-elevated").not.toMatch(SHADOW_PATTERNS.arbitraryShadow);
      expect("shadow-modal").not.toMatch(SHADOW_PATTERNS.arbitraryShadow);
    });
  });

  describe("SHADOW_PATTERNS.inlineBoxShadow", () => {
    it("should match inline box-shadow styles", () => {
      expect('style="box-shadow: 0 2px 4px rgba(0,0,0,0.1);"').toMatch(
        SHADOW_PATTERNS.inlineBoxShadow
      );
    });

    it("should match box-shadow with multiple values", () => {
      expect('style="box-shadow: 0 1px 2px #000, 0 2px 4px #000;"').toMatch(
        SHADOW_PATTERNS.inlineBoxShadow
      );
    });
  });
});

// =============================================================================
// Z-Index Pattern Tests
// =============================================================================

describe("Z-Index Patterns", () => {
  describe("ZINDEX_PATTERNS.arbitraryZIndex", () => {
    it("should match arbitrary z-index values", () => {
      expect("z-[100]").toMatch(ZINDEX_PATTERNS.arbitraryZIndex);
      expect("z-[999]").toMatch(ZINDEX_PATTERNS.arbitraryZIndex);
    });

    it("should not match design token z-index", () => {
      expect("z-10").not.toMatch(ZINDEX_PATTERNS.arbitraryZIndex);
      expect("z-50").not.toMatch(ZINDEX_PATTERNS.arbitraryZIndex);
    });
  });

  describe("ZINDEX_PATTERNS.nonTokenZIndex", () => {
    it("should match non-token z-index values", () => {
      // z-index values not in our token system
      expect("z-100").toMatch(ZINDEX_PATTERNS.nonTokenZIndex);
      expect("z-999").toMatch(ZINDEX_PATTERNS.nonTokenZIndex);
    });

    it("should not match token z-index values", () => {
      expect("z-0").not.toMatch(ZINDEX_PATTERNS.nonTokenZIndex);
      expect("z-10").not.toMatch(ZINDEX_PATTERNS.nonTokenZIndex);
      expect("z-50").not.toMatch(ZINDEX_PATTERNS.nonTokenZIndex);
      expect("z-60").not.toMatch(ZINDEX_PATTERNS.nonTokenZIndex);
    });
  });
});

// =============================================================================
// Animation Pattern Tests
// =============================================================================

describe("Animation Patterns", () => {
  describe("ANIMATION_PATTERNS.arbitraryDuration", () => {
    it("should match arbitrary duration values with units", () => {
      expect("duration-[200ms]").toMatch(ANIMATION_PATTERNS.arbitraryDuration);
      // Pattern uses [0-9]+ (integers only), so use integer values
      expect("duration-[1s]").toMatch(ANIMATION_PATTERNS.arbitraryDuration);
    });

    it("should not match decimal duration values", () => {
      // Pattern uses [0-9]+ which only matches integers, not decimals
      expect("duration-[0.5s]").not.toMatch(ANIMATION_PATTERNS.arbitraryDuration);
    });

    it("should not match duration without units", () => {
      // Pattern requires ms or s unit
      expect("duration-[0]").not.toMatch(ANIMATION_PATTERNS.arbitraryDuration);
    });

    it("should not match design token durations", () => {
      expect("duration-150").not.toMatch(ANIMATION_PATTERNS.arbitraryDuration);
      expect("duration-300").not.toMatch(ANIMATION_PATTERNS.arbitraryDuration);
    });
  });

  describe("ANIMATION_PATTERNS.inlineTransition", () => {
    it("should match inline transition with duration", () => {
      expect('style="transition: all 0.2s"').toMatch(
        ANIMATION_PATTERNS.inlineTransition
      );
      expect('style="transition: opacity 300ms"').toMatch(
        ANIMATION_PATTERNS.inlineTransition
      );
    });
  });
});

// =============================================================================
// categorizeViolation Tests
// =============================================================================

describe("categorizeViolation", () => {
  it("should categorize sizing violations", () => {
    expect(categorizeViolation("h-[42px]")).toBe("sizing");
    expect(categorizeViolation("w-[200px]")).toBe("sizing");
  });

  it("should categorize color violations", () => {
    expect(categorizeViolation("bg-red-500")).toBe("color");
    expect(categorizeViolation("text-gray-700")).toBe("color");
    expect(categorizeViolation("neutral-100")).toBe("color");
  });

  it("should categorize spacing violations", () => {
    expect(categorizeViolation("p-[20px]")).toBe("spacing");
    expect(categorizeViolation("gap-[10px]")).toBe("spacing");
  });

  it("should categorize typography violations", () => {
    expect(categorizeViolation("text-[14px]")).toBe("typography");
    // leading pattern matches bare numbers: leading-\[[0-9.]+\]
    expect(categorizeViolation("leading-[24]")).toBe("typography");
    // tracking pattern requires em or rem unit
    expect(categorizeViolation("tracking-[0.02em]")).toBe("typography");
  });

  it("should not categorize typography with wrong units", () => {
    // leading-[24px] does not match leading-\[[0-9.]+\] (expects ] after digits)
    expect(categorizeViolation("leading-[24px]")).toBeNull();
    // tracking-[0.5px] does not match tracking-\[[0-9.]+(em|rem)\] (px is not em|rem)
    expect(categorizeViolation("tracking-[0.5px]")).toBeNull();
  });

  it("should categorize border violations", () => {
    expect(categorizeViolation("rounded-[10px]")).toBe("border");
  });

  it("should categorize shadow violations", () => {
    expect(categorizeViolation("shadow-[0_2px_4px_rgba(0,0,0,0.1)]")).toBe("shadow");
  });

  it("should categorize z-index violations", () => {
    expect(categorizeViolation("z-[100]")).toBe("zindex");
  });

  it("should categorize animation violations", () => {
    expect(categorizeViolation("duration-[200ms]")).toBe("animation");
  });

  it("should return null for non-violations", () => {
    expect(categorizeViolation("bg-primary-9")).toBeNull();
    // Note: Radix single-digit scale (1-9) is correctly not matched
    expect(categorizeViolation("text-neutral-9")).toBeNull();
    expect(categorizeViolation("p-4")).toBeNull();
    expect(categorizeViolation("rounded-lg")).toBeNull();
  });
});

// =============================================================================
// getSuggestion Tests
// =============================================================================

describe("getSuggestion", () => {
  it("should provide sizing suggestions", () => {
    const suggestion = getSuggestion("h-[42px]", "sizing");
    // Returns generic suggestion to use Tailwind spacing scale
    expect(suggestion).toContain("Tailwind spacing scale");
    expect(suggestion).toContain("arbitrary values");
  });

  it("should provide color suggestions", () => {
    const suggestion = getSuggestion("bg-red-500", "color");
    expect(suggestion).toBeTruthy();
  });

  it("should provide gray to neutral migration suggestion", () => {
    const suggestion = getSuggestion("text-gray-700", "color");
    // getSuggestion checks for gray/slate/zinc/stone and suggests neutral scale
    expect(suggestion).toContain("neutral");
  });

  it("should provide spacing suggestions", () => {
    const suggestion = getSuggestion("p-[20px]", "spacing");
    expect(suggestion).toBeTruthy();
  });

  it("should provide typography suggestions", () => {
    const suggestion = getSuggestion("text-[14px]", "typography");
    expect(suggestion).toBeTruthy();
  });

  it("should provide border radius suggestions", () => {
    const suggestion = getSuggestion("rounded-[8px]", "border");
    expect(suggestion).toBeTruthy();
  });

  it("should provide shadow suggestions", () => {
    const suggestion = getSuggestion(
      "shadow-[0_2px_4px_rgba(0,0,0,0.1)]",
      "shadow"
    );
    expect(suggestion).toBeTruthy();
  });

  it("should provide default suggestions for categories", () => {
    // Default suggestions should always return something for known categories
    expect(getSuggestion("unknown-pattern", "sizing")).toBeTruthy();
    expect(getSuggestion("unknown-pattern", "color")).toBeTruthy();
    expect(getSuggestion("unknown-pattern", "spacing")).toBeTruthy();
    expect(getSuggestion("unknown-pattern", "typography")).toBeTruthy();
    expect(getSuggestion("unknown-pattern", "shadow")).toBeTruthy();
  });
});

// =============================================================================
// Legitimate Pattern Functions
// =============================================================================

describe("isLegitimateSizing", () => {
  describe("viewport-relative patterns", () => {
    it("should allow viewport-relative heights", () => {
      // Matches [hw]-\[[0-9]+(vh|vw)\]
      expect(isLegitimateSizing("h-[80vh]")).toBe(true);
      // Matches max-[hw]-\[[0-9]+(vh|vw)\]
      expect(isLegitimateSizing("max-h-[90vh]")).toBe(true);
      expect(isLegitimateSizing("max-h-[80vh]")).toBe(true);
      // Matches min-[hw]-\[[0-9]+(vh|vw)\]
      expect(isLegitimateSizing("min-h-[50vh]")).toBe(true);
    });

    it("should allow viewport-relative widths", () => {
      expect(isLegitimateSizing("max-w-[80vw]")).toBe(true);
      expect(isLegitimateSizing("w-[100vw]")).toBe(true);
    });
  });

  describe("calc-based patterns", () => {
    it("should allow calc-based values", () => {
      expect(isLegitimateSizing("h-[calc(100vh-48px)]")).toBe(true);
      expect(isLegitimateSizing("max-h-[calc(100vh-200px)]")).toBe(true);
      expect(isLegitimateSizing("min-h-[calc(100vh-60px)]")).toBe(true);
    });
  });

  describe("SVG and media dimensions", () => {
    it("should allow SVG/canvas/media sizing", () => {
      expect(isLegitimateSizing('<svg viewBox="0 0 100 100">')).toBe(true);
      expect(isLegitimateSizing("canvas")).toBe(true);
      expect(isLegitimateSizing("<Image")).toBe(true);
    });
  });

  describe("CSS custom properties and component props", () => {
    it("should allow var(--) and width/height props", () => {
      expect(isLegitimateSizing("var(--sidebar-width)")).toBe(true);
      expect(isLegitimateSizing("width={100}")).toBe(true);
    });
  });

  describe("small functional widths", () => {
    it("should allow 1px, 2px, 4px divider/border widths", () => {
      // Matches [hw]-\[(1|2|4)px\]
      expect(isLegitimateSizing("h-[1px]")).toBe(true);
      expect(isLegitimateSizing("w-[2px]")).toBe(true);
      expect(isLegitimateSizing("h-[4px]")).toBe(true);
    });
  });

  describe("workflow node widths", () => {
    it("should allow standard workflow node width with component context", () => {
      // Requires component name AND w-[180px]
      expect(isLegitimateSizing("LLMNode w-[180px]")).toBe(true);
      expect(isLegitimateSizing("ToolNode w-[180px]")).toBe(true);
    });

    it("should NOT allow workflow node width without component context", () => {
      // Without component name, w-[180px] is not in the common layout widths list
      expect(isLegitimateSizing("w-[180px]")).toBe(false);
    });
  });

  describe("dialog/modal heights", () => {
    it("should allow dialog heights with component context", () => {
      // Requires Dialog/Modal/Drawer context AND specific sizes
      expect(isLegitimateSizing("Dialog h-[400px]")).toBe(true);
      expect(isLegitimateSizing("Modal w-[600px]")).toBe(true);
    });
  });

  describe("artifact viewer heights", () => {
    it("should allow artifact viewer heights with component context", () => {
      expect(isLegitimateSizing("MermaidArtifact h-[400px]")).toBe(true);
      expect(isLegitimateSizing("CodeViewer h-[600px]")).toBe(true);
    });
  });

  describe("common layout widths", () => {
    it("should allow common layout widths (w- prefix)", () => {
      // Matches w-\[(200|300|320|400|500|600|800)px\]
      expect(isLegitimateSizing("w-[200px]")).toBe(true);
      expect(isLegitimateSizing("w-[300px]")).toBe(true);
      expect(isLegitimateSizing("w-[320px]")).toBe(true);
      expect(isLegitimateSizing("w-[400px]")).toBe(true);
      expect(isLegitimateSizing("w-[500px]")).toBe(true);
      expect(isLegitimateSizing("w-[600px]")).toBe(true);
      expect(isLegitimateSizing("w-[800px]")).toBe(true);
    });

    it("should also match min-w and max-w containing common layout widths", () => {
      // The w-[...] pattern is unanchored, so min-w-[200px] contains "w-[200px]"
      // and matches the common layout widths regex
      expect(isLegitimateSizing("min-w-[200px]")).toBe(true);
      expect(isLegitimateSizing("max-w-[300px]")).toBe(true);
    });

    it("should NOT allow widths not in the common layout list", () => {
      expect(isLegitimateSizing("w-[175px]")).toBe(false);
      expect(isLegitimateSizing("w-[250px]")).toBe(false);
    });
  });

  describe("non-legitimate patterns", () => {
    it("should NOT allow arbitrary pixel values without justification", () => {
      expect(isLegitimateSizing("h-[42px]")).toBe(false);
      expect(isLegitimateSizing("w-[175px]")).toBe(false);
    });

    it("should NOT allow percentage-based values (not in implementation)", () => {
      // No percentage pattern in isLegitimateSizing
      expect(isLegitimateSizing("max-w-[70%]")).toBe(false);
      expect(isLegitimateSizing("max-w-[80%]")).toBe(false);
    });

    it("should NOT allow arbitrary min/max heights without context", () => {
      expect(isLegitimateSizing("min-h-[40px]")).toBe(false);
      expect(isLegitimateSizing("max-h-[200px]")).toBe(false);
      expect(isLegitimateSizing("min-h-[44px]")).toBe(false);
      expect(isLegitimateSizing("min-w-[44px]")).toBe(false);
    });

    it("should NOT allow arbitrary h-[...] heights not in a known pattern", () => {
      // h-[300px] etc. are NOT in common layout widths (that's w- only)
      expect(isLegitimateSizing("h-[300px]")).toBe(false);
    });
  });
});

describe("isLegitimateSpacing", () => {
  describe("viewport-relative padding", () => {
    it("should allow viewport-relative padding", () => {
      // Pattern: p(t|b|l|r|x|y)?-\[[0-9]+(vh|vw)\]
      expect(isLegitimateSpacing("pt-[20vh]")).toBe(true);
      expect(isLegitimateSpacing("pb-[10vh]")).toBe(true);
      expect(isLegitimateSpacing("p-[5vw]")).toBe(true);
    });
  });

  describe("negative margins", () => {
    it("should allow negative margin patterns", () => {
      // Pattern: -m(t|b|l|r|x|y)?-\[
      expect(isLegitimateSpacing("-mt-[4px]")).toBe(true);
      expect(isLegitimateSpacing("-ml-[8px]")).toBe(true);
    });
  });

  describe("CSS custom properties and calc", () => {
    it("should allow var(--) and calc() patterns", () => {
      expect(isLegitimateSpacing("var(--spacing)")).toBe(true);
      expect(isLegitimateSpacing("calc(100% - 20px)")).toBe(true);
    });
  });

  describe("transform/translate", () => {
    it("should allow transform and translate contexts", () => {
      expect(isLegitimateSpacing("transform")).toBe(true);
      expect(isLegitimateSpacing("translate")).toBe(true);
    });
  });

  describe("command palette padding", () => {
    it("should allow command palette viewport padding", () => {
      expect(isLegitimateSpacing("AICommandPalette pt-[20vh]")).toBe(true);
      expect(isLegitimateSpacing("GenericCommandPalette pt-[20vh]")).toBe(true);
    });
  });

  describe("non-legitimate patterns", () => {
    it("should NOT allow arbitrary pixel spacing", () => {
      expect(isLegitimateSpacing("ml-[72px]")).toBe(false);
      expect(isLegitimateSpacing("p-[20px]")).toBe(false);
      expect(isLegitimateSpacing("mt-[15px]")).toBe(false);
    });

    it("should NOT allow viewport-relative margins (only padding is recognized)", () => {
      // The implementation only matches p-prefixed viewport units, not m-prefixed
      expect(isLegitimateSpacing("mt-[5vh]")).toBe(false);
      expect(isLegitimateSpacing("ml-[10vw]")).toBe(false);
    });
  });
});

// =============================================================================
// RIPGREP_PATTERNS Coverage Tests
// =============================================================================

describe("RIPGREP_PATTERNS structure", () => {
  it("should have patterns for all categories", () => {
    const expectedCategories: ViolationCategory[] = [
      "sizing",
      "color",
      "spacing",
      "typography",
      "border",
      "shadow",
      "zindex",
      "animation",
    ];

    for (const category of expectedCategories) {
      expect(RIPGREP_PATTERNS[category]).toBeDefined();
      expect(RIPGREP_PATTERNS[category].length).toBeGreaterThan(0);
    }
  });

  it("should have multiple sizing patterns", () => {
    expect(RIPGREP_PATTERNS.sizing.length).toBeGreaterThanOrEqual(2);
  });

  it("should have multiple color patterns", () => {
    expect(RIPGREP_PATTERNS.color.length).toBeGreaterThanOrEqual(2);
  });
});

// =============================================================================
// NEW PATTERN TESTS - Border Width, Primary-9 Contrast, Test ID Kebab Case
// =============================================================================

describe("Border Width Patterns", () => {
  describe("BORDER_PATTERNS.arbitraryWidth", () => {
    it("should match arbitrary border widths", () => {
      expect("border-[2px]").toMatch(BORDER_PATTERNS.arbitraryWidth);
      expect("border-[3px]").toMatch(BORDER_PATTERNS.arbitraryWidth);
      expect("border-[4px]").toMatch(BORDER_PATTERNS.arbitraryWidth);
    });

    it("should not match standard border tokens", () => {
      expect("border").not.toMatch(BORDER_PATTERNS.arbitraryWidth);
      expect("border-2").not.toMatch(BORDER_PATTERNS.arbitraryWidth);
      expect("border-4").not.toMatch(BORDER_PATTERNS.arbitraryWidth);
    });
  });
});

describe("Color Pattern - Gray/Slate/Zinc/Stone Scale", () => {
  // Last color pattern matches gray/slate/zinc/stone scale colors
  const grayScalePattern = toRegex(
    RIPGREP_PATTERNS.color[RIPGREP_PATTERNS.color.length - 1]
  );

  it("should match gray-scale colors with bg/text/border prefix", () => {
    expect("bg-gray-100").toMatch(grayScalePattern);
    expect("text-slate-700").toMatch(grayScalePattern);
    expect("border-zinc-300").toMatch(grayScalePattern);
    expect("bg-stone-200").toMatch(grayScalePattern);
  });

  it("should not match semantic colors (Radix scale)", () => {
    // Semantic colors like primary-9 are not in the gray-scale pattern
    expect("text-primary-9").not.toMatch(grayScalePattern);
    expect("text-primary-11").not.toMatch(grayScalePattern);
    expect("text-primary-12").not.toMatch(grayScalePattern);
  });

  it("should not match Radix neutral scale (1-12)", () => {
    expect("text-neutral-9").not.toMatch(grayScalePattern);
    expect("bg-neutral-3").not.toMatch(grayScalePattern);
  });
});

describe("Test ID Kebab Case Patterns", () => {
  // testid category should exist and have patterns
  it("should have testid category in RIPGREP_PATTERNS", () => {
    expect(RIPGREP_PATTERNS.testid).toBeDefined();
    expect(RIPGREP_PATTERNS.testid.length).toBeGreaterThan(0);
  });

  const testIdPattern = toRegex(RIPGREP_PATTERNS.testid[0]);

  it("should match camelCase test IDs", () => {
    expect('data-testid="fileUploadButton"').toMatch(testIdPattern);
    expect('data-testid="userProfileCard"').toMatch(testIdPattern);
    expect('data-testid="sendButton"').toMatch(testIdPattern);
  });

  it("should not match kebab-case test IDs (valid)", () => {
    expect('data-testid="file-upload-button"').not.toMatch(testIdPattern);
    expect('data-testid="user-profile-card"').not.toMatch(testIdPattern);
    expect('data-testid="send-button"').not.toMatch(testIdPattern);
  });

  it("should not match single-word test IDs (valid)", () => {
    expect('data-testid="button"').not.toMatch(testIdPattern);
    expect('data-testid="modal"').not.toMatch(testIdPattern);
  });
});
