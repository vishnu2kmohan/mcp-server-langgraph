/**
 * Accessibility Utilities
 *
 * Helper functions for WCAG compliance checking,
 * color contrast validation, and accessibility testing.
 */

export interface RGB {
  r: number;
  g: number;
  b: number;
}

/**
 * Convert hex color to RGB values
 */
export function hexToRgb(hex: string): RGB {
  // Remove # if present
  const cleanHex = hex.replace("#", "");

  // Handle 3-digit hex
  let fullHex = cleanHex;
  if (cleanHex.length === 3) {
    fullHex = cleanHex
      .split("")
      .map((c) => c + c)
      .join("");
  }

  const result = /^([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(fullHex);

  if (!result) {
    return { r: 0, g: 0, b: 0 };
  }

  const rHex = result[1];
  const gHex = result[2];
  const bHex = result[3];

  return {
    r: rHex ? parseInt(rHex, 16) : 0,
    g: gHex ? parseInt(gHex, 16) : 0,
    b: bHex ? parseInt(bHex, 16) : 0,
  };
}

/**
 * Calculate relative luminance of a color
 * Based on WCAG 2.1 formula
 * https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
 */
export function getRelativeLuminance(r: number, g: number, b: number): number {
  const convertChannel = (c: number): number => {
    const sRGB = c / 255;
    return sRGB <= 0.03928
      ? sRGB / 12.92
      : Math.pow((sRGB + 0.055) / 1.055, 2.4);
  };

  const rs = convertChannel(r);
  const gs = convertChannel(g);
  const bs = convertChannel(b);

  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

/**
 * Calculate contrast ratio between two colors
 * Based on WCAG 2.1 formula
 * https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio
 */
export function calculateContrastRatio(
  foreground: string,
  background: string,
): number {
  const fg = hexToRgb(foreground);
  const bg = hexToRgb(background);

  const fgLuminance = getRelativeLuminance(fg.r, fg.g, fg.b);
  const bgLuminance = getRelativeLuminance(bg.r, bg.g, bg.b);

  const lighter = Math.max(fgLuminance, bgLuminance);
  const darker = Math.min(fgLuminance, bgLuminance);

  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Check if colors meet WCAG 2.1 AA standards
 * - Normal text: 4.5:1 minimum
 * - Large text (18pt+ or 14pt+ bold): 3:1 minimum
 */
export function meetsWCAGAA(
  foreground: string,
  background: string,
  isLargeText: boolean = false,
): boolean {
  const ratio = calculateContrastRatio(foreground, background);
  const threshold = isLargeText ? 3 : 4.5;
  return ratio >= threshold;
}

/**
 * Check if colors meet WCAG 2.1 AAA standards
 * - Normal text: 7:1 minimum
 * - Large text (18pt+ or 14pt+ bold): 4.5:1 minimum
 */
export function meetsWCAGAAA(
  foreground: string,
  background: string,
  isLargeText: boolean = false,
): boolean {
  const ratio = calculateContrastRatio(foreground, background);
  const threshold = isLargeText ? 4.5 : 7;
  return ratio >= threshold;
}

/**
 * Color palette for accessibility validation
 * These are the Tailwind colors commonly used in the app
 */
export const colorPalette = {
  // Text colors (Radix scale)
  textPrimary: "#1f2937", // neutral-12
  textSecondary: "#4b5563", // neutral-11
  textMuted: "#9ca3af", // neutral-9
  textDisabled: "#d1d5db", // neutral-5

  // Background colors
  bgWhite: "#ffffff",
  bgGray50: "#f9fafb",
  bgGray100: "#f3f4f6",
  bgGray800: "#1f2937",
  bgGray900: "#111827",

  // Brand colors
  blue500: "#3b82f6",
  blue600: "#2563eb",
  green500: "#22c55e",
  green600: "#16a34a",
  red500: "#ef4444",
  red600: "#dc2626",
  yellow500: "#eab308",
  amber500: "#f59e0b",
};

/**
 * Validate common text/background combinations
 * Returns array of failing combinations
 */
export function validateColorContrast(): Array<{
  foreground: string;
  background: string;
  ratio: number;
  passes: boolean;
}> {
  const combinations = [
    {
      fg: colorPalette.textPrimary,
      bg: colorPalette.bgWhite,
      name: "Primary text on white",
    },
    {
      fg: colorPalette.textSecondary,
      bg: colorPalette.bgWhite,
      name: "Secondary text on white",
    },
    {
      fg: colorPalette.textMuted,
      bg: colorPalette.bgWhite,
      name: "Muted text on white",
    },
    {
      fg: colorPalette.blue600,
      bg: colorPalette.bgWhite,
      name: "Blue link on white",
    },
    {
      fg: colorPalette.red600,
      bg: colorPalette.bgWhite,
      name: "Red error on white",
    },
    { fg: "#ffffff", bg: colorPalette.bgGray800, name: "White text on dark" },
    { fg: "#d1d5db", bg: colorPalette.bgGray800, name: "Gray text on dark" },
  ];

  return combinations.map(({ fg, bg }) => {
    const ratio = calculateContrastRatio(fg, bg);
    return {
      foreground: fg,
      background: bg,
      ratio,
      passes: ratio >= 4.5,
    };
  });
}
