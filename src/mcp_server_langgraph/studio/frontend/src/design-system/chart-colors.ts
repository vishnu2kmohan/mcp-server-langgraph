/**
 * Chart Color Constants
 *
 * Centralized color palettes for data visualization.
 * Uses ColorBrewer palettes with Vega-Lite integration.
 *
 * @see https://colorbrewer2.org/
 * @see https://vega.github.io/vega-lite/docs/scale.html#scheme
 */

/**
 * ColorBrewer palette configurations for Vega-Lite.
 * Set2 is preferred for categorical data (colorblind-safe up to 3 categories).
 */
export const CHART_PALETTES = {
  /** Set2 - Default categorical, colorblind-safe up to 3 categories */
  categorical: {
    scheme: 'set2',
    colors: [
      '#66c2a5', // teal
      '#fc8d62', // salmon
      '#8da0cb', // blue-gray
      '#e78ac3', // pink
      '#a6d854', // lime
      '#ffd92f', // yellow
      '#e5c494', // tan
      '#b3b3b3', // gray
    ],
  },

  /** Dark2 - Higher contrast categorical */
  categoricalDark: {
    scheme: 'dark2',
    colors: [
      '#1b9e77', // teal
      '#d95f02', // orange
      '#7570b3', // purple
      '#e7298a', // magenta
      '#66a61e', // green
      '#e6ab02', // gold
      '#a6761d', // brown
      '#666666', // gray
    ],
  },

  /** Sequential palettes - for ordered/continuous data */
  sequential: {
    blue: { scheme: 'blues' },
    green: { scheme: 'greens' },
    purple: { scheme: 'purples' },
    orange: { scheme: 'oranges' },
    gray: { scheme: 'greys' },
    /** Viridis - perceptually uniform, colorblind-safe */
    viridis: { scheme: 'viridis' },
  },

  /** Diverging palettes - for data with meaningful midpoint */
  diverging: {
    /** Blue to Red - default diverging */
    blueRed: { scheme: 'rdbu' },
    /** Brown to Blue-Green - colorblind-safe */
    brownTeal: { scheme: 'brbg' },
    /** Purple to Green */
    purpleGreen: { scheme: 'prgn' },
  },

  /** Heatmap palettes */
  heatmap: {
    viridis: { scheme: 'viridis' },
    inferno: { scheme: 'inferno' },
    magma: { scheme: 'magma' },
    plasma: { scheme: 'plasma' },
  },
} as const;

/**
 * Paul Tol's qualitative palette for 8+ categories.
 * Designed specifically for colorblind accessibility.
 *
 * @see https://personal.sron.nl/~pault/
 */
export const PAUL_TOL_PALETTE = [
  '#332288', // indigo
  '#88CCEE', // cyan
  '#44AA99', // teal
  '#117733', // green
  '#999933', // olive
  '#DDCC77', // sand
  '#CC6677', // rose
  '#882255', // wine
  '#AA4499', // purple
] as const;

/**
 * LangGraph node type colors with patterns for accessibility.
 * Uses semantic color variables + fallback patterns.
 */
export const NODE_TYPE_COLORS = {
  tool: {
    fill: 'var(--primary-9)',
    stroke: 'var(--primary-11)',
    pattern: 'diagonal-stripe',
    label: 'Tool',
  },
  llm: {
    fill: 'var(--violet-9)',
    stroke: 'var(--violet-11)',
    pattern: 'dots',
    label: 'LLM',
  },
  conditional: {
    fill: 'var(--amber-9)',
    stroke: 'var(--amber-11)',
    pattern: 'crosshatch',
    label: 'Conditional',
  },
  start: {
    fill: 'var(--grass-9)',
    stroke: 'var(--grass-11)',
    pattern: 'horizontal-lines',
    label: 'Start',
  },
  end: {
    fill: 'var(--neutral-9)',
    stroke: 'var(--neutral-11)',
    pattern: 'vertical-lines',
    label: 'End',
  },
  human: {
    fill: 'var(--sky-9)',
    stroke: 'var(--sky-11)',
    pattern: 'grid',
    label: 'Human',
  },
  error: {
    fill: 'var(--ruby-9)',
    stroke: 'var(--ruby-11)',
    pattern: 'zigzag',
    label: 'Error',
  },
  parallel: {
    fill: 'var(--orange-9)',
    stroke: 'var(--orange-11)',
    pattern: 'waves',
    label: 'Parallel',
  },
} as const;

/**
 * Vega-Lite theme configuration for Agent Studio.
 * Apply this config to all Vega-Lite charts for consistent styling.
 */
export const VEGA_LITE_THEME = {
  config: {
    background: 'transparent',

    // Default color ranges
    range: {
      category: { scheme: 'set2' },
      diverging: { scheme: 'brbg' },
      heatmap: { scheme: 'viridis' },
      ordinal: { scheme: 'blues' },
      ramp: { scheme: 'blues' },
    },

    // Axis styling (uses CSS variables)
    axis: {
      labelColor: 'var(--neutral-11)',
      titleColor: 'var(--neutral-12)',
      gridColor: 'var(--neutral-6)',
      domainColor: 'var(--neutral-8)',
      tickColor: 'var(--neutral-8)',
      labelFont: 'Inter, system-ui, sans-serif',
      titleFont: 'Inter, system-ui, sans-serif',
      labelFontSize: 11,
      titleFontSize: 12,
    },

    // Legend styling
    legend: {
      labelColor: 'var(--neutral-11)',
      titleColor: 'var(--neutral-12)',
      labelFont: 'Inter, system-ui, sans-serif',
      titleFont: 'Inter, system-ui, sans-serif',
      labelFontSize: 11,
      titleFontSize: 12,
    },

    // Title styling
    title: {
      color: 'var(--neutral-12)',
      font: 'Inter, system-ui, sans-serif',
      fontSize: 14,
      fontWeight: 500,
    },

    // Mark defaults
    mark: {
      tooltip: true,
    },

    // Bar chart defaults
    bar: {
      cornerRadiusEnd: 2,
    },

    // Line chart defaults
    line: {
      strokeWidth: 2,
    },

    // Point defaults
    point: {
      size: 60,
    },
  },
} as const;

/**
 * Get chart colors for high contrast mode.
 * Adds pattern overlays for colorblind accessibility.
 */
export function getHighContrastChartConfig() {
  return {
    ...VEGA_LITE_THEME.config,
    range: {
      category: PAUL_TOL_PALETTE,
    },
  };
}

export type NodeType = keyof typeof NODE_TYPE_COLORS;
export type SequentialScheme = keyof typeof CHART_PALETTES.sequential;
export type DivergingScheme = keyof typeof CHART_PALETTES.diverging;
