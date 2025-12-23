/**
 * Lazy AI Components
 *
 * Code-split versions of AI components for reduced initial bundle size.
 * These components are loaded on-demand when first rendered.
 *
 * Usage:
 * ```tsx
 * import { LazyAICommandPalette } from "../ai/lazy";
 * import { Suspense } from "react";
 *
 * <Suspense fallback={<div>Loading...</div>}>
 *   <LazyAICommandPalette {...props} />
 * </Suspense>
 * ```
 *
 * Benefits:
 * - Reduces initial bundle size by ~50-100KB
 * - AI components loaded only when feature flags enable them
 * - Faster initial page load for users who don't use AI features
 */

import { lazy } from "react";

/**
 * Lazy-loaded AICommandPalette component.
 * Only loaded when command palette (Cmd+K) is activated.
 */
export const LazyAICommandPalette = lazy(() =>
  import("./AICommandPalette").then((module) => ({
    default: module.AICommandPalette,
  })),
);

/**
 * Lazy-loaded BackgroundAgentPanel component.
 * Only loaded when background agents are running.
 */
export const LazyBackgroundAgentPanel = lazy(() =>
  import("./BackgroundAgentPanel").then((module) => ({
    default: module.BackgroundAgentPanel,
  })),
);

/**
 * Lazy-loaded AgentTaskQueue component.
 * Only loaded when agent panel is toggled open.
 */
export const LazyAgentTaskQueue = lazy(() =>
  import("./AgentTaskQueue").then((module) => ({
    default: module.AgentTaskQueue,
  })),
);

/**
 * Lazy-loaded AIEditOverlay component.
 * Only loaded when AI edit mode is activated in canvas.
 */
export const LazyAIEditOverlay = lazy(() =>
  import("./AIEditOverlay").then((module) => ({
    default: module.AIEditOverlay,
  })),
);

/**
 * Lazy-loaded InlineSuggestions component.
 * Only loaded when suggestions feature is enabled.
 */
export const LazyInlineSuggestions = lazy(() =>
  import("./InlineSuggestions").then((module) => ({
    default: module.InlineSuggestions,
  })),
);

// Re-export types that consumers need (types don't affect bundle size)
export type {
  Command,
  AIInterpretation,
  AICommandPaletteProps,
} from "./AICommandPalette";
export type {
  BackgroundAgent,
  AgentStatus,
  BackgroundAgentPanelProps,
} from "./BackgroundAgentPanel";
export type { AgentTaskQueueProps } from "./AgentTaskQueue";
export type {
  Selection,
  DiffLine,
  EditResult,
  EditRequest,
  AIEditOverlayProps,
} from "./AIEditOverlay";
export type { Suggestion, SuggestionType } from "./InlineSuggestions";
