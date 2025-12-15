/**
 * Store Exports
 *
 * Central export point for Redux store types and slices.
 *
 * Use Redux hooks (useAppDispatch, useAppSelector) from store/hooks.ts
 * to access store state and dispatch actions.
 */

// Re-export Persona type from Redux slice for compatibility
export type { Persona } from "../store/slices/personaSlice";
