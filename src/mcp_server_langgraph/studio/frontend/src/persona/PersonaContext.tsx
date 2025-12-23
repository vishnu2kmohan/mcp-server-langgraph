/**
 * PersonaContext
 *
 * React context that provides persona state to components
 * without requiring direct Redux access.
 *
 * Provides:
 * - Current persona and sub-persona
 * - Visible modules based on persona
 * - Helper functions for access control
 */
/* eslint-disable react-refresh/only-export-components -- Context files export both providers and hooks by design */
import { createContext, useContext, useMemo, type ReactNode } from "react";
import { useAppSelector } from "../store/hooks";
import {
  selectPersona,
  selectSubPersona,
  selectUsername,
  selectVisibleModules,
  selectDefaultRoute,
  type Persona,
  type SubPersona,
} from "../store/slices/personaSlice";
import type { ModuleId } from "./PersonaVariants";

// =============================================================================
// Types
// =============================================================================

export interface PersonaContextValue {
  /** Current base persona (admin, developer, user) */
  persona: Persona;
  /** Current sub-persona (8 variants) */
  subPersona: SubPersona | null;
  /** Current username */
  username: string | null;
  /** List of visible modules for current persona */
  visibleModules: ModuleId[];
  /** Default route for current persona */
  defaultRoute: string;
  /** Helper: is admin persona */
  isAdmin: boolean;
  /** Helper: is developer persona */
  isDeveloper: boolean;
  /** Helper: is user persona */
  isUser: boolean;
}

// =============================================================================
// Context
// =============================================================================

const PersonaContext = createContext<PersonaContextValue | null>(null);

// =============================================================================
// Provider
// =============================================================================

export interface PersonaProviderProps {
  children: ReactNode;
}

export function PersonaProvider({ children }: PersonaProviderProps) {
  const persona = useAppSelector(selectPersona);
  const subPersona = useAppSelector(selectSubPersona);
  const username = useAppSelector(selectUsername);
  const visibleModules = useAppSelector(selectVisibleModules);
  const defaultRoute = useAppSelector(selectDefaultRoute);

  const value = useMemo<PersonaContextValue>(
    () => ({
      persona,
      subPersona,
      username,
      visibleModules,
      defaultRoute,
      isAdmin: persona === "admin",
      isDeveloper: persona === "developer",
      isUser: persona === "user",
    }),
    [persona, subPersona, username, visibleModules, defaultRoute],
  );

  return (
    <PersonaContext.Provider value={value}>{children}</PersonaContext.Provider>
  );
}

// =============================================================================
// Hooks
// =============================================================================

/**
 * Access the full persona context
 */
export function usePersonaContext(): PersonaContextValue {
  const context = useContext(PersonaContext);
  if (!context) {
    throw new Error("usePersonaContext must be used within a PersonaProvider");
  }
  return context;
}

/**
 * Check if the current persona can access a specific module
 */
export function useCanAccessModule(moduleId: ModuleId): boolean {
  const { visibleModules } = usePersonaContext();
  return visibleModules.includes(moduleId);
}

/**
 * Get the default route for the current persona
 */
export function useDefaultRoute(): string {
  const { defaultRoute } = usePersonaContext();
  return defaultRoute;
}

// =============================================================================
// Exports
// =============================================================================

export { PersonaContext };
