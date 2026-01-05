/**
 * Orchestrator Mode Type Definitions
 *
 * Centralized types for orchestrator modes. Distinguishes between:
 * - UserOrchestratorMode: Modes selectable by users in the UI ("standard" | "swarm")
 * - OrchestratorMode: All modes including internal ones (studio, ux, alert)
 *
 * Reference: ADR-0090 Agent Orchestration Architecture
 *
 * @module types/orchestrator
 */

// =============================================================================
// User-Facing Orchestrator Modes
// =============================================================================

/**
 * Orchestrator modes available for user selection in the chat UI.
 * Limited to modes that users can meaningfully choose between.
 */
export type UserOrchestratorMode = "standard" | "swarm";

/**
 * Array of user-facing orchestrator modes for iteration and validation.
 */
export const USER_ORCHESTRATOR_MODES: readonly UserOrchestratorMode[] = [
  "standard",
  "swarm",
] as const;

// =============================================================================
// All Orchestrator Modes (Including Internal)
// =============================================================================

/**
 * All orchestrator modes, including internal modes used by the application.
 *
 * - standard: Default single-agent flow
 * - swarm: Parallel multi-agent execution (race/cascade/consensus)
 * - studio: Studio-specific agent configuration (internal)
 * - ux: UX-optimized response generation (internal)
 * - alert: Alert-triggered automated response (internal)
 */
export type OrchestratorMode = "standard" | "swarm" | "studio" | "ux" | "alert";

/**
 * Array of all orchestrator modes for iteration and validation.
 */
export const ORCHESTRATOR_MODES: readonly OrchestratorMode[] = [
  "standard",
  "swarm",
  "studio",
  "ux",
  "alert",
] as const;

// =============================================================================
// Mode Descriptions
// =============================================================================

/**
 * Human-readable descriptions for each orchestrator mode.
 * Used in UI tooltips, documentation, and accessibility labels.
 */
export const ORCHESTRATOR_MODE_DESCRIPTIONS: Record<OrchestratorMode, string> =
  {
    standard: "Default single-agent flow for straightforward tasks",
    swarm:
      "Parallel multi-agent execution with race, cascade, or consensus strategies",
    studio: "Studio-specific agent configuration for workflow building",
    ux: "UX-optimized response generation for enhanced user experience",
    alert: "Alert-triggered automated response for monitoring workflows",
  };

// =============================================================================
// Type Guards
// =============================================================================

/**
 * Type guard to check if a value is a valid UserOrchestratorMode.
 *
 * @param value - The value to check
 * @returns True if the value is a valid user-facing orchestrator mode
 */
export function isUserOrchestratorMode(
  value: unknown,
): value is UserOrchestratorMode {
  return (
    typeof value === "string" &&
    USER_ORCHESTRATOR_MODES.includes(value as UserOrchestratorMode)
  );
}

/**
 * Type guard to check if a value is a valid OrchestratorMode.
 *
 * @param value - The value to check
 * @returns True if the value is a valid orchestrator mode (user or internal)
 */
export function isOrchestratorMode(value: unknown): value is OrchestratorMode {
  return (
    typeof value === "string" &&
    ORCHESTRATOR_MODES.includes(value as OrchestratorMode)
  );
}

// =============================================================================
// Conversion Functions
// =============================================================================

/**
 * Converts any orchestrator mode to a user-facing mode.
 * Internal modes are converted to "standard" as the safe default.
 *
 * @param mode - The orchestrator mode to convert
 * @returns A valid UserOrchestratorMode
 */
export function toUserOrchestratorMode(mode: string): UserOrchestratorMode {
  if (isUserOrchestratorMode(mode)) {
    return mode;
  }
  return "standard";
}
