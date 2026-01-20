/**
 * Micro-Interactions Library
 *
 * Reusable animation variants for common UI patterns.
 * These are Motion Variants that can be used with the variants prop.
 *
 * @see https://motion.dev/docs/react-animation#variants
 */

import type { Variants } from 'motion/react';

/**
 * Button press effect - subtle scale on hover/press.
 *
 * @example
 * <motion.button variants={buttonVariants} initial="rest" whileHover="hover" whileTap="pressed">
 */
export const buttonVariants: Variants = {
  rest: { scale: 1 },
  hover: { scale: 1.02 },
  pressed: { scale: 0.98 },
};

/**
 * Checkbox/toggle check animation - animated path drawing.
 *
 * @example
 * <motion.path variants={checkboxVariants} initial="unchecked" animate={isChecked ? "checked" : "unchecked"} />
 */
export const checkboxVariants: Variants = {
  unchecked: { pathLength: 0, opacity: 0 },
  checked: {
    pathLength: 1,
    opacity: 1,
    transition: { duration: 0.2, ease: 'easeOut' },
  },
};

/**
 * List container - orchestrates staggered children animations.
 *
 * @example
 * <motion.ul variants={listContainerVariants} initial="hidden" animate="visible">
 */
export const listContainerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
      delayChildren: 0.1,
    },
  },
};

/**
 * List item - slides in from left with fade.
 * Use with listContainerVariants for staggered effect.
 *
 * @example
 * <motion.li variants={listItemVariants}>
 */
export const listItemVariants: Variants = {
  hidden: { opacity: 0, x: -10 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { type: 'spring', stiffness: 300, damping: 25 },
  },
};

/**
 * Toast notification - slides up from bottom.
 *
 * @example
 * <motion.div variants={toastVariants} initial="initial" animate="animate" exit="exit">
 */
export const toastVariants: Variants = {
  initial: { opacity: 0, y: 50, scale: 0.9 },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: 'spring', stiffness: 400, damping: 30 },
  },
  exit: {
    opacity: 0,
    y: 20,
    scale: 0.9,
    transition: { duration: 0.15 },
  },
};

/**
 * Modal/dialog - scales up from center.
 *
 * @example
 * <motion.div variants={modalVariants} initial="hidden" animate="visible" exit="hidden">
 */
export const modalVariants: Variants = {
  hidden: { opacity: 0, scale: 0.95, y: 10 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { type: 'spring', stiffness: 300, damping: 25 },
  },
};

/**
 * Modal backdrop - simple fade.
 *
 * @example
 * <motion.div variants={backdropVariants} initial="hidden" animate="visible" exit="hidden">
 */
export const backdropVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
};

/**
 * Dropdown menu - slides down with fade.
 *
 * @example
 * <motion.div variants={dropdownVariants} initial="hidden" animate="visible" exit="hidden">
 */
export const dropdownVariants: Variants = {
  hidden: {
    opacity: 0,
    y: -8,
    scale: 0.95,
    transition: { duration: 0.1 },
  },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: 'spring', stiffness: 400, damping: 30 },
  },
};

/**
 * Skeleton pulse - infinite opacity animation (reduced motion safe).
 *
 * @example
 * <motion.div variants={skeletonVariants} animate="pulse">
 */
export const skeletonVariants: Variants = {
  pulse: {
    opacity: [0.5, 1, 0.5],
    transition: {
      duration: 1.5,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
};

/**
 * Shimmer loading effect - animated gradient sweep for skeleton loaders.
 * Creates a horizontal shimmer effect that sweeps across the element.
 *
 * CSS requirement: Element needs a shimmer gradient background:
 * background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
 * background-size: 200% 100%;
 *
 * @example
 * <motion.div
 *   className="bg-gradient-to-r from-transparent via-white/40 to-transparent bg-[length:200%_100%]"
 *   variants={shimmerVariants}
 *   animate="shimmer"
 * />
 */
export const shimmerVariants: Variants = {
  shimmer: {
    backgroundPosition: ['200% 0', '-200% 0'],
    transition: {
      duration: 1.5,
      repeat: Infinity,
      ease: 'linear',
    },
  },
};

/**
 * Card hover effect - subtle lift and shadow.
 *
 * @example
 * <motion.div variants={cardHoverVariants} initial="rest" whileHover="hover">
 */
export const cardHoverVariants: Variants = {
  rest: {
    y: 0,
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
  },
  hover: {
    y: -2,
    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
    transition: { type: 'spring', stiffness: 400, damping: 25 },
  },
};

/**
 * Accordion content - expand/collapse with opacity.
 *
 * @example
 * <motion.div variants={accordionVariants} initial="collapsed" animate={isOpen ? "expanded" : "collapsed"}>
 */
export const accordionVariants: Variants = {
  collapsed: {
    height: 0,
    opacity: 0,
    transition: { duration: 0.2, ease: 'easeInOut' },
  },
  expanded: {
    height: 'auto',
    opacity: 1,
    transition: { duration: 0.2, ease: 'easeInOut' },
  },
};

/**
 * Tab indicator - sliding underline.
 *
 * @example
 * <motion.div layoutId="tab-indicator" className="absolute bottom-0 h-0.5 bg-primary-9" />
 */
export const tabIndicatorVariants: Variants = {
  inactive: { opacity: 0.5 },
  active: { opacity: 1 },
};

/**
 * Notification badge - bouncy entrance.
 *
 * @example
 * <motion.span variants={badgeVariants} initial="hidden" animate="visible">
 */
export const badgeVariants: Variants = {
  hidden: { scale: 0, opacity: 0 },
  visible: {
    scale: 1,
    opacity: 1,
    transition: { type: 'spring', stiffness: 500, damping: 15 },
  },
};

/**
 * Spinner rotation - continuous rotation (reduced motion safe as it's functional).
 *
 * @example
 * <motion.div animate={{ rotate: 360 }} transition={spinnerTransition}>
 */
export const spinnerTransition = {
  repeat: Infinity,
  duration: 1,
  ease: 'linear',
} as const;

/**
 * Trace node selection - scale and shadow emphasis.
 *
 * @example
 * <motion.div
 *   animate={isSelected ? "selected" : "default"}
 *   variants={traceNodeVariants}
 * />
 */
export const traceNodeVariants: Variants = {
  default: {
    scale: 1,
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
  },
  selected: {
    scale: 1.02,
    boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
    transition: { type: 'spring', stiffness: 300, damping: 25 },
  },
  hover: {
    scale: 1.01,
    boxShadow: '0 4px 16px rgba(0,0,0,0.15)',
  },
};

/**
 * Chip/tag animation - scale in/out with spring physics.
 * Used for attachment previews, tags, badges that can be added/removed.
 *
 * @example
 * <AnimatePresence>
 *   {chips.map(chip => (
 *     <motion.div key={chip.id} variants={chipVariants} initial="hidden" animate="visible" exit="exit" layout>
 *   ))}
 * </AnimatePresence>
 */
export const chipVariants: Variants = {
  hidden: {
    opacity: 0,
    scale: 0.8,
    x: -10,
  },
  visible: {
    opacity: 1,
    scale: 1,
    x: 0,
    transition: { type: 'spring', stiffness: 400, damping: 25 },
  },
  exit: {
    opacity: 0,
    scale: 0.8,
    x: -10,
    transition: { duration: 0.15 },
  },
};

/**
 * Session item animation - for session list items.
 * Slides in from right with fade.
 *
 * @example
 * <motion.div variants={sessionItemVariants} layout>
 */
export const sessionItemVariants: Variants = {
  hidden: { opacity: 0, x: 20 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { type: 'spring', stiffness: 300, damping: 25 },
  },
  exit: {
    opacity: 0,
    x: -20,
    transition: { duration: 0.15 },
  },
};

/**
 * Panel slide-in animation - for sidebars and panels.
 * Slides in from specified direction.
 *
 * @example
 * <motion.div variants={panelSlideVariants} initial="hidden" animate="visible" exit="hidden">
 */
export const panelSlideVariants: Variants = {
  hidden: {
    opacity: 0,
    y: -10,
  },
  visible: {
    opacity: 1,
    y: 0,
    transition: { type: 'spring', stiffness: 300, damping: 25 },
  },
};

/**
 * Voice recording pulse - for microphone button active state.
 *
 * @example
 * <motion.div variants={voiceRecordingVariants} animate={isRecording ? "recording" : "idle"}>
 */
export const voiceRecordingVariants: Variants = {
  idle: {
    scale: 1,
    boxShadow: '0 0 0 0 rgba(239, 68, 68, 0)',
  },
  recording: {
    scale: [1, 1.05, 1],
    boxShadow: [
      '0 0 0 0 rgba(239, 68, 68, 0.4)',
      '0 0 0 8px rgba(239, 68, 68, 0)',
      '0 0 0 0 rgba(239, 68, 68, 0.4)',
    ],
    transition: {
      duration: 1.5,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
};

/**
 * Send button pulse - subtle pulse when ready to send.
 *
 * @example
 * <motion.button variants={sendButtonVariants} animate={hasContent ? "ready" : "idle"}>
 */
export const sendButtonVariants: Variants = {
  idle: { scale: 1 },
  ready: {
    scale: [1, 1.05, 1],
    transition: {
      duration: 0.3,
      times: [0, 0.5, 1],
    },
  },
  pressed: { scale: 0.95 },
};

// =============================================================================
// DevTools Animation Variants
// =============================================================================

/**
 * DevTools panel expand/collapse animation.
 * Slides up from bottom with height animation.
 *
 * @example
 * <motion.div variants={devToolsPanelVariants} initial="collapsed" animate={isOpen ? "expanded" : "collapsed"}>
 */
export const devToolsPanelVariants: Variants = {
  collapsed: {
    height: 0,
    opacity: 0,
    transition: { duration: 0.2, ease: 'easeInOut' },
  },
  expanded: {
    height: 'auto',
    opacity: 1,
    transition: { type: 'spring', stiffness: 300, damping: 30 },
  },
};

/**
 * Tab content transition - crossfade between tabs.
 *
 * @example
 * <AnimatePresence mode="wait">
 *   <motion.div key={activeTab} variants={tabContentVariants} initial="hidden" animate="visible" exit="exit">
 * </AnimatePresence>
 */
export const tabContentVariants: Variants = {
  hidden: {
    opacity: 0,
    y: 10,
    transition: { duration: 0.1 },
  },
  visible: {
    opacity: 1,
    y: 0,
    transition: { type: 'spring', stiffness: 300, damping: 25 },
  },
  exit: {
    opacity: 0,
    y: -10,
    transition: { duration: 0.1 },
  },
};

/**
 * Console/log entry animation - for individual log entries.
 * Use with listContainerVariants for staggered effect.
 *
 * @example
 * <motion.div variants={logEntryVariants}>
 */
export const logEntryVariants: Variants = {
  hidden: { opacity: 0, x: -10 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { type: 'spring', stiffness: 400, damping: 30 },
  },
};

/**
 * Alert badge pulse - for new/critical alerts.
 *
 * @example
 * <motion.span variants={alertBadgePulseVariants} animate={hasNew ? "pulse" : "idle"}>
 */
export const alertBadgePulseVariants: Variants = {
  idle: { scale: 1 },
  pulse: {
    scale: [1, 1.2, 1],
    transition: {
      duration: 0.6,
      repeat: 2,
      ease: 'easeInOut',
    },
  },
};

/**
 * Timeline scrubber animation - for time-travel debugging.
 *
 * @example
 * <motion.div variants={timelineScrubberVariants} whileDrag="dragging">
 */
export const timelineScrubberVariants: Variants = {
  rest: {
    scale: 1,
    boxShadow: '0 0 0 0 rgba(99, 102, 241, 0)',
  },
  hover: {
    scale: 1.1,
    boxShadow: '0 0 0 4px rgba(99, 102, 241, 0.2)',
  },
  dragging: {
    scale: 1.15,
    boxShadow: '0 0 0 6px rgba(99, 102, 241, 0.3)',
  },
};

/**
 * Network request row animation - for network tab entries.
 *
 * @example
 * <motion.tr variants={networkRowVariants}>
 */
export const networkRowVariants: Variants = {
  hidden: { opacity: 0, x: -8 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { type: 'spring', stiffness: 300, damping: 25 },
  },
  hover: {
    backgroundColor: 'rgba(99, 102, 241, 0.05)',
  },
};

/**
 * Problem indicator animation - for problems/issues in DevTools.
 *
 * @example
 * <motion.div variants={problemIndicatorVariants} animate={severity}>
 */
export const problemIndicatorVariants: Variants = {
  error: {
    scale: [1, 1.05, 1],
    transition: { duration: 0.3 },
  },
  warning: { scale: 1 },
  info: { scale: 1 },
};

/**
 * Resize handle drag indicator - shows resize is active.
 *
 * @example
 * <motion.div variants={resizeHandleVariants} whileHover="hover" whileDrag="dragging">
 */
export const resizeHandleVariants: Variants = {
  rest: {
    scaleX: 1,
    backgroundColor: 'rgba(99, 102, 241, 0)',
  },
  hover: {
    scaleX: 1.5,
    backgroundColor: 'rgba(99, 102, 241, 0.2)',
    transition: { duration: 0.15 },
  },
  dragging: {
    scaleX: 2,
    backgroundColor: 'rgba(99, 102, 241, 0.4)',
    transition: { duration: 0.1 },
  },
};

/**
 * DevTools tab button animation - for tab selection feedback.
 *
 * @example
 * <motion.button variants={devToolsTabVariants} initial="rest" whileHover="hover" whileTap="pressed">
 */
export const devToolsTabVariants: Variants = {
  rest: { scale: 1 },
  hover: {
    scale: 1.02,
    transition: { type: 'spring', stiffness: 400, damping: 25 },
  },
  pressed: { scale: 0.98 },
  active: {
    scale: 1,
    transition: { type: 'spring', stiffness: 300, damping: 25 },
  },
};

/**
 * Filter button animation - for dropdown filter toggles in DevTools tabs.
 *
 * @example
 * <motion.button variants={filterButtonVariants} initial="rest" whileHover="hover" whileTap="pressed">
 */
export const filterButtonVariants: Variants = {
  rest: { scale: 1 },
  hover: {
    scale: 1.02,
    transition: { type: 'spring', stiffness: 400, damping: 30 },
  },
  pressed: { scale: 0.98 },
};

/**
 * Insight card animation - for AI insights with hover feedback.
 *
 * @example
 * <motion.div variants={insightCardVariants} initial="rest" whileHover="hover">
 */
export const insightCardVariants: Variants = {
  rest: {
    y: 0,
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
  },
  hover: {
    y: -1,
    boxShadow: '0 4px 12px rgba(0,0,0,0.12)',
    transition: { type: 'spring', stiffness: 400, damping: 25 },
  },
};

/**
 * Spinner animation - for loading indicators.
 * Safe for reduced motion as it's functional.
 *
 * @example
 * <motion.div variants={spinnerVariants} animate="spin">
 */
export const spinnerVariants: Variants = {
  spin: {
    rotate: 360,
    transition: {
      duration: 1,
      repeat: Infinity,
      ease: 'linear',
    },
  },
};
