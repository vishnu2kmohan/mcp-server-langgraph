 
/**
 * Animations Stories
 *
 * Documents the animation system using Motion (formerly Framer Motion).
 * Showcases duration tokens, spring physics, easing functions,
 * and reusable micro-interaction variants.
 *
 * @see src/design-system/animation-tokens.ts
 * @see src/design-system/micro-interactions.ts
 */

import { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { motion, AnimatePresence } from "motion/react";
import { Check, X, Bell, ChevronDown, Loader2 } from "lucide-react";
import {
  ANIMATION_DURATION,
  ANIMATION_SPRING,
  ANIMATION_EASING,
  ANIMATION_PRESETS,
} from "../design-system/animation-tokens";
import {
  buttonVariants,
  listContainerVariants,
  listItemVariants,
  toastVariants,
  modalVariants,
  backdropVariants,
  dropdownVariants,
  cardHoverVariants,
  accordionVariants,
  badgeVariants,
  spinnerTransition,
  shimmerVariants,
  skeletonVariants,
} from "../design-system/micro-interactions";

// =============================================================================
// Duration Tokens Demo
// =============================================================================

function DurationTokens() {
  const [activeDemo, setActiveDemo] = useState<string | null>(null);

  const durations = [
    { name: "instant", value: ANIMATION_DURATION.instant, ms: "100ms", usage: "Hover states, micro-feedback" },
    { name: "fast", value: ANIMATION_DURATION.fast, ms: "150ms", usage: "Button states, quick feedback" },
    { name: "normal", value: ANIMATION_DURATION.normal, ms: "200ms", usage: "Standard transitions" },
    { name: "slow", value: ANIMATION_DURATION.slow, ms: "300ms", usage: "Complex animations, modals" },
    { name: "slower", value: ANIMATION_DURATION.slower, ms: "500ms", usage: "Page transitions" },
  ];

  return (
    <div className="space-y-6 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">Duration Tokens</h2>
        <p className="text-neutral-11">
          Standardized animation durations for consistent timing across the UI.
        </p>
      </div>

      <div className="space-y-3">
        {durations.map((d) => (
          <div key={d.name} className="flex items-center gap-4 p-3 border border-neutral-6 rounded-lg">
            <div className="w-24 shrink-0">
              <code className="text-sm text-neutral-11">{d.name}</code>
            </div>
            <div className="w-16 shrink-0 text-sm text-neutral-10">{d.ms}</div>
            <div className="flex-1 text-sm text-neutral-10">{d.usage}</div>
            <div className="w-40 shrink-0">
              <button
                onClick={() => setActiveDemo(activeDemo === d.name ? null : d.name)}
                className="px-3 py-1.5 bg-primary-9 text-neutral-12 text-sm rounded hover:bg-primary-10 transition-colors"
              >
                {activeDemo === d.name ? "Reset" : "Play"}
              </button>
            </div>
            <div className="w-32 h-8 bg-neutral-4 rounded overflow-hidden">
              <motion.div
                className="h-full bg-primary-9"
                initial={{ width: 0 }}
                animate={{ width: activeDemo === d.name ? "100%" : 0 }}
                transition={{ duration: d.value, ease: "easeOut" }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// =============================================================================
// Spring Physics Demo
// =============================================================================

function SpringPhysics() {
  const [trigger, setTrigger] = useState(0);

  const springs = [
    { name: "snappy", config: ANIMATION_SPRING.snappy, desc: "Buttons, toggles - quick response" },
    { name: "smooth", config: ANIMATION_SPRING.smooth, desc: "Most UI elements - natural feel" },
    { name: "gentle", config: ANIMATION_SPRING.gentle, desc: "Large elements, modals - slow settle" },
    { name: "bouncy", config: ANIMATION_SPRING.bouncy, desc: "Success states - playful feel" },
  ];

  return (
    <div className="space-y-6 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">Spring Physics</h2>
        <p className="text-neutral-11">
          Physics-based springs create natural, organic motion.
        </p>
      </div>

      <button
        onClick={() => setTrigger((t) => t + 1)}
        className="px-4 py-2 bg-primary-9 text-neutral-12 rounded hover:bg-primary-10 transition-colors"
      >
        Trigger All Springs
      </button>

      <div className="grid grid-cols-2 gap-4 mt-4">
        {springs.map((s) => (
          <div key={s.name} className="p-4 border border-neutral-6 rounded-lg">
            <div className="flex items-center justify-between mb-3">
              <code className="text-sm font-medium text-neutral-12">{s.name}</code>
              <span className="text-xs text-neutral-10">
                stiffness: {s.config.stiffness}, damping: {s.config.damping}
              </span>
            </div>
            <p className="text-sm text-neutral-10 mb-4">{s.desc}</p>
            <div className="h-12 bg-neutral-4 rounded flex items-center px-2">
              <motion.div
                key={trigger}
                className="w-10 h-10 bg-primary-9 rounded"
                initial={{ x: 0 }}
                animate={{ x: 200 }}
                transition={s.config}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// =============================================================================
// Easing Functions Demo
// =============================================================================

function EasingFunctions() {
  const [trigger, setTrigger] = useState(0);

  const easings = [
    { name: "easeOut", values: ANIMATION_EASING.easeOut, desc: "Entrances - decelerating" },
    { name: "easeIn", values: ANIMATION_EASING.easeIn, desc: "Exits - accelerating" },
    { name: "easeInOut", values: ANIMATION_EASING.easeInOut, desc: "State changes - symmetric" },
    { name: "anticipate", values: ANIMATION_EASING.anticipate, desc: "Emphasis - pull back first" },
  ];

  return (
    <div className="space-y-6 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">Easing Functions</h2>
        <p className="text-neutral-11">
          Cubic-bezier curves for non-spring animations.
        </p>
      </div>

      <button
        onClick={() => setTrigger((t) => t + 1)}
        className="px-4 py-2 bg-primary-9 text-neutral-12 rounded hover:bg-primary-10 transition-colors"
      >
        Trigger All Easings
      </button>

      <div className="space-y-4 mt-4">
        {easings.map((e) => (
          <div key={e.name} className="flex items-center gap-4 p-3 border border-neutral-6 rounded-lg">
            <div className="w-28 shrink-0">
              <code className="text-sm text-neutral-11">{e.name}</code>
            </div>
            <div className="w-40 shrink-0 text-sm text-neutral-10">{e.desc}</div>
            <div className="flex-1 h-8 bg-neutral-4 rounded overflow-hidden">
              <motion.div
                key={trigger}
                className="w-8 h-full bg-primary-9 rounded"
                initial={{ x: 0 }}
                animate={{ x: "calc(100% - 32px)" }}
                transition={{ duration: 0.5, ease: e.values }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// =============================================================================
// Animation Presets Demo
// =============================================================================

function AnimationPresets() {
  const [activePreset, setActivePreset] = useState<string | null>(null);

  const presets = [
    { name: "fade", desc: "Simple opacity transition" },
    { name: "slideUp", desc: "Modal entrances, toasts" },
    { name: "slideDown", desc: "Collapsible content" },
    { name: "scale", desc: "Buttons, cards, popovers" },
    { name: "slideInRight", desc: "Side panels, drawers" },
    { name: "slideInLeft", desc: "Back navigation" },
  ];

  return (
    <div className="space-y-6 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">Animation Presets</h2>
        <p className="text-neutral-11">
          Ready-to-use animation configurations that can be spread onto Motion components.
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {presets.map((p) => (
          <div key={p.name} className="p-4 border border-neutral-6 rounded-lg">
            <code className="text-sm font-medium text-neutral-12">{p.name}</code>
            <p className="text-xs text-neutral-10 mt-1 mb-4">{p.desc}</p>
            <button
              onClick={() => setActivePreset(activePreset === p.name ? null : p.name)}
              className="w-full py-1.5 bg-neutral-4 text-neutral-11 text-sm rounded hover:bg-neutral-4 transition-colors"
            >
              {activePreset === p.name ? "Hide" : "Demo"}
            </button>
            <div className="h-20 mt-3 bg-neutral-2 rounded flex items-center justify-center overflow-hidden">
              <AnimatePresence>
                {activePreset === p.name && (
                  <motion.div
                    className="w-12 h-12 bg-primary-9 rounded"
                    {...(ANIMATION_PRESETS[p.name as keyof typeof ANIMATION_PRESETS] as object)}
                  />
                )}
              </AnimatePresence>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-neutral-2 border border-neutral-6 rounded-lg p-4 font-mono text-xs">
        <p className="text-neutral-10 mb-2">{"// Usage example"}</p>
        <p className="text-neutral-12">{"<motion.div {...ANIMATION_PRESETS.slideUp}>"}</p>
        <p className="text-neutral-12 pl-4">{"Content here"}</p>
        <p className="text-neutral-12">{"</motion.div>"}</p>
      </div>
    </div>
  );
}

// =============================================================================
// Micro-Interactions Demo
// =============================================================================

function MicroInteractions() {
  const [showToast, setShowToast] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [accordionOpen, setAccordionOpen] = useState(false);
  const [badgeCount, setBadgeCount] = useState(0);

  const listItems = ["Item 1", "Item 2", "Item 3", "Item 4"];

  return (
    <div className="space-y-8 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">Micro-Interactions</h2>
        <p className="text-neutral-11">
          Reusable Motion variants for common UI patterns.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Button */}
        <div className="p-4 border border-neutral-6 rounded-lg">
          <h4 className="font-medium text-neutral-12 mb-3">Button Press</h4>
          <motion.button
            variants={buttonVariants}
            initial="rest"
            whileHover="hover"
            whileTap="pressed"
            className="px-4 py-2 bg-primary-9 text-neutral-12 rounded"
          >
            Hover & Click Me
          </motion.button>
          <p className="text-xs text-neutral-10 mt-2">buttonVariants</p>
        </div>

        {/* Card Hover */}
        <div className="p-4 border border-neutral-6 rounded-lg">
          <h4 className="font-medium text-neutral-12 mb-3">Card Hover</h4>
          <motion.div
            variants={cardHoverVariants}
            initial="rest"
            whileHover="hover"
            className="p-4 bg-neutral-2 rounded-lg cursor-pointer"
          >
            <p className="text-sm text-neutral-12">Hover over me</p>
          </motion.div>
          <p className="text-xs text-neutral-10 mt-2">cardHoverVariants</p>
        </div>

        {/* List Stagger */}
        <div className="p-4 border border-neutral-6 rounded-lg">
          <h4 className="font-medium text-neutral-12 mb-3">List Stagger</h4>
          <motion.ul
            variants={listContainerVariants}
            initial="hidden"
            animate="visible"
            className="space-y-2"
          >
            {listItems.map((item) => (
              <motion.li
                key={item}
                variants={listItemVariants}
                className="p-2 bg-neutral-4 rounded text-sm text-neutral-12"
              >
                {item}
              </motion.li>
            ))}
          </motion.ul>
          <p className="text-xs text-neutral-10 mt-2">listContainerVariants + listItemVariants</p>
        </div>

        {/* Toast */}
        <div className="p-4 border border-neutral-6 rounded-lg">
          <h4 className="font-medium text-neutral-12 mb-3">Toast Notification</h4>
          <button
            onClick={() => {
              setShowToast(true);
              setTimeout(() => setShowToast(false), 2000);
            }}
            className="px-3 py-1.5 bg-primary-9 text-neutral-12 text-sm rounded"
          >
            Show Toast
          </button>
          <div className="h-16 mt-3 flex items-end justify-center">
            <AnimatePresence>
              {showToast && (
                <motion.div
                  variants={toastVariants}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                  className="px-4 py-2 bg-success-9 text-neutral-12 rounded-lg flex items-center gap-2"
                >
                  <Check size={16} /> Saved!
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          <p className="text-xs text-neutral-10 mt-2">toastVariants</p>
        </div>

        {/* Dropdown */}
        <div className="p-4 border border-neutral-6 rounded-lg">
          <h4 className="font-medium text-neutral-12 mb-3">Dropdown Menu</h4>
          <div className="relative">
            <button
              onClick={() => setShowDropdown(!showDropdown)}
              className="flex items-center gap-2 px-3 py-1.5 bg-neutral-4 text-neutral-12 text-sm rounded"
            >
              Options <ChevronDown size={14} />
            </button>
            <AnimatePresence>
              {showDropdown && (
                <motion.div
                  variants={dropdownVariants}
                  initial="hidden"
                  animate="visible"
                  exit="hidden"
                  className="absolute top-full left-0 mt-1 w-32 bg-neutral-1 border border-neutral-6 rounded-lg shadow-lg py-1 z-10"
                >
                  {["Edit", "Copy", "Delete"].map((item) => (
                    <button
                      key={item}
                      onClick={() => setShowDropdown(false)}
                      className="w-full px-3 py-1.5 text-left text-sm text-neutral-12 hover:bg-neutral-4"
                    >
                      {item}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          <p className="text-xs text-neutral-10 mt-2">dropdownVariants</p>
        </div>

        {/* Accordion */}
        <div className="p-4 border border-neutral-6 rounded-lg">
          <h4 className="font-medium text-neutral-12 mb-3">Accordion</h4>
          <button
            onClick={() => setAccordionOpen(!accordionOpen)}
            className="flex items-center justify-between w-full p-2 bg-neutral-4 rounded text-sm text-neutral-12"
          >
            Toggle Content
            <motion.span
              animate={{ rotate: accordionOpen ? 180 : 0 }}
              transition={{ duration: 0.2 }}
            >
              <ChevronDown size={14} />
            </motion.span>
          </button>
          <AnimatePresence initial={false}>
            {accordionOpen && (
              <motion.div
                variants={accordionVariants}
                initial="collapsed"
                animate="expanded"
                exit="collapsed"
                className="overflow-hidden"
              >
                <div className="p-3 text-sm text-neutral-11">
                  This content expands and collapses smoothly.
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          <p className="text-xs text-neutral-10 mt-2">accordionVariants</p>
        </div>

        {/* Badge */}
        <div className="p-4 border border-neutral-6 rounded-lg">
          <h4 className="font-medium text-neutral-12 mb-3">Notification Badge</h4>
          <button
            onClick={() => setBadgeCount((c) => c + 1)}
            className="relative px-4 py-2 bg-neutral-4 text-neutral-12 rounded"
          >
            <Bell size={20} />
            <AnimatePresence>
              {badgeCount > 0 && (
                <motion.span
                  key={badgeCount}
                  variants={badgeVariants}
                  initial="hidden"
                  animate="visible"
                  className="absolute -top-1 -right-1 w-5 h-5 bg-error-9 text-neutral-12 text-xs rounded-full flex items-center justify-center"
                >
                  {badgeCount}
                </motion.span>
              )}
            </AnimatePresence>
          </button>
          <button
            onClick={() => setBadgeCount(0)}
            className="ml-2 px-2 py-1 text-xs text-neutral-10 hover:text-neutral-12"
          >
            Reset
          </button>
          <p className="text-xs text-neutral-10 mt-2">badgeVariants</p>
        </div>

        {/* Spinner */}
        <div className="p-4 border border-neutral-6 rounded-lg">
          <h4 className="font-medium text-neutral-12 mb-3">Loading Spinner</h4>
          <motion.div
            animate={{ rotate: 360 }}
            transition={spinnerTransition}
            className="w-8 h-8 text-primary-9"
          >
            <Loader2 size={32} />
          </motion.div>
          <p className="text-xs text-neutral-10 mt-2">spinnerTransition</p>
        </div>
      </div>

      {/* Modal Demo */}
      <div className="p-4 border border-neutral-6 rounded-lg">
        <h4 className="font-medium text-neutral-12 mb-3">Modal Dialog</h4>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-primary-9 text-neutral-12 rounded"
        >
          Open Modal
        </button>
        <AnimatePresence>
          {showModal && (
            <>
              <motion.div
                variants={backdropVariants}
                initial="hidden"
                animate="visible"
                exit="hidden"
                onClick={() => setShowModal(false)}
                className="fixed inset-0 bg-neutral-a6 z-40"
              />
              <motion.div
                variants={modalVariants}
                initial="hidden"
                animate="visible"
                exit="hidden"
                className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-80 p-6 bg-neutral-1 rounded-lg shadow-xl z-50"
              >
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-medium text-neutral-12">Modal Title</h3>
                  <button onClick={() => setShowModal(false)} className="text-neutral-10 hover:text-neutral-12">
                    <X size={18} />
                  </button>
                </div>
                <p className="text-sm text-neutral-11">Modal content with animated entrance and exit.</p>
              </motion.div>
            </>
          )}
        </AnimatePresence>
        <p className="text-xs text-neutral-10 mt-2">modalVariants + backdropVariants</p>
      </div>
    </div>
  );
}

// =============================================================================
// Loading States Demo (Shimmer + Skeleton)
// =============================================================================

function LoadingStates() {
  return (
    <div className="space-y-8 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">Loading States</h2>
        <p className="text-neutral-11">
          Shimmer and skeleton animations for loading placeholders.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Shimmer Animation */}
        <div className="p-4 border border-neutral-6 rounded-lg">
          <h4 className="font-medium text-neutral-12 mb-3">Shimmer Effect</h4>
          <p className="text-sm text-neutral-10 mb-4">
            Continuous gradient sweep for loading skeletons.
          </p>
          <div className="space-y-3">
            {/* Text skeleton */}
            <motion.div
              className="h-4 w-3/4 bg-gradient-to-r from-neutral-200 via-neutral-100 to-neutral-200 dark:from-neutral-700 dark:via-neutral-600 dark:to-neutral-700 bg-[length:200%_100%] rounded"
              variants={shimmerVariants}
              animate="shimmer"
            />
            {/* Shorter line */}
            <motion.div
              className="h-4 w-1/2 bg-gradient-to-r from-neutral-200 via-neutral-100 to-neutral-200 dark:from-neutral-700 dark:via-neutral-600 dark:to-neutral-700 bg-[length:200%_100%] rounded"
              variants={shimmerVariants}
              animate="shimmer"
            />
            {/* Avatar skeleton */}
            <div className="flex items-center gap-3 mt-4">
              <motion.div
                className="w-10 h-10 bg-gradient-to-r from-neutral-200 via-neutral-100 to-neutral-200 dark:from-neutral-700 dark:via-neutral-600 dark:to-neutral-700 bg-[length:200%_100%] rounded-full"
                variants={shimmerVariants}
                animate="shimmer"
              />
              <div className="flex-1 space-y-2">
                <motion.div
                  className="h-3 w-24 bg-gradient-to-r from-neutral-200 via-neutral-100 to-neutral-200 dark:from-neutral-700 dark:via-neutral-600 dark:to-neutral-700 bg-[length:200%_100%] rounded"
                  variants={shimmerVariants}
                  animate="shimmer"
                />
                <motion.div
                  className="h-3 w-16 bg-gradient-to-r from-neutral-200 via-neutral-100 to-neutral-200 dark:from-neutral-700 dark:via-neutral-600 dark:to-neutral-700 bg-[length:200%_100%] rounded"
                  variants={shimmerVariants}
                  animate="shimmer"
                />
              </div>
            </div>
          </div>
          <p className="text-xs text-neutral-10 mt-4">shimmerVariants</p>
        </div>

        {/* Skeleton Pulse */}
        <div className="p-4 border border-neutral-6 rounded-lg">
          <h4 className="font-medium text-neutral-12 mb-3">Skeleton Pulse</h4>
          <p className="text-sm text-neutral-10 mb-4">
            Simple opacity pulsing for loading states.
          </p>
          <div className="space-y-3">
            {/* Card skeleton */}
            <motion.div
              className="p-4 bg-neutral-4 rounded-lg"
              variants={skeletonVariants}
              animate="pulse"
            >
              <div className="h-4 w-3/4 bg-neutral-4 rounded mb-2" />
              <div className="h-4 w-1/2 bg-neutral-4 rounded mb-4" />
              <div className="h-20 bg-neutral-4 rounded" />
            </motion.div>
          </div>
          <p className="text-xs text-neutral-10 mt-4">skeletonVariants</p>
        </div>

        {/* Table Skeleton */}
        <div className="p-4 border border-neutral-6 rounded-lg col-span-2">
          <h4 className="font-medium text-neutral-12 mb-3">Table Loading</h4>
          <p className="text-sm text-neutral-10 mb-4">
            Row placeholders with shimmer effect.
          </p>
          <div className="border border-neutral-6 rounded-lg overflow-hidden">
            {/* Header */}
            <div className="flex items-center gap-4 p-3 bg-neutral-2 border-b border-neutral-6">
              <div className="w-8 h-4 bg-neutral-4 rounded" />
              <div className="flex-1 h-4 bg-neutral-4 rounded" />
              <div className="w-24 h-4 bg-neutral-4 rounded" />
              <div className="w-20 h-4 bg-neutral-4 rounded" />
            </div>
            {/* Rows with shimmer */}
            {[1, 2, 3].map((i) => (
              <motion.div
                key={i}
                className="flex items-center gap-4 p-3 border-b border-neutral-6 last:border-b-0 bg-gradient-to-r from-neutral-50 via-white to-neutral-50 dark:from-neutral-800 dark:via-neutral-750 dark:to-neutral-800 bg-[length:200%_100%]"
                variants={shimmerVariants}
                animate="shimmer"
              >
                <div className="w-8 h-4 bg-neutral-4 rounded" />
                <div className="flex-1 h-4 bg-neutral-4 rounded" />
                <div className="w-24 h-4 bg-neutral-4 rounded" />
                <div className="w-20 h-4 bg-neutral-4 rounded" />
              </motion.div>
            ))}
          </div>
          <p className="text-xs text-neutral-10 mt-4">shimmerVariants on table rows</p>
        </div>
      </div>

      <div className="bg-neutral-2 border border-neutral-6 rounded-lg p-4 font-mono text-xs">
        <p className="text-neutral-10 mb-2">{"// Usage example"}</p>
        <p className="text-neutral-12">{"<motion.div"}</p>
        <p className="text-neutral-12 pl-4">{"className=\"bg-gradient-to-r from-neutral-3 via-neutral-2 to-neutral-3 bg-[length:200%_100%]\""}</p>
        <p className="text-neutral-12 pl-4">{"variants={shimmerVariants}"}</p>
        <p className="text-neutral-12 pl-4">{"animate=\"shimmer\""}</p>
        <p className="text-neutral-12">{"/>"}</p>
      </div>
    </div>
  );
}

// =============================================================================
// Reduced Motion Support
// =============================================================================

function ReducedMotionSupport() {
  return (
    <div className="space-y-6 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">Reduced Motion Support</h2>
        <p className="text-neutral-11">
          Accessibility support for users who prefer reduced motion.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="p-4 border border-neutral-6 rounded-lg">
          <h4 className="font-medium text-neutral-12 mb-2">OS Detection</h4>
          <p className="text-sm text-neutral-11 mb-4">
            Motion's <code className="bg-neutral-4 px-1 rounded">useReducedMotion()</code> hook
            detects the user's OS preference automatically.
          </p>
          <div className="bg-neutral-2 p-3 rounded font-mono text-xs">
            <p className="text-neutral-10">{"// Hook usage"}</p>
            <p className="text-neutral-12">{"const prefersReduced = useReducedMotion();"}</p>
          </div>
        </div>

        <div className="p-4 border border-neutral-6 rounded-lg">
          <h4 className="font-medium text-neutral-12 mb-2">useMotionSafe Hook</h4>
          <p className="text-sm text-neutral-11 mb-4">
            Our custom hook automatically falls back to opacity-only animations.
          </p>
          <div className="bg-neutral-2 p-3 rounded font-mono text-xs">
            <p className="text-neutral-10">{"// Import and use"}</p>
            <p className="text-neutral-12">{"const motionProps = useMotionSafe(ANIMATION_PRESETS.slideUp);"}</p>
          </div>
        </div>
      </div>

      <div className="bg-warning-2 border border-warning-6 rounded-lg p-4">
        <h4 className="font-medium text-warning-11 mb-1">Accessibility Note</h4>
        <p className="text-sm text-warning-11">
          When reduced motion is enabled, all animations fall back to simple opacity transitions
          with a fast duration (150ms). This respects user preferences while maintaining
          visual feedback.
        </p>
      </div>

      <div className="bg-neutral-2 border border-neutral-6 rounded-lg p-4 font-mono text-xs">
        <p className="text-neutral-10 mb-2">{"/* CSS fallback for reduced motion */"}</p>
        <p className="text-neutral-12">{"@media (prefers-reduced-motion: reduce) {"}</p>
        <p className="text-neutral-12 pl-4">{"*, *::before, *::after {"}</p>
        <p className="text-neutral-12 pl-8">{"animation-duration: 0.01ms !important;"}</p>
        <p className="text-neutral-12 pl-8">{"transition-duration: 0.01ms !important;"}</p>
        <p className="text-neutral-12 pl-4">{"}"}</p>
        <p className="text-neutral-12">{"}"}</p>
      </div>
    </div>
  );
}

// =============================================================================
// Meta & Stories
// =============================================================================

const meta: Meta = {
  title: "Design System/Animations",
  tags: ["autodocs"],
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "Animation system using Motion. Includes duration tokens, spring physics, easing curves, and reusable micro-interaction variants.",
      },
    },
  },
};

export default meta;
type Story = StoryObj;

export const Durations: Story = {
  render: () => <DurationTokens />,
  parameters: {
    docs: {
      description: {
        story: "Standardized duration tokens from instant (100ms) to slower (500ms).",
      },
    },
  },
};

export const Springs: Story = {
  render: () => <SpringPhysics />,
  parameters: {
    docs: {
      description: {
        story: "Physics-based spring configurations for natural motion.",
      },
    },
  },
};

export const Easings: Story = {
  render: () => <EasingFunctions />,
  parameters: {
    docs: {
      description: {
        story: "Cubic-bezier easing functions for non-spring animations.",
      },
    },
  },
};

export const Presets: Story = {
  render: () => <AnimationPresets />,
  parameters: {
    docs: {
      description: {
        story: "Ready-to-use animation configurations (fade, slide, scale, expand).",
      },
    },
  },
};

export const Interactions: Story = {
  render: () => <MicroInteractions />,
  parameters: {
    docs: {
      description: {
        story: "Reusable Motion variants for buttons, lists, toasts, modals, and more.",
      },
    },
  },
};

export const Loading: Story = {
  render: () => <LoadingStates />,
  parameters: {
    docs: {
      description: {
        story: "Shimmer and skeleton animations for loading placeholders.",
      },
    },
  },
};

export const Accessibility: Story = {
  render: () => <ReducedMotionSupport />,
  parameters: {
    docs: {
      description: {
        story: "Reduced motion support for accessibility compliance.",
      },
    },
  },
};

// =============================================================================
// DevTools Animations Demo
// =============================================================================

import {
  logEntryVariants,
  networkRowVariants,
} from "../design-system/micro-interactions";

function DevToolsAnimations() {
  const [showLogs, setShowLogs] = useState(true);
  const [showNetwork, setShowNetwork] = useState(true);

  const mockLogs = [
    { id: "1", level: "info", message: "Server started on port 3000", service: "api" },
    { id: "2", level: "warning", message: "Rate limit approaching threshold", service: "gateway" },
    { id: "3", level: "error", message: "Database connection timeout", service: "db" },
    { id: "4", level: "info", message: "Request completed in 150ms", service: "api" },
  ];

  const mockNetwork = [
    { id: "1", method: "GET", url: "/api/users", status: 200, duration: "45ms" },
    { id: "2", method: "POST", url: "/api/sessions", status: 201, duration: "120ms" },
    { id: "3", method: "GET", url: "/api/metrics", status: 500, duration: "2500ms" },
    { id: "4", method: "DELETE", url: "/api/cache", status: 204, duration: "12ms" },
  ];

  const getLevelColor = (level: string) => {
    switch (level) {
      case "error": return "text-error-11 bg-error-3";
      case "warning": return "text-warning-11 bg-warning-3";
      case "info": return "text-primary-11 bg-primary-3";
      default: return "text-neutral-11 bg-neutral-4";
    }
  };

  const getStatusColor = (status: number) => {
    if (status >= 500) return "text-error-11";
    if (status >= 400) return "text-warning-11";
    if (status >= 200 && status < 300) return "text-success-11";
    return "text-neutral-11";
  };

  const getMethodColor = (method: string) => {
    switch (method) {
      case "GET": return "text-primary-11";
      case "POST": return "text-success-11";
      case "PUT": return "text-warning-11";
      case "DELETE": return "text-error-11";
      default: return "text-neutral-11";
    }
  };

  return (
    <div className="space-y-8 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">DevTools Animations</h2>
        <p className="text-neutral-11">
          Specialized animations for DevTools panels: log entries and network requests.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Log Entries */}
        <div className="p-4 border border-neutral-6 rounded-lg">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-medium text-neutral-12">Log Entries</h4>
            <button
              onClick={() => setShowLogs(!showLogs)}
              className="px-3 py-1 text-sm bg-neutral-4 rounded hover:bg-neutral-4"
            >
              {showLogs ? "Reset" : "Show"}
            </button>
          </div>
          <p className="text-sm text-neutral-10 mb-4">
            Staggered fade-in with slide animation using logEntryVariants.
          </p>
          <div className="border border-neutral-6 rounded-lg overflow-hidden">
            <AnimatePresence>
              {showLogs && mockLogs.map((log, index) => (
                <motion.div
                  key={log.id}
                  className="flex items-center gap-3 p-2 border-b border-neutral-6 last:border-b-0"
                  variants={logEntryVariants}
                  initial="hidden"
                  animate="visible"
                  custom={index}
                >
                  <span className={`px-2 py-0.5 text-xs font-medium rounded uppercase ${getLevelColor(log.level)}`}>
                    {log.level}
                  </span>
                  <span className="text-xs text-neutral-10">{log.service}</span>
                  <span className="text-sm text-neutral-12 flex-1 truncate">{log.message}</span>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
          <p className="text-xs text-neutral-10 mt-2">logEntryVariants</p>
        </div>

        {/* Network Requests */}
        <div className="p-4 border border-neutral-6 rounded-lg">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-medium text-neutral-12">Network Requests</h4>
            <button
              onClick={() => setShowNetwork(!showNetwork)}
              className="px-3 py-1 text-sm bg-neutral-4 rounded hover:bg-neutral-4"
            >
              {showNetwork ? "Reset" : "Show"}
            </button>
          </div>
          <p className="text-sm text-neutral-10 mb-4">
            Table row animation with fade and subtle slide using networkRowVariants.
          </p>
          <div className="border border-neutral-6 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-neutral-2 text-neutral-10">
                <tr>
                  <th className="px-3 py-2 text-left">Method</th>
                  <th className="px-3 py-2 text-left">URL</th>
                  <th className="px-3 py-2 text-left">Status</th>
                  <th className="px-3 py-2 text-left">Time</th>
                </tr>
              </thead>
              <tbody>
                <AnimatePresence>
                  {showNetwork && mockNetwork.map((req, index) => (
                    <motion.tr
                      key={req.id}
                      className="border-t border-neutral-6"
                      variants={networkRowVariants}
                      initial="hidden"
                      animate="visible"
                      custom={index}
                    >
                      <td className={`px-3 py-2 font-medium ${getMethodColor(req.method)}`}>
                        {req.method}
                      </td>
                      <td className="px-3 py-2 text-neutral-12 font-mono text-xs">{req.url}</td>
                      <td className={`px-3 py-2 font-medium ${getStatusColor(req.status)}`}>
                        {req.status}
                      </td>
                      <td className="px-3 py-2 text-neutral-10">{req.duration}</td>
                    </motion.tr>
                  ))}
                </AnimatePresence>
              </tbody>
            </table>
          </div>
          <p className="text-xs text-neutral-10 mt-2">networkRowVariants</p>
        </div>
      </div>

      {/* Shimmer Loading for DevTools */}
      <div className="p-4 border border-neutral-6 rounded-lg">
        <h4 className="font-medium text-neutral-12 mb-4">DevTools Loading States</h4>
        <p className="text-sm text-neutral-10 mb-4">
          Shimmer skeletons for DevTools panels match the structure of actual content.
        </p>

        <div className="grid grid-cols-2 gap-4">
          {/* Log skeleton */}
          <div className="border border-neutral-6 rounded-lg overflow-hidden">
            <div className="bg-neutral-2 px-3 py-2 text-sm text-neutral-10">Logs Loading</div>
            <div className="p-3 space-y-2">
              {[1, 2, 3].map((i) => (
                <motion.div
                  key={i}
                  className="flex items-center gap-3"
                  variants={shimmerVariants}
                  animate="shimmer"
                >
                  <div className="h-5 w-14 bg-gradient-to-r from-neutral-200 via-neutral-100 to-neutral-200 dark:from-neutral-700 dark:via-neutral-600 dark:to-neutral-700 bg-[length:200%_100%] rounded" />
                  <div className="h-4 w-12 bg-gradient-to-r from-neutral-200 via-neutral-100 to-neutral-200 dark:from-neutral-700 dark:via-neutral-600 dark:to-neutral-700 bg-[length:200%_100%] rounded" />
                  <div className="h-4 flex-1 bg-gradient-to-r from-neutral-200 via-neutral-100 to-neutral-200 dark:from-neutral-700 dark:via-neutral-600 dark:to-neutral-700 bg-[length:200%_100%] rounded" />
                </motion.div>
              ))}
            </div>
          </div>

          {/* Network skeleton */}
          <div className="border border-neutral-6 rounded-lg overflow-hidden">
            <div className="bg-neutral-2 px-3 py-2 text-sm text-neutral-10">Network Loading</div>
            <div className="p-3 space-y-2">
              {[1, 2, 3].map((i) => (
                <motion.div
                  key={i}
                  className="h-8 bg-gradient-to-r from-neutral-200 via-neutral-100 to-neutral-200 dark:from-neutral-700 dark:via-neutral-600 dark:to-neutral-700 bg-[length:200%_100%] rounded"
                  variants={shimmerVariants}
                  animate="shimmer"
                />
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="bg-neutral-2 border border-neutral-6 rounded-lg p-4 font-mono text-xs">
        <p className="text-neutral-10 mb-2">{`// DevTools row animation usage`}</p>
        <p className="text-neutral-12">{`<motion.div`}</p>
        <p className="text-neutral-12 pl-4">{`variants={logEntryVariants}`}</p>
        <p className="text-neutral-12 pl-4">{`initial="hidden"`}</p>
        <p className="text-neutral-12 pl-4">{`animate="visible"`}</p>
        <p className="text-neutral-12 pl-4">{`custom={index} // for stagger delay`}</p>
        <p className="text-neutral-12">{`/>`}</p>
      </div>
    </div>
  );
}

export const DevTools: Story = {
  render: () => <DevToolsAnimations />,
  parameters: {
    docs: {
      description: {
        story: "DevTools-specific animations for logs, network requests, and loading states.",
      },
    },
  },
};

// =============================================================================
// Panel & Status Transitions Demo
// =============================================================================

import { panelSlideVariants } from "../design-system/micro-interactions";

function PanelAndStatusTransitions() {
  const [showPanel, setShowPanel] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<"disconnected" | "connecting" | "connected" | "error">("disconnected");

  const statusColors = {
    disconnected: "bg-neutral-4",
    connecting: "bg-warning-9 animate-pulse",
    connected: "bg-success-9",
    error: "bg-error-9",
  };

  const statusLabels = {
    disconnected: "Disconnected",
    connecting: "Connecting...",
    connected: "Connected",
    error: "Error",
  };

  const cycleStatus = () => {
    const states: Array<typeof connectionStatus> = ["disconnected", "connecting", "connected", "error"];
    const currentIndex = states.indexOf(connectionStatus);
    setConnectionStatus(states[(currentIndex + 1) % states.length]);
  };

  return (
    <div className="space-y-8 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">Panel & Status Transitions</h2>
        <p className="text-neutral-11">
          Animations for sliding panels and connection status indicators.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Panel Slide */}
        <div className="p-4 border border-neutral-6 rounded-lg">
          <h4 className="font-medium text-neutral-12 mb-3">Panel Slide Animation</h4>
          <p className="text-sm text-neutral-10 mb-4">
            Used in TraceCanvas control panel and floating toolbars.
          </p>
          <button
            onClick={() => setShowPanel(!showPanel)}
            className="px-3 py-1.5 bg-primary-9 text-neutral-12 text-sm rounded hover:bg-primary-10"
          >
            {showPanel ? "Hide Panel" : "Show Panel"}
          </button>
          <div className="h-40 mt-4 bg-neutral-2 rounded-lg relative overflow-hidden">
            <AnimatePresence>
              {showPanel && (
                <motion.div
                  className="absolute top-3 right-3 bg-neutral-1 border border-neutral-6 rounded-lg shadow-lg p-4"
                  variants={panelSlideVariants}
                  initial="hidden"
                  animate="visible"
                  exit="hidden"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full bg-success-9" />
                      <span className="text-sm text-neutral-11">Connected</span>
                    </div>
                    <div className="text-sm text-neutral-10">5 spans | 12 events</div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          <p className="text-xs text-neutral-10 mt-2">panelSlideVariants</p>
        </div>

        {/* Connection Status */}
        <div className="p-4 border border-neutral-6 rounded-lg">
          <h4 className="font-medium text-neutral-12 mb-3">Connection Status Indicator</h4>
          <p className="text-sm text-neutral-10 mb-4">
            Animated status dots with pulse effect for connecting state.
          </p>
          <button
            onClick={cycleStatus}
            className="px-3 py-1.5 bg-neutral-4 text-neutral-12 text-sm rounded hover:bg-neutral-4"
          >
            Cycle Status
          </button>
          <div className="mt-4 p-4 bg-neutral-2 rounded-lg">
            <div className="flex items-center gap-3">
              <motion.span
                className={`h-3 w-3 rounded-full ${statusColors[connectionStatus]}`}
                initial={{ scale: 0.8 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
                key={connectionStatus}
              />
              <motion.span
                className="text-sm text-neutral-12"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                key={connectionStatus}
              >
                {statusLabels[connectionStatus]}
              </motion.span>
            </div>
          </div>
          <p className="text-xs text-neutral-10 mt-2">Spring animation on status change</p>
        </div>

        {/* Tab Switch Animation */}
        <div className="p-4 border border-neutral-6 rounded-lg col-span-2">
          <h4 className="font-medium text-neutral-12 mb-3">Tab Switch Animation</h4>
          <p className="text-sm text-neutral-10 mb-4">
            Smooth fade and slide when switching between DevTools tabs.
          </p>
          <TabSwitchDemo />
        </div>
      </div>

      <div className="bg-neutral-2 border border-neutral-6 rounded-lg p-4 font-mono text-xs">
        <p className="text-neutral-10 mb-2">{`// Panel slide usage`}</p>
        <p className="text-neutral-12">{`<Panel position="top-right">`}</p>
        <p className="text-neutral-12 pl-4">{`<motion.div`}</p>
        <p className="text-neutral-12 pl-8">{`variants={panelSlideVariants}`}</p>
        <p className="text-neutral-12 pl-8">{`initial="hidden"`}</p>
        <p className="text-neutral-12 pl-8">{`animate="visible"`}</p>
        <p className="text-neutral-12 pl-4">{`>`}</p>
        <p className="text-neutral-12 pl-8">{`Panel content...`}</p>
        <p className="text-neutral-12 pl-4">{`</motion.div>`}</p>
        <p className="text-neutral-12">{`</Panel>`}</p>
      </div>
    </div>
  );
}

function TabSwitchDemo() {
  const [activeTab, setActiveTab] = useState(0);
  const tabs = ["Console", "Network", "State", "Traces"];

  return (
    <div>
      <div className="flex border-b border-neutral-6">
        {tabs.map((tab, index) => (
          <button
            key={tab}
            onClick={() => setActiveTab(index)}
            className={`px-4 py-2 text-sm relative ${
              activeTab === index
                ? "text-primary-11"
                : "text-neutral-10 hover:text-neutral-12"
            }`}
          >
            {tab}
            {activeTab === index && (
              <motion.div
                className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary-9"
                layoutId="activeTab"
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              />
            )}
          </button>
        ))}
      </div>
      <div className="h-32 bg-neutral-2 rounded-b-lg overflow-hidden">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.15 }}
            className="p-4"
          >
            <p className="text-neutral-11">{tabs[activeTab]} tab content</p>
            <p className="text-sm text-neutral-10 mt-2">
              Tab switch uses layoutId for indicator and fade for content.
            </p>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

export const PanelTransitions: Story = {
  render: () => <PanelAndStatusTransitions />,
  parameters: {
    docs: {
      description: {
        story: "Panel slide animations, connection status indicators, and tab switch transitions.",
      },
    },
  },
};

// =============================================================================
// Reduced Motion Demo
// =============================================================================

function ReducedMotionDemo() {
  const [showAccordion, setShowAccordion] = useState(false);
  const [simulateReducedMotion, setSimulateReducedMotion] = useState(false);

  // In a real app, this would use useReducedMotion() from motion/react
  // Here we simulate it with a toggle for demonstration

  return (
    <div className="space-y-8 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">Reduced Motion Accessibility</h2>
        <p className="text-neutral-11">
          Demonstrating WCAG 2.2 AA compliance with reduced motion support.
          Toggle the simulation to see how animations change.
        </p>
      </div>

      {/* Control Panel */}
      <div className="p-4 bg-warning-2 border border-warning-6 rounded-lg">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={simulateReducedMotion}
            onChange={(e) => setSimulateReducedMotion(e.target.checked)}
            className="w-5 h-5 accent-primary-9"
          />
          <div>
            <span className="font-medium text-warning-11">Simulate prefers-reduced-motion</span>
            <p className="text-sm text-warning-10">
              When enabled, animations are disabled or simplified to opacity-only transitions.
            </p>
          </div>
        </label>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Card Hover Animation */}
        <div className="space-y-3">
          <h4 className="font-medium text-neutral-12">Card Hover Animation</h4>
          <p className="text-sm text-neutral-10">
            {simulateReducedMotion
              ? "Hover is disabled - no visual motion."
              : "Hover to see lift and shadow effect."}
          </p>
          <motion.div
            className="p-4 bg-neutral-1 border border-neutral-6 rounded-lg cursor-pointer"
            variants={simulateReducedMotion ? undefined : cardHoverVariants}
            initial={simulateReducedMotion ? undefined : "rest"}
            whileHover={simulateReducedMotion ? undefined : "hover"}
          >
            <p className="text-neutral-12 font-medium">Interactive Card</p>
            <p className="text-sm text-neutral-10">Hover over me</p>
          </motion.div>
        </div>

        {/* Accordion Animation */}
        <div className="space-y-3">
          <h4 className="font-medium text-neutral-12">Accordion Animation</h4>
          <p className="text-sm text-neutral-10">
            {simulateReducedMotion
              ? "Content appears instantly."
              : "Content animates in with height transition."}
          </p>
          <button
            onClick={() => setShowAccordion(!showAccordion)}
            className="px-3 py-1.5 bg-primary-9 text-neutral-12 text-sm rounded hover:bg-primary-10"
          >
            {showAccordion ? "Collapse" : "Expand"}
          </button>
          <AnimatePresence>
            {showAccordion && (
              <motion.div
                className="overflow-hidden"
                variants={simulateReducedMotion ? undefined : accordionVariants}
                initial={simulateReducedMotion ? { opacity: 0 } : "collapsed"}
                animate={simulateReducedMotion ? { opacity: 1 } : "expanded"}
                exit={simulateReducedMotion ? { opacity: 0 } : "collapsed"}
                transition={simulateReducedMotion ? { duration: 0 } : undefined}
              >
                <div className="p-4 bg-neutral-2 rounded-lg mt-2">
                  <p className="text-neutral-11">
                    This content expands with a height animation normally,
                    but appears instantly with reduced motion.
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Spring vs Instant */}
        <div className="space-y-3 col-span-2">
          <h4 className="font-medium text-neutral-12">Spring vs Instant Transition</h4>
          <p className="text-sm text-neutral-10">
            Click the button to toggle the box position and observe the difference.
          </p>
          <BoxTransitionDemo simulateReducedMotion={simulateReducedMotion} />
        </div>
      </div>

      {/* Implementation Guide */}
      <div className="bg-neutral-2 border border-neutral-6 rounded-lg p-4">
        <h4 className="font-medium text-neutral-12 mb-3">Implementation Pattern</h4>
        <pre className="text-xs font-mono text-neutral-11 overflow-x-auto">
{`import { useReducedMotion } from "motion/react";

function AnimatedComponent() {
  const prefersReducedMotion = useReducedMotion();

  return (
    <motion.div
      variants={prefersReducedMotion ? undefined : springVariants}
      initial={prefersReducedMotion ? { opacity: 0 } : "hidden"}
      animate={prefersReducedMotion ? { opacity: 1 } : "visible"}
      transition={prefersReducedMotion ? { duration: 0.1 } : undefined}
    >
      Content
    </motion.div>
  );
}`}
        </pre>
      </div>

      {/* Compliance Checklist */}
      <div className="bg-success-2 border border-success-6 rounded-lg p-4">
        <h4 className="font-medium text-success-11 mb-3">WCAG 2.2 AA Compliance Checklist</h4>
        <ul className="space-y-2 text-sm text-success-11">
          <li className="flex items-center gap-2">
            <span className="text-success-9">✓</span>
            Use <code className="bg-success-3 px-1 rounded">useReducedMotion()</code> in all animated components
          </li>
          <li className="flex items-center gap-2">
            <span className="text-success-9">✓</span>
            Disable variants, whileHover, whileTap when reduced motion is preferred
          </li>
          <li className="flex items-center gap-2">
            <span className="text-success-9">✓</span>
            Use simple opacity transitions instead of position/scale animations
          </li>
          <li className="flex items-center gap-2">
            <span className="text-success-9">✓</span>
            Keep transition duration under 200ms for essential transitions
          </li>
          <li className="flex items-center gap-2">
            <span className="text-success-9">✓</span>
            Ensure functionality works identically with or without motion
          </li>
        </ul>
      </div>
    </div>
  );
}

function BoxTransitionDemo({ simulateReducedMotion }: { simulateReducedMotion: boolean }) {
  const [isRight, setIsRight] = useState(false);

  return (
    <div className="space-y-3">
      <button
        onClick={() => setIsRight(!isRight)}
        className="px-3 py-1.5 bg-neutral-4 text-neutral-12 text-sm rounded hover:bg-neutral-4"
      >
        Toggle Position
      </button>
      <div className="h-20 bg-neutral-2 rounded-lg relative">
        <motion.div
          className="absolute top-4 w-12 h-12 bg-primary-9 rounded-lg"
          animate={{
            left: isRight ? "calc(100% - 64px)" : "16px",
          }}
          transition={
            simulateReducedMotion
              ? { duration: 0 }
              : { type: "spring", stiffness: 300, damping: 25 }
          }
        />
      </div>
      <p className="text-xs text-neutral-10">
        {simulateReducedMotion
          ? "Position changes instantly (no motion)"
          : "Position animates with spring physics"}
      </p>
    </div>
  );
}

export const ReducedMotionAccessibility: Story = {
  render: () => <ReducedMotionDemo />,
  parameters: {
    docs: {
      description: {
        story: "Demonstrates WCAG 2.2 AA reduced motion compliance patterns. Toggle the simulation to see before/after comparison.",
      },
    },
  },
};
