/**
 * Animation Tokens
 *
 * Centralized animation configuration for the Agent Studio design system.
 * Uses Motion (formerly Framer Motion) for complex animations.
 *
 * @see https://motion.dev/
 */

/**
 * Duration tokens (in seconds for Motion, milliseconds for CSS).
 * All values are accessible via CSS custom properties.
 */
export const ANIMATION_DURATION = {
  /** 100ms - Micro-interactions (hover states) */
  instant: 0.1,
  /** 150ms - Button states, quick feedback */
  fast: 0.15,
  /** 200ms - Standard transitions */
  normal: 0.2,
  /** 300ms - Complex animations, modals */
  slow: 0.3,
  /** 500ms - Page transitions, major state changes */
  slower: 0.5,
} as const;

/**
 * Spring physics configurations for Motion.
 * Springs create natural, physics-based animations.
 */
export const ANIMATION_SPRING = {
  /** Snappy, responsive feel - buttons, toggles */
  snappy: { type: "spring" as const, stiffness: 400, damping: 30 },
  /** Smooth, natural feel - most UI elements */
  smooth: { type: "spring" as const, stiffness: 300, damping: 25 },
  /** Gentle, slow settle - large elements, modals */
  gentle: { type: "spring" as const, stiffness: 200, damping: 20 },
  /** Bouncy, playful feel - success states, celebrations */
  bouncy: { type: "spring" as const, stiffness: 400, damping: 10 },
} as const;

/**
 * Easing functions for non-spring animations.
 * Format: [x1, y1, x2, y2] cubic-bezier values.
 */
export const ANIMATION_EASING = {
  /** Decelerate - most common, for entrances */
  easeOut: [0.0, 0.0, 0.2, 1] as const,
  /** Accelerate - for exits */
  easeIn: [0.4, 0.0, 1, 1] as const,
  /** Symmetric - for state changes */
  easeInOut: [0.4, 0.0, 0.2, 1] as const,
  /** Pull back before moving - for special emphasis */
  anticipate: [0.36, 0, 0.66, -0.56] as const,
} as const;

/**
 * Semantic animation presets for common use cases.
 * These can be spread directly onto Motion components.
 */
export const ANIMATION_PRESETS = {
  /** Simple fade in/out */
  fade: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    exit: { opacity: 0 },
    transition: { duration: ANIMATION_DURATION.fast },
  },

  /** Slide up with fade - modals, toasts, dropdowns */
  slideUp: {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: 20 },
    transition: ANIMATION_SPRING.snappy,
  },

  /** Slide down - collapsible content */
  slideDown: {
    initial: { opacity: 0, y: -10 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -10 },
    transition: ANIMATION_SPRING.smooth,
  },

  /** Scale with fade - buttons, cards, popovers */
  scale: {
    initial: { opacity: 0, scale: 0.95 },
    animate: { opacity: 1, scale: 1 },
    exit: { opacity: 0, scale: 0.95 },
    transition: ANIMATION_SPRING.smooth,
  },

  /** Expand/collapse - accordions, expandable sections */
  expand: {
    initial: { height: 0, opacity: 0 },
    animate: { height: "auto", opacity: 1 },
    exit: { height: 0, opacity: 0 },
    transition: { duration: ANIMATION_DURATION.normal },
  },

  /** Slide in from right - side panels, drawers */
  slideInRight: {
    initial: { opacity: 0, x: 20 },
    animate: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: 20 },
    transition: ANIMATION_SPRING.smooth,
  },

  /** Slide in from left - back navigation */
  slideInLeft: {
    initial: { opacity: 0, x: -20 },
    animate: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: -20 },
    transition: ANIMATION_SPRING.smooth,
  },
} as const;

/**
 * Reduced motion variants - used when user prefers reduced motion.
 * Falls back to opacity-only transitions.
 */
export const REDUCED_MOTION_PRESET = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
  transition: { duration: ANIMATION_DURATION.fast },
} as const;

/**
 * CSS custom properties for animation tokens.
 * Use in Tailwind config or global CSS.
 */
export const ANIMATION_CSS_VARS = {
  "--duration-instant": `${ANIMATION_DURATION.instant * 1000}ms`,
  "--duration-fast": `${ANIMATION_DURATION.fast * 1000}ms`,
  "--duration-normal": `${ANIMATION_DURATION.normal * 1000}ms`,
  "--duration-slow": `${ANIMATION_DURATION.slow * 1000}ms`,
  "--duration-slower": `${ANIMATION_DURATION.slower * 1000}ms`,
  "--ease-out": `cubic-bezier(${ANIMATION_EASING.easeOut.join(", ")})`,
  "--ease-in": `cubic-bezier(${ANIMATION_EASING.easeIn.join(", ")})`,
  "--ease-in-out": `cubic-bezier(${ANIMATION_EASING.easeInOut.join(", ")})`,
} as const;

export type AnimationPreset = keyof typeof ANIMATION_PRESETS;
export type AnimationDuration = keyof typeof ANIMATION_DURATION;
export type AnimationSpring = keyof typeof ANIMATION_SPRING;
export type AnimationEasing = keyof typeof ANIMATION_EASING;
