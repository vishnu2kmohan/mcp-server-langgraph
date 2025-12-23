/**
 * EmptyState Component Module
 *
 * A standardized empty state system implementing the Fogg Behavior Model
 * for consistent UX across the application.
 */

export {
  EmptyState,
  type EmptyStateProps,
  type EmptyStateContext,
  type EmptyStateVariant,
} from "./EmptyState";
export { default } from "./EmptyState";

// AI-Enhanced Empty State (Phase 6.2)
export { AIEmptyState, type AIEmptyStateProps } from "./AIEmptyState";

// Registry for persona-specific configurations
export {
  getEmptyStateConfig,
  getSupportedContexts,
  getSupportedPersonas,
  hasPersonaConfig,
  type Persona,
  type EmptyStateConfig,
} from "./EmptyStateRegistry";
