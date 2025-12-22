/**
 * Persona Module - Phase 2
 *
 * Persona management components and configurations.
 */

export {
  PersonaSwitcher,
  type Persona,
  type PersonaSwitcherProps,
} from "./PersonaSwitcher";
export {
  WorkspacePresets,
  type WorkspacePreset,
  type WorkspaceLayout,
  type WorkspacePresetsProps,
} from "./WorkspacePresets";
export {
  PERSONA_VARIANTS,
  PERSONA_OPENFGA_MAPPINGS,
  PERSONA_VISIBLE_MODULES,
  PERSONA_DEFAULT_VIEW,
  PERSONA_DEFAULT_PRESET,
  DEFAULT_PRESETS,
  getPersonaById,
  getPersonasByRole,
  getVisibleModules,
  getDefaultView,
  getDefaultPreset,
  type OpenFGATuple,
  type ModuleId,
} from "./PersonaVariants";
export {
  PersonaProvider,
  PersonaContext,
  usePersonaContext,
  useCanAccessModule,
  useDefaultRoute,
  type PersonaProviderProps,
  type PersonaContextValue,
} from "./PersonaContext";
export { PersonaRouter, type PersonaRouterProps } from "./PersonaRouter";
