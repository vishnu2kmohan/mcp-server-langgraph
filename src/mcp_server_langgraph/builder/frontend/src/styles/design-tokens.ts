/**
 * Design Tokens for MCP Server LangGraph
 *
 * Shared design system tokens for consistent UI across:
 * - Visual Workflow Builder
 * - Interactive Playground
 *
 * Based on Tailwind CSS with custom semantic tokens.
 */

// ==============================================================================
// Color Palette
// ==============================================================================

export const colors = {
  // Brand Colors
  brand: {
    primary: '#3b82f6',      // Blue-500
    secondary: '#8b5cf6',    // Purple-500
    accent: '#10b981',       // Emerald-500
  },

  // Semantic Colors
  semantic: {
    success: '#22c55e',      // Green-500
    warning: '#f59e0b',      // Amber-500
    error: '#ef4444',        // Red-500
    info: '#3b82f6',         // Blue-500
  },

  // Node Type Colors (for workflow builder)
  nodes: {
    tool: '#3b82f6',         // Blue
    llm: '#8b5cf6',          // Purple
    conditional: '#f59e0b',  // Orange
    approval: '#ef4444',     // Red
    custom: '#6b7280',       // Gray
    start: '#10b981',        // Emerald
    end: '#64748b',          // Slate
  },

  // Surface Colors
  surface: {
    light: {
      background: '#f9fafb',   // Gray-50
      paper: '#ffffff',         // White
      border: '#e5e7eb',        // Gray-200
      borderHover: '#d1d5db',   // Gray-300
    },
    dark: {
      background: '#111827',   // Gray-900
      paper: '#1f2937',         // Gray-800
      border: '#374151',        // Gray-700
      borderHover: '#4b5563',   // Gray-600
    },
  },

  // Text Colors
  text: {
    light: {
      primary: '#111827',      // Gray-900
      secondary: '#6b7280',    // Gray-500
      muted: '#9ca3af',        // Gray-400
      inverse: '#ffffff',      // White
    },
    dark: {
      primary: '#f9fafb',      // Gray-50
      secondary: '#d1d5db',    // Gray-300
      muted: '#9ca3af',        // Gray-400
      inverse: '#111827',      // Gray-900
    },
  },
} as const;

// ==============================================================================
// Typography
// ==============================================================================

export const typography = {
  fontFamily: {
    sans: ['Inter', 'system-ui', 'sans-serif'],
    mono: ['JetBrains Mono', 'Menlo', 'monospace'],
  },

  fontSize: {
    xs: ['0.75rem', { lineHeight: '1rem' }],
    sm: ['0.875rem', { lineHeight: '1.25rem' }],
    base: ['1rem', { lineHeight: '1.5rem' }],
    lg: ['1.125rem', { lineHeight: '1.75rem' }],
    xl: ['1.25rem', { lineHeight: '1.75rem' }],
    '2xl': ['1.5rem', { lineHeight: '2rem' }],
    '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
  },

  fontWeight: {
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },
} as const;

// ==============================================================================
// Spacing
// ==============================================================================

export const spacing = {
  px: '1px',
  0: '0',
  0.5: '0.125rem',   // 2px
  1: '0.25rem',      // 4px
  1.5: '0.375rem',   // 6px
  2: '0.5rem',       // 8px
  2.5: '0.625rem',   // 10px
  3: '0.75rem',      // 12px
  3.5: '0.875rem',   // 14px
  4: '1rem',         // 16px
  5: '1.25rem',      // 20px
  6: '1.5rem',       // 24px
  7: '1.75rem',      // 28px
  8: '2rem',         // 32px
  9: '2.25rem',      // 36px
  10: '2.5rem',      // 40px
  12: '3rem',        // 48px
  14: '3.5rem',      // 56px
  16: '4rem',        // 64px
} as const;

// ==============================================================================
// Border Radius
// ==============================================================================

export const borderRadius = {
  none: '0',
  sm: '0.125rem',    // 2px
  DEFAULT: '0.25rem', // 4px
  md: '0.375rem',    // 6px
  lg: '0.5rem',      // 8px
  xl: '0.75rem',     // 12px
  '2xl': '1rem',     // 16px
  '3xl': '1.5rem',   // 24px
  full: '9999px',
} as const;

// ==============================================================================
// Shadows
// ==============================================================================

export const shadows = {
  sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  DEFAULT: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
  md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
  lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
  xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
} as const;

// ==============================================================================
// Transitions
// ==============================================================================

export const transitions = {
  duration: {
    fast: '150ms',
    DEFAULT: '200ms',
    slow: '300ms',
    slower: '500ms',
  },

  easing: {
    DEFAULT: 'cubic-bezier(0.4, 0, 0.2, 1)',
    in: 'cubic-bezier(0.4, 0, 1, 1)',
    out: 'cubic-bezier(0, 0, 0.2, 1)',
    inOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
  },
} as const;

// ==============================================================================
// Z-Index Scale
// ==============================================================================

export const zIndex = {
  dropdown: 1000,
  sticky: 1020,
  fixed: 1030,
  modalBackdrop: 1040,
  modal: 1050,
  popover: 1060,
  tooltip: 1070,
  toast: 1080,
} as const;

// ==============================================================================
// Breakpoints (responsive design)
// ==============================================================================

export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const;

// ==============================================================================
// Component-Specific Tokens
// ==============================================================================

export const components = {
  // Button variants
  button: {
    sizes: {
      sm: { padding: '0.5rem 0.75rem', fontSize: '0.875rem' },
      md: { padding: '0.625rem 1rem', fontSize: '1rem' },
      lg: { padding: '0.75rem 1.25rem', fontSize: '1.125rem' },
    },
    variants: {
      primary: {
        bg: colors.brand.primary,
        text: '#ffffff',
        hover: '#2563eb', // Blue-600
      },
      secondary: {
        bg: '#f3f4f6', // Gray-100
        text: '#374151', // Gray-700
        hover: '#e5e7eb', // Gray-200
      },
      danger: {
        bg: colors.semantic.error,
        text: '#ffffff',
        hover: '#dc2626', // Red-600
      },
    },
  },

  // Input fields
  input: {
    borderColor: colors.surface.light.border,
    focusRing: colors.brand.primary,
    placeholder: colors.text.light.muted,
    errorBorder: colors.semantic.error,
  },

  // Cards/Panels
  card: {
    bg: colors.surface.light.paper,
    border: colors.surface.light.border,
    shadow: shadows.md,
    borderRadius: borderRadius.lg,
  },

  // Modal
  modal: {
    backdropBg: 'rgba(0, 0, 0, 0.5)',
    bg: colors.surface.light.paper,
    shadow: shadows.xl,
    borderRadius: borderRadius.xl,
    maxWidth: '28rem', // 448px
  },

  // Toast notifications
  toast: {
    success: { bg: '#dcfce7', text: '#166534', border: '#86efac' },
    error: { bg: '#fee2e2', text: '#991b1b', border: '#fca5a5' },
    warning: { bg: '#fef3c7', text: '#92400e', border: '#fcd34d' },
    info: { bg: '#dbeafe', text: '#1e40af', border: '#93c5fd' },
  },
} as const;

// ==============================================================================
// CSS Custom Properties (for use in CSS)
// ==============================================================================

export const cssVariables = `
  :root {
    /* Brand Colors */
    --color-brand-primary: ${colors.brand.primary};
    --color-brand-secondary: ${colors.brand.secondary};
    --color-brand-accent: ${colors.brand.accent};

    /* Semantic Colors */
    --color-success: ${colors.semantic.success};
    --color-warning: ${colors.semantic.warning};
    --color-error: ${colors.semantic.error};
    --color-info: ${colors.semantic.info};

    /* Surface Colors */
    --color-bg: ${colors.surface.light.background};
    --color-paper: ${colors.surface.light.paper};
    --color-border: ${colors.surface.light.border};

    /* Text Colors */
    --color-text-primary: ${colors.text.light.primary};
    --color-text-secondary: ${colors.text.light.secondary};
    --color-text-muted: ${colors.text.light.muted};

    /* Transitions */
    --transition-fast: ${transitions.duration.fast};
    --transition-default: ${transitions.duration.DEFAULT};
    --transition-easing: ${transitions.easing.DEFAULT};
  }

  .dark {
    --color-bg: ${colors.surface.dark.background};
    --color-paper: ${colors.surface.dark.paper};
    --color-border: ${colors.surface.dark.border};
    --color-text-primary: ${colors.text.dark.primary};
    --color-text-secondary: ${colors.text.dark.secondary};
    --color-text-muted: ${colors.text.dark.muted};
  }
`;

export default {
  colors,
  typography,
  spacing,
  borderRadius,
  shadows,
  transitions,
  zIndex,
  breakpoints,
  components,
  cssVariables,
};
