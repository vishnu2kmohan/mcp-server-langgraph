/**
 * Design System Tokens
 *
 * Central definition of design tokens for the Agent Studio frontend.
 * These tokens map to Tailwind CSS classes and ensure consistency.
 */

/**
 * Color Palette
 * Aligned with Tailwind CSS default palette
 */
export const colors = {
  // Primary brand colors (Blue)
  primary: {
    50: "#eff6ff",
    100: "#dbeafe",
    200: "#bfdbfe",
    300: "#93c5fd",
    400: "#60a5fa",
    500: "#3b82f6",
    600: "#2563eb",
    700: "#1d4ed8",
    800: "#1e40af",
    900: "#1e3a8a",
  },

  // Gray scale
  gray: {
    50: "#f9fafb",
    100: "#f3f4f6",
    200: "#e5e7eb",
    300: "#d1d5db",
    400: "#9ca3af",
    500: "#6b7280",
    600: "#4b5563",
    700: "#374151",
    800: "#1f2937",
    900: "#111827",
  },

  // Semantic colors
  success: {
    50: "#f0fdf4",
    100: "#dcfce7",
    500: "#22c55e",
    600: "#16a34a",
    700: "#15803d",
  },

  warning: {
    50: "#fffbeb",
    100: "#fef3c7",
    500: "#f59e0b",
    600: "#d97706",
    700: "#b45309",
  },

  error: {
    50: "#fef2f2",
    100: "#fee2e2",
    500: "#ef4444",
    600: "#dc2626",
    700: "#b91c1c",
  },

  info: {
    50: "#f0f9ff",
    100: "#e0f2fe",
    500: "#0ea5e9",
    600: "#0284c7",
    700: "#0369a1",
  },

  // Grafana brand colors (for observability integration)
  grafana: {
    50: "#fff8f3",
    100: "#ffefe5",
    200: "#ffd9c2",
    300: "#ffbe94",
    400: "#ff9a5c",
    500: "#F46800", // Official Grafana brand orange
    600: "#db5d00",
    700: "#b84e00",
    800: "#944000",
    900: "#763300",
  },

  // AI/Insights semantic colors (purple theme for AI features)
  insight: {
    50: "#faf5ff",
    100: "#f3e8ff",
    200: "#e9d5ff",
    300: "#d8b4fe",
    400: "#c084fc",
    500: "#a855f7", // Main AI insight purple
    600: "#9333ea",
    700: "#7e22ce",
    800: "#6b21a8",
    900: "#581c87",
  },

  // Background colors
  background: {
    light: "#ffffff",
    lightAlt: "#f9fafb",
    dark: "#1f2937",
    darkAlt: "#111827",
  },

  // Text colors
  text: {
    primary: "#1f2937",
    secondary: "#4b5563",
    muted: "#9ca3af",
    disabled: "#d1d5db",
    primaryDark: "#f9fafb",
    secondaryDark: "#d1d5db",
  },
} as const;

/**
 * Typography Scale
 */
export const typography = {
  fontFamily: {
    sans: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    mono: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
  },

  fontSize: {
    xs: "0.75rem", // 12px
    sm: "0.875rem", // 14px
    base: "1rem", // 16px
    lg: "1.125rem", // 18px
    xl: "1.25rem", // 20px
    "2xl": "1.5rem", // 24px
    "3xl": "1.875rem", // 30px
    "4xl": "2.25rem", // 36px
  },

  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },

  lineHeight: {
    none: 1,
    tight: 1.25,
    snug: 1.375,
    normal: 1.5,
    relaxed: 1.625,
    loose: 2,
  },

  letterSpacing: {
    tighter: "-0.05em",
    tight: "-0.025em",
    normal: "0",
    wide: "0.025em",
    wider: "0.05em",
  },
} as const;

/**
 * Spacing Scale
 * Based on 0.25rem (4px) increments
 */
export const spacing = {
  0: "0",
  0.5: "0.125rem",
  1: "0.25rem",
  1.5: "0.375rem",
  2: "0.5rem",
  2.5: "0.625rem",
  3: "0.75rem",
  3.5: "0.875rem",
  4: "1rem",
  5: "1.25rem",
  6: "1.5rem",
  7: "1.75rem",
  8: "2rem",
  9: "2.25rem",
  10: "2.5rem",
  12: "3rem",
  14: "3.5rem",
  16: "4rem",
  20: "5rem",
  24: "6rem",
} as const;

/**
 * Shadow Tokens
 */
export const shadows = {
  none: "none",
  sm: "0 1px 2px 0 rgb(0 0 0 / 0.05)",
  md: "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)",
  lg: "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)",
  xl: "0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)",
  "2xl": "0 25px 50px -12px rgb(0 0 0 / 0.25)",
  inner: "inset 0 2px 4px 0 rgb(0 0 0 / 0.05)",
} as const;

/**
 * Border Radius
 */
export const borderRadius = {
  none: "0",
  sm: "0.125rem",
  md: "0.375rem",
  lg: "0.5rem",
  xl: "0.75rem",
  "2xl": "1rem",
  "3xl": "1.5rem",
  full: "9999px",
} as const;

/**
 * Responsive Breakpoints
 */
export const breakpoints = {
  sm: "640px",
  md: "768px",
  lg: "1024px",
  xl: "1280px",
  "2xl": "1536px",
} as const;

/**
 * Z-Index Scale
 * Matches the z-index system in the codebase
 */
export const zIndex = {
  base: 0,
  tooltip: 10,
  dropdown: 50,
  panel: 50,
  commandPalette: 55,
  modal: 60,
  notification: 65,
  systemAlert: 70,
  toast: 75,
} as const;

/**
 * Animation Durations
 */
export const animation = {
  duration: {
    fast: "150ms",
    normal: "300ms",
    slow: "500ms",
  },
  easing: {
    default: "ease-in-out",
    in: "ease-in",
    out: "ease-out",
    inOut: "ease-in-out",
  },
} as const;

/**
 * Helper: Get color value by path (e.g., "primary.500")
 */
export function getColorValue(path: string): string | undefined {
  const parts = path.split(".");
  const group = parts[0];
  const shade = parts[1];
  if (!group || !shade) return undefined;
  const colorGroup = colors[group as keyof typeof colors];

  if (!colorGroup || typeof colorGroup !== "object") {
    return undefined;
  }

  return (colorGroup as Record<string, string>)[shade];
}

/**
 * Helper: Get spacing value by key
 */
export function getSpacingValue(key: keyof typeof spacing): string {
  return spacing[key];
}

/**
 * Export all tokens as a single object for external use
 */
export const designTokens = {
  colors,
  typography,
  spacing,
  shadows,
  borderRadius,
  breakpoints,
  zIndex,
  animation,
} as const;

export default designTokens;
