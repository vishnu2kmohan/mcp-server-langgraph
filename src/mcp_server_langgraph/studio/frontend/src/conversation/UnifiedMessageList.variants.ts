/**
 * UnifiedMessageList CVA Variants
 *
 * Extracted to separate file for react-refresh compatibility.
 * These variants define the visual styling for message rows and bubbles.
 *
 * @see STYLE.md Section 2 (CVA Variants)
 * @see STYLE.md Section 4 (Radix colors)
 */
import { cva } from "class-variance-authority";

/**
 * Message row container variants
 */
export const messageRowVariants = cva(
  "group flex items-start gap-2 animate-in fade-in duration-300 motion-reduce:animate-none",
  {
    variants: {
      role: {
        user: "justify-end",
        assistant: "justify-start",
        system: "justify-start",
      },
    },
    defaultVariants: {
      role: "assistant",
    },
  },
);

/**
 * Message bubble variants (STYLE.md Section 4 - Radix colors)
 */
export const messageBubbleVariants = cva(
  "max-w-[70%] rounded-2xl px-4 py-3",
  {
    variants: {
      role: {
        user: "bg-primary-9 text-neutral-1 rounded-br-md",
        assistant:
          "bg-neutral-2 border border-neutral-6 text-neutral-12 rounded-bl-md",
        system:
          "bg-neutral-3 border border-neutral-6 text-neutral-11 italic rounded-bl-md",
      },
    },
    defaultVariants: {
      role: "assistant",
    },
  },
);
