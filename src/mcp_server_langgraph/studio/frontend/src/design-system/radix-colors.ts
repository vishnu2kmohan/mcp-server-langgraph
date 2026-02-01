/**
 * Radix Colors Integration
 *
 * Maps Radix color scales to semantic names for the Agent Studio design system.
 * Supports 4 theme presets: violet-sage (default), teal-sage, violet-olive, teal-olive.
 *
 * @see https://www.radix-ui.com/colors
 */

// Theme types
export type ColorTheme =
  | "violet-sage"
  | "teal-sage"
  | "violet-olive"
  | "teal-olive";
export type FontTheme = "jetbrains" | "firacode" | "monaspace";

// Radix color scale names
export type RadixAccentColor =
  | "tomato"
  | "red"
  | "ruby"
  | "crimson"
  | "pink"
  | "plum"
  | "purple"
  | "violet"
  | "iris"
  | "indigo"
  | "blue"
  | "cyan"
  | "teal"
  | "jade"
  | "green"
  | "grass"
  | "bronze"
  | "gold"
  | "brown"
  | "orange"
  | "amber"
  | "yellow"
  | "lime"
  | "mint"
  | "sky";

export type RadixGrayColor =
  | "gray"
  | "mauve"
  | "slate"
  | "sage"
  | "olive"
  | "sand";

// Semantic color names used throughout the app
export type SemanticColor =
  | "primary"
  | "success"
  | "warning"
  | "error"
  | "info"
  | "insight"
  | "neutral"
  | "grafana";

// Radix uses 1-12 scale
export type RadixStep = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12;

// Tailwind uses 50-950 scale
export type TailwindShade =
  | 50
  | 100
  | 200
  | 300
  | 400
  | 500
  | 600
  | 700
  | 800
  | 900
  | 950;

/**
 * Maps Tailwind shade numbers (50-950) to Radix step numbers (1-12).
 * This enables backward compatibility during migration.
 */
export const TAILWIND_TO_RADIX_MAP: Record<TailwindShade, RadixStep> = {
  50: 1,
  100: 2,
  200: 3,
  300: 4,
  400: 5,
  500: 9, // Primary/action color
  600: 10,
  700: 11,
  800: 11,
  900: 12,
  950: 12,
} as const;

/**
 * Semantic color mappings for each theme preset.
 * Each theme maps semantic names to Radix color scales.
 */
export const THEME_COLOR_MAPPINGS: Record<
  ColorTheme,
  Record<SemanticColor, RadixAccentColor | RadixGrayColor>
> = {
  "violet-sage": {
    primary: "violet",
    success: "grass",
    warning: "amber",
    error: "ruby",
    info: "sky",
    insight: "violet",
    neutral: "slate",
    grafana: "orange",
  },
  "teal-sage": {
    primary: "teal",
    success: "grass",
    warning: "amber",
    error: "ruby",
    info: "sky",
    insight: "violet",
    neutral: "slate",
    grafana: "orange",
  },
  "violet-olive": {
    primary: "violet",
    success: "grass",
    warning: "amber",
    error: "ruby",
    info: "sky",
    insight: "violet",
    neutral: "olive",
    grafana: "orange",
  },
  "teal-olive": {
    primary: "teal",
    success: "grass",
    warning: "amber",
    error: "ruby",
    info: "sky",
    insight: "violet",
    neutral: "olive",
    grafana: "orange",
  },
} as const;

/**
 * Default theme preset
 */
export const DEFAULT_COLOR_THEME: ColorTheme = "violet-sage";
export const DEFAULT_FONT_THEME: FontTheme = "jetbrains";

/**
 * Get the Radix color variable for a semantic color and step.
 *
 * @example
 * getSemanticColorVar('primary', 9) // 'var(--primary-9)'
 */
export function getSemanticColorVar(
  color: SemanticColor,
  step: RadixStep,
): string {
  return `var(--${color}-${step})`;
}

/**
 * Get the Radix color variable using Tailwind shade notation (for backward compatibility).
 *
 * @example
 * getSemanticColorVarLegacy('primary', 500) // 'var(--primary-9)'
 */
export function getSemanticColorVarLegacy(
  color: SemanticColor,
  shade: TailwindShade,
): string {
  const radixStep = TAILWIND_TO_RADIX_MAP[shade];
  return getSemanticColorVar(color, radixStep);
}

/**
 * Radix step usage guide:
 *
 * Steps 1-2:  App/component backgrounds
 * Steps 3-5:  Interactive component backgrounds (hover: 4, active: 5)
 * Steps 6-8:  Borders and separators
 * Steps 9-10: Solid backgrounds (buttons, badges)
 * Steps 11-12: High-contrast text
 */
export const RADIX_STEP_USAGE = {
  background: [1, 2] as const,
  interactive: [3, 4, 5] as const,
  border: [6, 7, 8] as const,
  solid: [9, 10] as const,
  text: [11, 12] as const,
} as const;

/**
 * Paul Tol's qualitative palette for 8+ categories (colorblind-safe).
 * Use for LangGraph node types when pattern overlays aren't feasible.
 *
 * @see https://personal.sron.nl/~pault/
 */
export const PAUL_TOL_QUALITATIVE = [
  "#332288", // dark blue
  "#88CCEE", // light cyan
  "#44AA99", // teal
  "#117733", // dark green
  "#999933", // olive
  "#DDCC77", // sand
  "#CC6677", // rose
  "#882255", // wine
] as const;

/**
 * LangGraph node type color mappings using semantic colors.
 * Each node type has a color (Radix step 9) and a pattern for colorblind accessibility.
 */
export const NODE_TYPE_STYLES = {
  tool: { color: "var(--primary-9)", pattern: "diagonal" },
  llm: { color: "var(--violet-9)", pattern: "dots" },
  conditional: { color: "var(--amber-9)", pattern: "crosshatch" },
  start: { color: "var(--grass-9)", pattern: "horizontal" },
  end: { color: "var(--neutral-9)", pattern: "vertical" },
  human: { color: "var(--sky-9)", pattern: "grid" },
  error: { color: "var(--ruby-9)", pattern: "zigzag" },
  parallel: { color: "var(--orange-9)", pattern: "waves" },
} as const;

export type NodeType = keyof typeof NODE_TYPE_STYLES;
