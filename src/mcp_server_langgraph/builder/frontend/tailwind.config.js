/** @type {import('tailwindcss').Config} */
import { colors, typography, spacing, borderRadius, shadows, breakpoints } from './src/styles/design-tokens';

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      // Brand and semantic colors
      colors: {
        brand: colors.brand,
        semantic: colors.semantic,
        node: colors.nodes,
        surface: {
          light: colors.surface.light,
          dark: colors.surface.dark,
        },
      },
      // Typography
      fontFamily: {
        sans: typography.fontFamily.sans,
        mono: typography.fontFamily.mono,
      },
      // Spacing (extended)
      spacing: {
        '0.5': spacing['0.5'],
        '1.5': spacing['1.5'],
        '2.5': spacing['2.5'],
        '3.5': spacing['3.5'],
        '14': spacing['14'],
      },
      // Border radius
      borderRadius: {
        DEFAULT: borderRadius.DEFAULT,
        'xl': borderRadius.xl,
        '2xl': borderRadius['2xl'],
        '3xl': borderRadius['3xl'],
      },
      // Box shadows
      boxShadow: {
        DEFAULT: shadows.DEFAULT,
        sm: shadows.sm,
        md: shadows.md,
        lg: shadows.lg,
        xl: shadows.xl,
      },
      // Screen breakpoints
      screens: breakpoints,
      // Custom transitions
      transitionDuration: {
        fast: '150ms',
        DEFAULT: '200ms',
        slow: '300ms',
        slower: '500ms',
      },
      transitionTimingFunction: {
        DEFAULT: 'cubic-bezier(0.4, 0, 0.2, 1)',
        'in': 'cubic-bezier(0.4, 0, 1, 1)',
        'out': 'cubic-bezier(0, 0, 0.2, 1)',
        'in-out': 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
    },
  },
  plugins: [],
}
