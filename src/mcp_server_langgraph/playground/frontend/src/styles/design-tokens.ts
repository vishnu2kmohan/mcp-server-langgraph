/**
 * Design Tokens for Interactive Playground
 *
 * Centralized design system constants for consistent styling.
 * These tokens are used alongside Tailwind CSS for precise control.
 */

// =============================================================================
// Color Palette
// =============================================================================

export const colors = {
  // Primary brand colors
  primary: {
    50: '#f0f9ff',
    100: '#e0f2fe',
    200: '#bae6fd',
    300: '#7dd3fc',
    400: '#38bdf8',
    500: '#0ea5e9',
    600: '#0284c7',
    700: '#0369a1',
    800: '#075985',
    900: '#0c4a6e',
    950: '#082f49',
  },

  // Semantic colors
  success: {
    50: '#f0fdf4',
    100: '#dcfce7',
    200: '#bbf7d0',
    300: '#86efac',
    400: '#4ade80',
    500: '#22c55e',
    600: '#16a34a',
    700: '#15803d',
    800: '#166534',
    900: '#14532d',
  },

  warning: {
    50: '#fffbeb',
    100: '#fef3c7',
    200: '#fde68a',
    300: '#fcd34d',
    400: '#fbbf24',
    500: '#f59e0b',
    600: '#d97706',
    700: '#b45309',
    800: '#92400e',
    900: '#78350f',
  },

  error: {
    50: '#fef2f2',
    100: '#fee2e2',
    200: '#fecaca',
    300: '#fca5a5',
    400: '#f87171',
    500: '#ef4444',
    600: '#dc2626',
    700: '#b91c1c',
    800: '#991b1b',
    900: '#7f1d1d',
  },

  // Neutral grays
  gray: {
    50: '#f9fafb',
    100: '#f3f4f6',
    200: '#e5e7eb',
    300: '#d1d5db',
    400: '#9ca3af',
    500: '#6b7280',
    600: '#4b5563',
    700: '#374151',
    800: '#1f2937',
    900: '#111827',
    950: '#030712',
  },

  // Dark mode specific
  dark: {
    bg: '#0f172a',
    surface: '#1e293b',
    surfaceHover: '#334155',
    border: '#334155',
    borderSubtle: '#1e293b',
    text: '#f1f5f9',
    textSecondary: '#94a3b8',
    textMuted: '#64748b',
  },

  // Light mode specific
  light: {
    bg: '#ffffff',
    surface: '#f9fafb',
    surfaceHover: '#f3f4f6',
    border: '#e5e7eb',
    borderSubtle: '#f3f4f6',
    text: '#111827',
    textSecondary: '#4b5563',
    textMuted: '#9ca3af',
  },
} as const;

// =============================================================================
// Typography
// =============================================================================

export const typography = {
  fontFamily: {
    sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'].join(', '),
    mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'].join(', '),
  },

  fontSize: {
    xs: ['0.75rem', { lineHeight: '1rem' }] as const,
    sm: ['0.875rem', { lineHeight: '1.25rem' }] as const,
    base: ['1rem', { lineHeight: '1.5rem' }] as const,
    lg: ['1.125rem', { lineHeight: '1.75rem' }] as const,
    xl: ['1.25rem', { lineHeight: '1.75rem' }] as const,
    '2xl': ['1.5rem', { lineHeight: '2rem' }] as const,
    '3xl': ['1.875rem', { lineHeight: '2.25rem' }] as const,
    '4xl': ['2.25rem', { lineHeight: '2.5rem' }] as const,
  },

  fontWeight: {
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },
} as const;

// =============================================================================
// Spacing
// =============================================================================

export const spacing = {
  0: '0',
  px: '1px',
  0.5: '0.125rem',
  1: '0.25rem',
  1.5: '0.375rem',
  2: '0.5rem',
  2.5: '0.625rem',
  3: '0.75rem',
  3.5: '0.875rem',
  4: '1rem',
  5: '1.25rem',
  6: '1.5rem',
  7: '1.75rem',
  8: '2rem',
  9: '2.25rem',
  10: '2.5rem',
  12: '3rem',
  14: '3.5rem',
  16: '4rem',
  20: '5rem',
  24: '6rem',
  28: '7rem',
  32: '8rem',
  36: '9rem',
  40: '10rem',
  48: '12rem',
  56: '14rem',
  64: '16rem',
  72: '18rem',
  80: '20rem',
  96: '24rem',
} as const;

// =============================================================================
// Shadows
// =============================================================================

export const shadows = {
  sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  DEFAULT: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
  md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
  lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
  xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
  '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
  inner: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
  none: 'none',
} as const;

// =============================================================================
// Border Radius
// =============================================================================

export const borderRadius = {
  none: '0',
  sm: '0.125rem',
  DEFAULT: '0.25rem',
  md: '0.375rem',
  lg: '0.5rem',
  xl: '0.75rem',
  '2xl': '1rem',
  '3xl': '1.5rem',
  full: '9999px',
} as const;

// =============================================================================
// Transitions
// =============================================================================

export const transitions = {
  fast: '150ms cubic-bezier(0.4, 0, 0.2, 1)',
  normal: '200ms cubic-bezier(0.4, 0, 0.2, 1)',
  slow: '300ms cubic-bezier(0.4, 0, 0.2, 1)',
  colors: 'color 150ms, background-color 150ms, border-color 150ms',
  transform: 'transform 150ms cubic-bezier(0.4, 0, 0.2, 1)',
  opacity: 'opacity 150ms cubic-bezier(0.4, 0, 0.2, 1)',
  all: 'all 150ms cubic-bezier(0.4, 0, 0.2, 1)',
} as const;

// =============================================================================
// Z-Index
// =============================================================================

export const zIndex = {
  base: 0,
  dropdown: 10,
  sticky: 20,
  fixed: 30,
  modalBackdrop: 40,
  modal: 50,
  popover: 60,
  tooltip: 70,
  toast: 80,
} as const;

// =============================================================================
// Breakpoints
// =============================================================================

export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const;

// =============================================================================
// Layout
// =============================================================================

export const layout = {
  // Sidebar width
  sidebarWidth: '280px',
  sidebarCollapsedWidth: '64px',

  // Header height
  headerHeight: '64px',

  // Max content width
  maxContentWidth: '1400px',

  // Panel widths
  sessionPanelWidth: '320px',
  observabilityPanelWidth: '400px',
  chatMinWidth: '400px',
} as const;

// =============================================================================
// Component Tokens
// =============================================================================

export const components = {
  // Button variants
  button: {
    primary: {
      bg: colors.primary[600],
      bgHover: colors.primary[700],
      text: '#ffffff',
    },
    secondary: {
      bg: colors.gray[100],
      bgHover: colors.gray[200],
      text: colors.gray[900],
    },
    ghost: {
      bg: 'transparent',
      bgHover: colors.gray[100],
      text: colors.gray[700],
    },
    danger: {
      bg: colors.error[600],
      bgHover: colors.error[700],
      text: '#ffffff',
    },
  },

  // Badge variants
  badge: {
    info: {
      bg: colors.primary[100],
      text: colors.primary[800],
    },
    success: {
      bg: colors.success[100],
      text: colors.success[800],
    },
    warning: {
      bg: colors.warning[100],
      text: colors.warning[800],
    },
    error: {
      bg: colors.error[100],
      text: colors.error[800],
    },
  },

  // Alert severity colors
  alert: {
    critical: colors.error[500],
    high: colors.error[400],
    medium: colors.warning[500],
    low: colors.primary[500],
  },

  // Trace span colors
  trace: {
    llm: colors.primary[500],
    tool: colors.success[500],
    agent: colors.warning[500],
    error: colors.error[500],
  },
} as const;

// =============================================================================
// Export all tokens
// =============================================================================

export const designTokens = {
  colors,
  typography,
  spacing,
  shadows,
  borderRadius,
  transitions,
  zIndex,
  breakpoints,
  layout,
  components,
} as const;

export default designTokens;
