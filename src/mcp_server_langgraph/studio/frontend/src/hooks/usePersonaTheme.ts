/**
 * usePersonaTheme Hook
 *
 * Returns theme configuration for the current persona.
 * Used for consistent persona-specific styling across the application.
 *
 * @example
 * ```tsx
 * function PersonaBadge() {
 *   const theme = usePersonaTheme();
 *   return <span className={theme.badge}>Current Persona</span>;
 * }
 * ```
 */

import { useAppSelector } from "../store/hooks";
import { selectSubPersona } from "../store/slices/personaSlice";
import { getPersonaTheme, type PersonaTheme } from "../persona/PersonaVariants";

/**
 * Hook to get the current persona's theme configuration.
 *
 * @returns PersonaTheme with Tailwind classes for consistent styling
 */
export function usePersonaTheme(): PersonaTheme {
  const personaId = useAppSelector(selectSubPersona);
  return getPersonaTheme(personaId ?? "bob");
}

export default usePersonaTheme;
