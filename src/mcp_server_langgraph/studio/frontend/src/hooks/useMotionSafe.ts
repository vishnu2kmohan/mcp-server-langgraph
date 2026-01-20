/**
 * useMotionSafe Hook
 *
 * Returns motion-safe animation props that respect the user's
 * reduced motion preference (prefers-reduced-motion).
 *
 * When reduced motion is enabled, falls back to opacity-only
 * animations with faster transitions for a better accessibility experience.
 *
 * @example
 * // Basic usage
 * function Modal({ children }) {
 *   const motionProps = useMotionSafe({
 *     initial: { opacity: 0, y: 20 },
 *     animate: { opacity: 1, y: 0 },
 *     exit: { opacity: 0, y: 20 },
 *     transition: { type: 'spring', stiffness: 400 }
 *   });
 *
 *   return <motion.div {...motionProps}>{children}</motion.div>;
 * }
 *
 * @example
 * // With custom reduced motion overrides
 * const motionProps = useMotionSafe(
 *   { initial: { opacity: 0, scale: 0.9 }, animate: { opacity: 1, scale: 1 } },
 *   { transition: { duration: 0.2 } }
 * );
 */

import { useReducedMotion, type Variants } from "motion/react";

// =============================================================================
// Types
// =============================================================================

interface MotionProps {
  initial?: Record<string, unknown>;
  animate?: Record<string, unknown>;
  exit?: Record<string, unknown>;
  transition?: Record<string, unknown>;
  [key: string]: unknown;
}

// =============================================================================
// Default Reduced Motion Props
// =============================================================================

const REDUCED_MOTION_DEFAULTS: MotionProps = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
  transition: { duration: 0.15 },
};

// =============================================================================
// Hook
// =============================================================================

/**
 * Returns motion-safe animation props.
 * Falls back to opacity-only animations when reduced motion is enabled.
 *
 * @param fullMotion - Full animation props to use when motion is allowed
 * @param reducedMotion - Optional custom props to use when reduced motion is preferred
 * @returns Motion props appropriate for the user's preferences
 */
export function useMotionSafe<T extends MotionProps>(
  fullMotion: T,
  reducedMotion?: Partial<T>
): T {
  const prefersReducedMotion = useReducedMotion();

  if (prefersReducedMotion) {
    return {
      ...fullMotion,
      // Apply reduced motion defaults
      ...REDUCED_MOTION_DEFAULTS,
      // Allow custom overrides
      ...reducedMotion,
    } as T;
  }

  return fullMotion;
}

/**
 * Returns whether reduced motion is preferred.
 * Useful for conditionally disabling animations.
 */
export function usePrefersReducedMotion(): boolean {
  return useReducedMotion() ?? false;
}

/**
 * Returns motion-safe variants.
 * When reduced motion is enabled, returns opacity-only variants.
 *
 * @param variants - Full variants object with all animation states
 * @returns Motion-safe variants appropriate for user's preferences
 *
 * @example
 * const safeVariants = useMotionSafeVariants({
 *   hidden: { opacity: 0, x: -20 },
 *   visible: { opacity: 1, x: 0 },
 *   exit: { opacity: 0, x: 20 },
 * });
 */
export function useMotionSafeVariants(variants: Variants): Variants {
  const prefersReducedMotion = useReducedMotion();

  if (prefersReducedMotion) {
    // Convert variants to opacity-only versions
    const reducedVariants: Variants = {};
    for (const [key, value] of Object.entries(variants)) {
      // Extract only opacity from the variant, or use sensible defaults
      const variantValue = value as Record<string, unknown> | undefined;
      const opacity = typeof variantValue?.opacity === 'number' ? variantValue.opacity :
        (key.includes('hidden') || key.includes('exit') || key.includes('collapsed')) ? 0 : 1;
      reducedVariants[key] = {
        opacity,
        transition: { duration: 0.15 },
      };
    }
    return reducedVariants;
  }

  return variants;
}

export default useMotionSafe;
