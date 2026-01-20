import type { Config } from 'tailwindcss';

/**
 * Tailwind CSS Configuration
 *
 * Unified design system using Radix Colors for the Agent Studio frontend.
 * Uses CSS custom properties for theme-aware colors.
 *
 * Color Scale:
 * - Radix uses 1-12 scale (1 = lightest, 12 = darkest)
 * - Step 9 is the primary action color (buttons, links)
 * - Steps 11-12 are for high-contrast text
 *
 * @see https://www.radix-ui.com/colors
 */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        /* ==========================================================================
         * Radix 1-12 Scale Colors (Theme-Aware via CSS Variables)
         * These are the PRIMARY color system. Use these for new code.
         * ========================================================================== */

        // Primary accent (switches between Violet/Teal based on theme)
        primary: {
          1: 'var(--primary-1)',
          2: 'var(--primary-2)',
          3: 'var(--primary-3)',
          4: 'var(--primary-4)',
          5: 'var(--primary-5)',
          6: 'var(--primary-6)',
          7: 'var(--primary-7)',
          8: 'var(--primary-8)',
          9: 'var(--primary-9)',
          10: 'var(--primary-10)',
          11: 'var(--primary-11)',
          12: 'var(--primary-12)',
          // Legacy 50-950 aliases for backward compatibility
          50: 'var(--primary-1)',
          100: 'var(--primary-2)',
          200: 'var(--primary-3)',
          300: 'var(--primary-4)',
          400: 'var(--primary-5)',
          500: 'var(--primary-9)',
          600: 'var(--primary-10)',
          700: 'var(--primary-11)',
          800: 'var(--primary-11)',
          900: 'var(--primary-12)',
          950: 'var(--primary-12)',
        },

        // Neutral (Slate for 'sage' themes, Olive for 'olive' themes)
        neutral: {
          1: 'var(--neutral-1)',
          2: 'var(--neutral-2)',
          3: 'var(--neutral-3)',
          4: 'var(--neutral-4)',
          5: 'var(--neutral-5)',
          6: 'var(--neutral-6)',
          7: 'var(--neutral-7)',
          8: 'var(--neutral-8)',
          9: 'var(--neutral-9)',
          10: 'var(--neutral-10)',
          11: 'var(--neutral-11)',
          12: 'var(--neutral-12)',
          // Legacy 50-950 aliases
          50: 'var(--neutral-1)',
          100: 'var(--neutral-2)',
          200: 'var(--neutral-3)',
          300: 'var(--neutral-4)',
          400: 'var(--neutral-5)',
          500: 'var(--neutral-9)',
          600: 'var(--neutral-10)',
          700: 'var(--neutral-11)',
          800: 'var(--neutral-11)',
          900: 'var(--neutral-12)',
          950: 'var(--neutral-12)',
        },

        // Success (Grass)
        success: {
          1: 'var(--success-1)',
          2: 'var(--success-2)',
          3: 'var(--success-3)',
          4: 'var(--success-4)',
          5: 'var(--success-5)',
          6: 'var(--success-6)',
          7: 'var(--success-7)',
          8: 'var(--success-8)',
          9: 'var(--success-9)',
          10: 'var(--success-10)',
          11: 'var(--success-11)',
          12: 'var(--success-12)',
          // Legacy aliases
          50: 'var(--success-1)',
          100: 'var(--success-2)',
          200: 'var(--success-3)',
          300: 'var(--success-4)',
          400: 'var(--success-5)',
          500: 'var(--success-9)',
          600: 'var(--success-10)',
          700: 'var(--success-11)',
          800: 'var(--success-11)',
          900: 'var(--success-12)',
        },

        // Warning (Amber)
        warning: {
          1: 'var(--warning-1)',
          2: 'var(--warning-2)',
          3: 'var(--warning-3)',
          4: 'var(--warning-4)',
          5: 'var(--warning-5)',
          6: 'var(--warning-6)',
          7: 'var(--warning-7)',
          8: 'var(--warning-8)',
          9: 'var(--warning-9)',
          10: 'var(--warning-10)',
          11: 'var(--warning-11)',
          12: 'var(--warning-12)',
          // Legacy aliases
          50: 'var(--warning-1)',
          100: 'var(--warning-2)',
          200: 'var(--warning-3)',
          300: 'var(--warning-4)',
          400: 'var(--warning-5)',
          500: 'var(--warning-9)',
          600: 'var(--warning-10)',
          700: 'var(--warning-11)',
          800: 'var(--warning-11)',
          900: 'var(--warning-12)',
        },

        // Error (Ruby)
        error: {
          1: 'var(--error-1)',
          2: 'var(--error-2)',
          3: 'var(--error-3)',
          4: 'var(--error-4)',
          5: 'var(--error-5)',
          6: 'var(--error-6)',
          7: 'var(--error-7)',
          8: 'var(--error-8)',
          9: 'var(--error-9)',
          10: 'var(--error-10)',
          11: 'var(--error-11)',
          12: 'var(--error-12)',
          // Legacy aliases
          50: 'var(--error-1)',
          100: 'var(--error-2)',
          200: 'var(--error-3)',
          300: 'var(--error-4)',
          400: 'var(--error-5)',
          500: 'var(--error-9)',
          600: 'var(--error-10)',
          700: 'var(--error-11)',
          800: 'var(--error-11)',
          900: 'var(--error-12)',
        },

        // Info (Sky)
        info: {
          1: 'var(--info-1)',
          2: 'var(--info-2)',
          3: 'var(--info-3)',
          4: 'var(--info-4)',
          5: 'var(--info-5)',
          6: 'var(--info-6)',
          7: 'var(--info-7)',
          8: 'var(--info-8)',
          9: 'var(--info-9)',
          10: 'var(--info-10)',
          11: 'var(--info-11)',
          12: 'var(--info-12)',
          // Legacy aliases
          50: 'var(--info-1)',
          100: 'var(--info-2)',
          200: 'var(--info-3)',
          300: 'var(--info-4)',
          400: 'var(--info-5)',
          500: 'var(--info-9)',
          600: 'var(--info-10)',
          700: 'var(--info-11)',
          800: 'var(--info-11)',
          900: 'var(--info-12)',
          950: 'var(--info-12)',
        },

        // Insight/AI (Violet)
        insight: {
          1: 'var(--insight-1)',
          2: 'var(--insight-2)',
          3: 'var(--insight-3)',
          4: 'var(--insight-4)',
          5: 'var(--insight-5)',
          6: 'var(--insight-6)',
          7: 'var(--insight-7)',
          8: 'var(--insight-8)',
          9: 'var(--insight-9)',
          10: 'var(--insight-10)',
          11: 'var(--insight-11)',
          12: 'var(--insight-12)',
          // Legacy aliases
          50: 'var(--insight-1)',
          100: 'var(--insight-2)',
          200: 'var(--insight-3)',
          300: 'var(--insight-4)',
          400: 'var(--insight-5)',
          500: 'var(--insight-9)',
          600: 'var(--insight-10)',
          700: 'var(--insight-11)',
          800: 'var(--insight-11)',
          900: 'var(--insight-12)',
          950: 'var(--insight-12)',
        },

        // Grafana brand (Orange)
        grafana: {
          1: 'var(--grafana-1)',
          2: 'var(--grafana-2)',
          3: 'var(--grafana-3)',
          4: 'var(--grafana-4)',
          5: 'var(--grafana-5)',
          6: 'var(--grafana-6)',
          7: 'var(--grafana-7)',
          8: 'var(--grafana-8)',
          9: 'var(--grafana-9)',
          10: 'var(--grafana-10)',
          11: 'var(--grafana-11)',
          12: 'var(--grafana-12)',
          // Legacy aliases
          50: 'var(--grafana-1)',
          100: 'var(--grafana-2)',
          200: 'var(--grafana-3)',
          300: 'var(--grafana-4)',
          400: 'var(--grafana-5)',
          500: 'var(--grafana-9)',
          600: 'var(--grafana-10)',
          700: 'var(--grafana-11)',
          800: 'var(--grafana-11)',
          900: 'var(--grafana-12)',
        },

        /* ==========================================================================
         * Direct Radix Color Access (for components that need specific colors)
         * ========================================================================== */
        violet: {
          1: 'var(--violet-1)', 2: 'var(--violet-2)', 3: 'var(--violet-3)',
          4: 'var(--violet-4)', 5: 'var(--violet-5)', 6: 'var(--violet-6)',
          7: 'var(--violet-7)', 8: 'var(--violet-8)', 9: 'var(--violet-9)',
          10: 'var(--violet-10)', 11: 'var(--violet-11)', 12: 'var(--violet-12)',
        },
        teal: {
          1: 'var(--teal-1)', 2: 'var(--teal-2)', 3: 'var(--teal-3)',
          4: 'var(--teal-4)', 5: 'var(--teal-5)', 6: 'var(--teal-6)',
          7: 'var(--teal-7)', 8: 'var(--teal-8)', 9: 'var(--teal-9)',
          10: 'var(--teal-10)', 11: 'var(--teal-11)', 12: 'var(--teal-12)',
        },
        sage: {
          1: 'var(--sage-1)', 2: 'var(--sage-2)', 3: 'var(--sage-3)',
          4: 'var(--sage-4)', 5: 'var(--sage-5)', 6: 'var(--sage-6)',
          7: 'var(--sage-7)', 8: 'var(--sage-8)', 9: 'var(--sage-9)',
          10: 'var(--sage-10)', 11: 'var(--sage-11)', 12: 'var(--sage-12)',
        },
        olive: {
          1: 'var(--olive-1)', 2: 'var(--olive-2)', 3: 'var(--olive-3)',
          4: 'var(--olive-4)', 5: 'var(--olive-5)', 6: 'var(--olive-6)',
          7: 'var(--olive-7)', 8: 'var(--olive-8)', 9: 'var(--olive-9)',
          10: 'var(--olive-10)', 11: 'var(--olive-11)', 12: 'var(--olive-12)',
        },
        grass: {
          1: 'var(--grass-1)', 2: 'var(--grass-2)', 3: 'var(--grass-3)',
          4: 'var(--grass-4)', 5: 'var(--grass-5)', 6: 'var(--grass-6)',
          7: 'var(--grass-7)', 8: 'var(--grass-8)', 9: 'var(--grass-9)',
          10: 'var(--grass-10)', 11: 'var(--grass-11)', 12: 'var(--grass-12)',
        },
        amber: {
          1: 'var(--amber-1)', 2: 'var(--amber-2)', 3: 'var(--amber-3)',
          4: 'var(--amber-4)', 5: 'var(--amber-5)', 6: 'var(--amber-6)',
          7: 'var(--amber-7)', 8: 'var(--amber-8)', 9: 'var(--amber-9)',
          10: 'var(--amber-10)', 11: 'var(--amber-11)', 12: 'var(--amber-12)',
        },
        ruby: {
          1: 'var(--ruby-1)', 2: 'var(--ruby-2)', 3: 'var(--ruby-3)',
          4: 'var(--ruby-4)', 5: 'var(--ruby-5)', 6: 'var(--ruby-6)',
          7: 'var(--ruby-7)', 8: 'var(--ruby-8)', 9: 'var(--ruby-9)',
          10: 'var(--ruby-10)', 11: 'var(--ruby-11)', 12: 'var(--ruby-12)',
        },
        sky: {
          1: 'var(--sky-1)', 2: 'var(--sky-2)', 3: 'var(--sky-3)',
          4: 'var(--sky-4)', 5: 'var(--sky-5)', 6: 'var(--sky-6)',
          7: 'var(--sky-7)', 8: 'var(--sky-8)', 9: 'var(--sky-9)',
          10: 'var(--sky-10)', 11: 'var(--sky-11)', 12: 'var(--sky-12)',
        },
        orange: {
          1: 'var(--orange-1)', 2: 'var(--orange-2)', 3: 'var(--orange-3)',
          4: 'var(--orange-4)', 5: 'var(--orange-5)', 6: 'var(--orange-6)',
          7: 'var(--orange-7)', 8: 'var(--orange-8)', 9: 'var(--orange-9)',
          10: 'var(--orange-10)', 11: 'var(--orange-11)', 12: 'var(--orange-12)',
        },

        /* ==========================================================================
         * Legacy/Fixed Colors (for backward compatibility)
         * ========================================================================== */

        // Brand colors (use primary-9 instead for new code)
        brand: {
          primary: 'var(--primary-9)',
          secondary: 'var(--insight-9)',
          accent: 'var(--success-9)',
        },

        // Node type colors for workflow canvas
        node: {
          tool: 'var(--primary-9)',
          llm: 'var(--violet-9)',
          conditional: 'var(--amber-9)',
          approval: 'var(--ruby-9)',
          custom: 'var(--neutral-9)',
          start: 'var(--grass-9)',
          end: 'var(--neutral-8)',
        },

        // Semantic surface colors
        surface: {
          light: 'var(--neutral-1)',
          dark: 'var(--neutral-12)',
        },

        // Chat UI semantic colors
        chat: {
          accent: 'var(--primary-9)',
          'accent-hover': 'var(--primary-10)',
          'user-bubble': 'var(--primary-9)',
          'user-bubble-dark': 'var(--primary-10)',
          'ai-bubble': 'var(--neutral-2)',
          'ai-bubble-dark': 'var(--neutral-3)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      // Typography scale (uses CSS variables for consistency)
      fontSize: {
        xs: 'var(--font-size-xs)',
        sm: 'var(--font-size-sm)',
        base: 'var(--font-size-base)',
        lg: 'var(--font-size-lg)',
        xl: 'var(--font-size-xl)',
        '2xl': 'var(--font-size-2xl)',
        '3xl': 'var(--font-size-3xl)',
        '4xl': 'var(--font-size-4xl)',
      },
      fontWeight: {
        normal: 'var(--font-weight-normal)',
        medium: 'var(--font-weight-medium)',
        semibold: 'var(--font-weight-semibold)',
        bold: 'var(--font-weight-bold)',
      },
      lineHeight: {
        none: 'var(--line-height-none)',
        tight: 'var(--line-height-tight)',
        snug: 'var(--line-height-snug)',
        normal: 'var(--line-height-normal)',
        relaxed: 'var(--line-height-relaxed)',
        loose: 'var(--line-height-loose)',
      },
      letterSpacing: {
        tighter: 'var(--letter-spacing-tighter)',
        tight: 'var(--letter-spacing-tight)',
        normal: 'var(--letter-spacing-normal)',
        wide: 'var(--letter-spacing-wide)',
        wider: 'var(--letter-spacing-wider)',
      },
      // Spacing scale (uses CSS variables for consistency)
      spacing: {
        0: 'var(--spacing-0)',
        px: 'var(--spacing-px)',
        0.5: 'var(--spacing-0-5)',
        1: 'var(--spacing-1)',
        1.5: 'var(--spacing-1-5)',
        2: 'var(--spacing-2)',
        2.5: 'var(--spacing-2-5)',
        3: 'var(--spacing-3)',
        3.5: 'var(--spacing-3-5)',
        4: 'var(--spacing-4)',
        5: 'var(--spacing-5)',
        6: 'var(--spacing-6)',
        7: 'var(--spacing-7)',
        8: 'var(--spacing-8)',
        9: 'var(--spacing-9)',
        10: 'var(--spacing-10)',
        12: 'var(--spacing-12)',
        14: 'var(--spacing-14)',
        16: 'var(--spacing-16)',
        20: 'var(--spacing-20)',
        24: 'var(--spacing-24)',
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'fade-out': 'fadeOut 0.2s ease-in',
        'slide-in': 'slideIn 0.2s ease-out',
        'slide-out': 'slideOut 0.2s ease-in',
        'scale-in': 'scaleIn 0.15s ease-out',
        'pulse-subtle': 'pulseSubtle 2s ease-in-out infinite',
        'spin-slow': 'spin 3s linear infinite',
        // Chat UI animations (Sprint 1.1)
        'shimmer': 'shimmer 2s infinite', // Streaming indicator shimmer
        'message-in': 'slideInFromBottom 0.2s ease-out', // Message entry animation
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeOut: {
          '0%': { opacity: '1' },
          '100%': { opacity: '0' },
        },
        slideIn: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideOut: {
          '0%': { transform: 'translateY(0)', opacity: '1' },
          '100%': { transform: 'translateY(-10px)', opacity: '0' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        pulseSubtle: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.8' },
        },
        // Chat UI keyframes (Sprint 1.1)
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        slideInFromBottom: {
          '0%': { transform: 'translateY(8px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
      // Border radius (uses CSS variables for consistency)
      borderRadius: {
        none: 'var(--radius-none)',
        sm: 'var(--radius-sm)',
        DEFAULT: 'var(--radius-DEFAULT)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        xl: 'var(--radius-xl)',
        '2xl': 'var(--radius-2xl)',
        '3xl': 'var(--radius-3xl)',
        full: 'var(--radius-full)',
      },
      // Box shadows (uses CSS variables for consistency)
      boxShadow: {
        none: 'var(--shadow-none)',
        sm: 'var(--shadow-sm)',
        DEFAULT: 'var(--shadow-md)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
        xl: 'var(--shadow-xl)',
        '2xl': 'var(--shadow-2xl)',
        inner: 'var(--shadow-inner)',
        // Semantic shadow aliases
        soft: 'var(--shadow-soft)',
        elevated: 'var(--shadow-elevated)',
        modal: 'var(--shadow-modal)',
      },
      // Transition durations (uses CSS variables for consistency)
      transitionDuration: {
        instant: 'var(--duration-instant)',
        fast: 'var(--duration-fast)',
        DEFAULT: 'var(--duration-normal)',
        normal: 'var(--duration-normal)',
        slow: 'var(--duration-slow)',
        slower: 'var(--duration-slower)',
      },
      // Easing functions (uses CSS variables for consistency)
      transitionTimingFunction: {
        DEFAULT: 'var(--ease-in-out)',
        in: 'var(--ease-in)',
        out: 'var(--ease-out)',
        'in-out': 'var(--ease-in-out)',
        anticipate: 'var(--ease-anticipate)',
      },
      // Animation delay values (for staggered animations)
      // Usage: animation-delay-150, animation-delay-300, etc.
      // Note: Requires plugin below to generate utilities
      animationDelay: {
        '0': '0ms',
        '75': '75ms',
        '150': '150ms',
        '300': '300ms',
        '500': '500ms',
        '700': '700ms',
        '1000': '1000ms',
      },
      // Z-index scale (uses CSS variables for consistency)
      zIndex: {
        auto: 'auto',
        0: '0',
        10: '10',
        20: '20',
        30: '30',
        40: '40',
        50: '50',
        // Semantic z-index values
        tooltip: 'var(--z-tooltip)',
        dropdown: 'var(--z-dropdown)',
        panel: 'var(--z-panel)',
        'command-palette': 'var(--z-command-palette)',
        modal: 'var(--z-modal)',
        notification: 'var(--z-notification)',
        'system-alert': 'var(--z-system-alert)',
        toast: 'var(--z-toast)',
      },
      // Semantic max-height tokens (replaces arbitrary [90vh] patterns)
      maxHeight: {
        modal: '90vh',
        panel: '80vh',
        drawer: '70vh',
        'dropdown-lg': '60vh',
      },
      // Semantic min-height tokens
      minHeight: {
        'input-rich': '100px',
        canvas: '300px',
        touch: '44px', // WCAG 2.5.8 touch target
        'touch-sm': '32px', // Desktop pointer target
      },
      // Semantic width tokens (replaces arbitrary [600px] patterns)
      width: {
        message: '70%',
        'dialog-sm': '300px',
        'dialog-md': '500px',
        'dialog-lg': '600px',
        'dialog-xl': '800px',
      },
      // Semantic max-width tokens
      maxWidth: {
        message: '70%',
        'chat-bubble': '80%',
      },
      // Semantic min-width tokens
      minWidth: {
        'dialog-sm': '300px',
        'dialog-md': '500px',
        'button-icon': '32px',
        'touch-target': '44px',
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    // Animation delay plugin - generates animation-delay-* utilities
    function({ addUtilities, theme }: { addUtilities: (utilities: Record<string, Record<string, string>>) => void; theme: (key: string) => Record<string, string> }) {
      const delays = theme('animationDelay') as Record<string, string>;
      const utilities = Object.entries(delays).reduce<Record<string, Record<string, string>>>((acc, [key, value]) => {
        acc[`.animation-delay-${key}`] = { 'animation-delay': value };
        return acc;
      }, {});
      addUtilities(utilities);
    },
  ],
} satisfies Config;
