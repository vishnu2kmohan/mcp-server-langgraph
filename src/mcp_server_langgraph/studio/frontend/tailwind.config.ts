import type { Config } from 'tailwindcss';

/**
 * Tailwind CSS Configuration
 *
 * Unified design system aligned with @mcp-server-langgraph/shared-frontend design tokens.
 * Ensures consistent styling across all Studio frontend components.
 */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Brand colors from shared design-tokens
        brand: {
          primary: '#3b82f6', // Blue-500 (aligned with shared tokens)
          secondary: '#8b5cf6', // Purple-500
          accent: '#10b981', // Emerald-500
        },
        // Primary color scale (Sky blue from shared tokens)
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
        // Status colors - full scales from shared design-tokens
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
        // Node type colors for workflow canvas
        node: {
          tool: '#3b82f6',
          llm: '#8b5cf6',
          conditional: '#f59e0b',
          approval: '#ef4444',
          custom: '#6b7280',
          start: '#10b981',
          end: '#64748b',
        },
        // Semantic surface colors for dark mode
        surface: {
          light: '#f9fafb',
          dark: '#1e293b',
        },
        // Chat UI semantic colors (Sprint 1.3 - scoped to chat, not global)
        // Richer blue (#2563eb) as requested, without modifying global primary/brand
        chat: {
          accent: '#2563eb', // Blue-600 - richer blue for chat interactions
          'accent-hover': '#1d4ed8', // Blue-700 - hover state
          'user-bubble': '#2563eb', // User message background
          'user-bubble-dark': '#1e40af', // User message dark mode
          'ai-bubble': '#f9fafb', // Assistant message background (gray-50)
          'ai-bubble-dark': '#1f2937', // Assistant message dark mode (gray-800)
        },
        // Grafana brand colors for observability integration
        grafana: {
          50: '#fff8f3',
          100: '#ffefe5',
          200: '#ffd9c2',
          300: '#ffbe94',
          400: '#ff9a5c',
          500: '#F46800', // Official Grafana brand orange
          600: '#db5d00',
          700: '#b84e00',
          800: '#944000',
          900: '#763300',
        },
        // AI/Insights semantic colors (purple theme for AI features)
        insight: {
          50: '#faf5ff',
          100: '#f3e8ff',
          200: '#e9d5ff',
          300: '#d8b4fe',
          400: '#c084fc',
          500: '#a855f7', // Main AI insight purple
          600: '#9333ea',
          700: '#7e22ce',
          800: '#6b21a8',
          900: '#581c87',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
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
      // Consistent border radius values
      borderRadius: {
        DEFAULT: '0.375rem', // 6px - Standard
        sm: '0.25rem', // 4px
        md: '0.375rem', // 6px
        lg: '0.5rem', // 8px
        xl: '0.75rem', // 12px
        '2xl': '1rem', // 16px
      },
      // Box shadows from shared tokens
      boxShadow: {
        'soft': '0 2px 8px -2px rgba(0, 0, 0, 0.1)',
        'elevated': '0 4px 12px -4px rgba(0, 0, 0, 0.15)',
        'modal': '0 16px 48px -8px rgba(0, 0, 0, 0.25)',
      },
      // Transition durations
      transitionDuration: {
        fast: '150ms',
        normal: '200ms',
        slow: '300ms',
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
} satisfies Config;
