/**
 * Motion Wrapper Component Library
 *
 * Pre-configured Motion components for common animation patterns.
 * All components respect reduced motion preferences for accessibility.
 *
 * @example
 * // Fade in content
 * <MotionFadeIn>Content</MotionFadeIn>
 *
 * // Slide in from left
 * <MotionSlideIn direction="left">Content</MotionSlideIn>
 *
 * // Animated list with stagger
 * <MotionList>
 *   <MotionListItem>Item 1</MotionListItem>
 *   <MotionListItem>Item 2</MotionListItem>
 * </MotionList>
 */

import { forwardRef, type ReactNode, type HTMLAttributes } from "react";
import { motion, AnimatePresence, useReducedMotion } from "motion/react";
import {
  listContainerVariants,
  listItemVariants,
  badgeVariants,
  skeletonVariants,
} from "../../design-system/micro-interactions";
import { cn } from "../../utils/cn";

// =============================================================================
// Types
// =============================================================================

type Direction = "up" | "down" | "left" | "right";

// Omit conflicting event handlers between React and Framer Motion
// React and Motion have incompatible types for these handlers
type OmitMotionConflicts<T> = Omit<
  T,
  | "onAnimationStart"
  | "onAnimationEnd"
  | "onAnimationIteration"
  | "onDragStart"
  | "onDragEnd"
  | "onDrag"
>;

interface MotionBaseProps
  extends OmitMotionConflicts<HTMLAttributes<HTMLDivElement>> {
  children: ReactNode;
  className?: string;
  /** Duration override in seconds */
  duration?: number;
  /** Delay before animation starts in seconds */
  delay?: number;
}

// =============================================================================
// MotionFadeIn
// =============================================================================

export type MotionFadeInProps = MotionBaseProps;

/**
 * Simple fade-in animation wrapper.
 * Fades content from opacity 0 to 1.
 */
export const MotionFadeIn = forwardRef<HTMLDivElement, MotionFadeInProps>(
  function MotionFadeIn(
    { children, className, duration = 0.3, delay = 0, ...props },
    ref
  ) {
    const prefersReducedMotion = useReducedMotion();

    return (
      <motion.div
        ref={ref}
        className={className}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{
          duration: prefersReducedMotion ? 0.1 : duration,
          delay: prefersReducedMotion ? 0 : delay,
        }}
        {...props}
      >
        {children}
      </motion.div>
    );
  }
);

// =============================================================================
// MotionSlideIn
// =============================================================================

export interface MotionSlideInProps extends MotionBaseProps {
  /** Direction to slide from */
  direction?: Direction;
  /** Distance to slide in pixels */
  distance?: number;
}

/**
 * Slide-in animation wrapper.
 * Slides content from the specified direction.
 */
export const MotionSlideIn = forwardRef<HTMLDivElement, MotionSlideInProps>(
  function MotionSlideIn(
    {
      children,
      className,
      direction = "up",
      distance = 20,
      duration = 0.3,
      delay = 0,
      ...props
    },
    ref
  ) {
    const prefersReducedMotion = useReducedMotion();

    const getInitialPosition = () => {
      if (prefersReducedMotion) return { opacity: 0 };
      switch (direction) {
        case "up":
          return { opacity: 0, y: distance };
        case "down":
          return { opacity: 0, y: -distance };
        case "left":
          return { opacity: 0, x: distance };
        case "right":
          return { opacity: 0, x: -distance };
      }
    };

    return (
      <motion.div
        ref={ref}
        className={className}
        initial={getInitialPosition()}
        animate={{ opacity: 1, x: 0, y: 0 }}
        exit={getInitialPosition()}
        transition={{
          type: prefersReducedMotion ? "tween" : "spring",
          stiffness: 300,
          damping: 25,
          duration: prefersReducedMotion ? 0.1 : duration,
          delay: prefersReducedMotion ? 0 : delay,
        }}
        {...props}
      >
        {children}
      </motion.div>
    );
  }
);

// =============================================================================
// MotionList
// =============================================================================

export interface MotionListProps
  extends OmitMotionConflicts<HTMLAttributes<HTMLUListElement>> {
  children: ReactNode;
  className?: string;
  /** Delay between each child animation */
  staggerDelay?: number;
}

/**
 * Animated list container with stagger effect.
 * Use with MotionListItem for coordinated animations.
 */
export const MotionList = forwardRef<HTMLUListElement, MotionListProps>(
  function MotionList(
    { children, className, staggerDelay = 0.05, ...props },
    ref
  ) {
    const prefersReducedMotion = useReducedMotion();

    const variants = prefersReducedMotion
      ? {
          hidden: { opacity: 0 },
          visible: { opacity: 1 },
        }
      : {
          hidden: listContainerVariants.hidden,
          visible: {
            ...listContainerVariants.visible,
            transition: {
              staggerChildren: staggerDelay,
              delayChildren: 0.1,
            },
          },
        };

    return (
      <motion.ul
        ref={ref}
        className={className}
        role="list"
        variants={variants}
        initial="hidden"
        animate="visible"
        {...props}
      >
        {children}
      </motion.ul>
    );
  }
);

// =============================================================================
// MotionListItem
// =============================================================================

export interface MotionListItemProps
  extends OmitMotionConflicts<HTMLAttributes<HTMLLIElement>> {
  children: ReactNode;
  className?: string;
}

/**
 * Animated list item for use with MotionList.
 */
export const MotionListItem = forwardRef<HTMLLIElement, MotionListItemProps>(
  function MotionListItem({ children, className, ...props }, ref) {
    const prefersReducedMotion = useReducedMotion();

    const variants = prefersReducedMotion
      ? {
          hidden: { opacity: 0 },
          visible: { opacity: 1, transition: { duration: 0.1 } },
        }
      : listItemVariants;

    return (
      <motion.li
        ref={ref}
        className={className}
        variants={variants}
        {...props}
      >
        {children}
      </motion.li>
    );
  }
);

// =============================================================================
// MotionPanel
// =============================================================================

export interface MotionPanelProps extends MotionBaseProps {
  /** Whether the panel is open */
  isOpen: boolean;
  /** Direction the panel slides from */
  direction?: Direction;
}

/**
 * Animated panel with AnimatePresence for mount/unmount.
 * Use for sidebars, drawers, and expandable panels.
 */
export function MotionPanel({
  children,
  className,
  isOpen,
  direction = "left",
  duration = 0.3,
  ...props
}: MotionPanelProps) {
  const prefersReducedMotion = useReducedMotion();

  const getTransform = (hidden: boolean) => {
    if (prefersReducedMotion) return {};
    const value = hidden ? "100%" : "0%";
    switch (direction) {
      case "left":
        return { x: hidden ? "-100%" : "0%" };
      case "right":
        return { x: value };
      case "up":
        return { y: hidden ? "-100%" : "0%" };
      case "down":
        return { y: value };
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className={className}
          initial={{ opacity: 0, ...getTransform(true) }}
          animate={{ opacity: 1, ...getTransform(false) }}
          exit={{ opacity: 0, ...getTransform(true) }}
          transition={{
            type: prefersReducedMotion ? "tween" : "spring",
            stiffness: 300,
            damping: 30,
            duration: prefersReducedMotion ? 0.1 : duration,
          }}
          {...props}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// =============================================================================
// MotionSkeleton
// =============================================================================

export interface MotionSkeletonProps
  extends OmitMotionConflicts<Omit<HTMLAttributes<HTMLDivElement>, "children">> {
  /** Width of the skeleton */
  width?: string | number;
  /** Height of the skeleton */
  height?: string | number;
  /** Shape variant */
  variant?: "rectangular" | "circular" | "text";
  className?: string;
}

/**
 * Animated skeleton loading placeholder.
 * Pulses to indicate loading state.
 */
export const MotionSkeleton = forwardRef<HTMLDivElement, MotionSkeletonProps>(
  function MotionSkeleton(
    { width, height, variant = "rectangular", className, style, ...props },
    ref
  ) {
    const prefersReducedMotion = useReducedMotion();

    const variantClasses = {
      rectangular: "rounded",
      circular: "rounded-full",
      text: "rounded h-4",
    };

    return (
      <motion.div
        ref={ref}
        className={cn(
          "bg-neutral-5",
          variantClasses[variant],
          className
        )}
        style={{
          width: typeof width === "number" ? `${width}px` : width,
          height: typeof height === "number" ? `${height}px` : height,
          ...style,
        }}
        variants={prefersReducedMotion ? undefined : skeletonVariants}
        animate={prefersReducedMotion ? undefined : "pulse"}
        {...props}
      />
    );
  }
);

// =============================================================================
// MotionBadge
// =============================================================================

export interface MotionBadgeProps extends MotionBaseProps {
  /** Whether to show pulse animation */
  pulse?: boolean;
  /** Visual variant */
  variant?: "default" | "success" | "warning" | "error" | "info";
}

/**
 * Animated badge with optional pulse effect.
 * Use for notification counts, status indicators.
 */
export const MotionBadge = forwardRef<HTMLSpanElement, MotionBadgeProps>(
  function MotionBadge(
    { children, className, pulse = false, variant = "default", ...props },
    ref
  ) {
    const prefersReducedMotion = useReducedMotion();

    const variantClasses = {
      default: "bg-neutral-5 text-neutral-12",
      success: "bg-success-9 text-neutral-12",
      warning: "bg-warning-9 text-neutral-12",
      error: "bg-error-9 text-neutral-12",
      info: "bg-info-9 text-neutral-12",
    };

    return (
      <motion.span
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center px-2 py-0.5 text-xs font-medium rounded-full",
          variantClasses[variant],
          className
        )}
        variants={prefersReducedMotion ? undefined : badgeVariants}
        initial="hidden"
        animate={pulse && !prefersReducedMotion ? "visible" : "visible"}
        {...props}
      >
        {children}
      </motion.span>
    );
  }
);

// =============================================================================
// ReducedMotionAnimatePresence
// =============================================================================

export interface ReducedMotionAnimatePresenceProps {
  children: ReactNode;
  /** AnimatePresence mode */
  mode?: "sync" | "wait" | "popLayout";
  /** Custom exit before enter behavior */
  exitBeforeEnter?: boolean;
  /** Initial animation on first render */
  initial?: boolean;
  /** Callback when all exiting animations complete */
  onExitComplete?: () => void;
}

/**
 * Accessibility-aware AnimatePresence wrapper.
 *
 * When reduced motion is preferred, uses instant transitions (no animation delay)
 * while still supporting enter/exit lifecycle for proper mounting/unmounting.
 *
 * @example
 * <ReducedMotionAnimatePresence>
 *   {isVisible && (
 *     <motion.div
 *       initial={{ opacity: 0, y: 20 }}
 *       animate={{ opacity: 1, y: 0 }}
 *       exit={{ opacity: 0, y: 20 }}
 *     >
 *       Content
 *     </motion.div>
 *   )}
 * </ReducedMotionAnimatePresence>
 */
export function ReducedMotionAnimatePresence({
  children,
  mode = "sync",
  initial = true,
  onExitComplete,
}: ReducedMotionAnimatePresenceProps) {
  const prefersReducedMotion = useReducedMotion();

  // AnimatePresence handles mount/unmount lifecycle
  // Child components should use useReducedMotion for their animations
  return (
    <AnimatePresence
      mode={mode}
      initial={prefersReducedMotion ? false : initial}
      onExitComplete={onExitComplete}
    >
      {children}
    </AnimatePresence>
  );
}

// =============================================================================
// Index Export
// =============================================================================

// eslint-disable-next-line react-refresh/only-export-components -- Intentional namespace pattern for component grouping
export const Motion = {
  FadeIn: MotionFadeIn,
  SlideIn: MotionSlideIn,
  List: MotionList,
  ListItem: MotionListItem,
  Panel: MotionPanel,
  Skeleton: MotionSkeleton,
  Badge: MotionBadge,
  AnimatePresence: ReducedMotionAnimatePresence,
};

export default Motion;
