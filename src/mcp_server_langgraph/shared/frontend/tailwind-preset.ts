/**
 * MCP Server LangGraph - Shared Tailwind Preset (ESM/TypeScript)
 *
 * ESM format for TypeScript imports.
 * Imports directly from design-tokens for type safety and single source of truth.
 *
 * @see tailwind-preset.cjs for CommonJS/Tailwind CLI version
 */

import { colors, typography, borderRadius, shadows, zIndex } from './src/styles/design-tokens';
import type { Config } from 'tailwindcss';

export const sharedPreset: Partial<Config> = {
  theme: {
    extend: {
      colors: {
        brand: colors.brand,
        primary: colors.primary,
        success: colors.success,
        warning: colors.warning,
        error: colors.error,
        nodes: colors.nodes,
      },
      fontFamily: {
        sans: typography.fontFamily.sans.split(', '),
        mono: typography.fontFamily.mono.split(', '),
      },
      borderRadius: {
        none: borderRadius.none,
        sm: borderRadius.sm,
        DEFAULT: borderRadius.DEFAULT,
        md: borderRadius.md,
        lg: borderRadius.lg,
        xl: borderRadius.xl,
        '2xl': borderRadius['2xl'],
        '3xl': borderRadius['3xl'],
        full: borderRadius.full,
      },
      boxShadow: {
        sm: shadows.sm,
        DEFAULT: shadows.DEFAULT,
        md: shadows.md,
        lg: shadows.lg,
        xl: shadows.xl,
        '2xl': shadows['2xl'],
        inner: shadows.inner,
        none: shadows.none,
      },
      zIndex: {
        dropdown: String(zIndex.dropdown),
        sticky: String(zIndex.sticky),
        fixed: String(zIndex.fixed),
        modalBackdrop: String(zIndex.modalBackdrop),
        modal: String(zIndex.modal),
        popover: String(zIndex.popover),
        tooltip: String(zIndex.tooltip),
        toast: String(zIndex.toast),
      },
    },
  },
};

export default sharedPreset;
