/**
 * Persona Slice
 *
 * Manages user persona and role-based access control state.
 * Supports 8 sub-persona variants for fine-grained RBAC.
 */

import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import {
  PERSONA_VISIBLE_MODULES,
  PERSONA_DEFAULT_VIEW,
  type ModuleId,
} from "../../persona/PersonaVariants";

export type Persona = "admin" | "developer" | "user";

// 8 sub-persona variants
export type SubPersona =
  | "admin"
  | "security-admin"
  | "auditor"
  | "alice-builder"
  | "alice-analyst"
  | "alice-devops"
  | "compliance-officer"
  | "bob";

// Maps sub-persona to base persona
const SUB_PERSONA_TO_BASE: Record<SubPersona, Persona> = {
  admin: "admin",
  "security-admin": "admin",
  auditor: "admin",
  "alice-builder": "developer",
  "alice-analyst": "developer",
  "alice-devops": "developer",
  "compliance-officer": "developer",
  bob: "user",
};

interface PersonaConfig {
  defaultRoute: string;
  sidebarItems: string[];
  allowedRoutePatterns: string[];
}

const PERSONA_CONFIGS: Record<Persona, PersonaConfig> = {
  admin: {
    // Default to chat-first experience
    defaultRoute: "/studio/chat",
    sidebarItems: [
      "projects",
      "chat",
      "workflows",
      "mcp",
      "agents",
      "vectors",
      "observability",
      "files",
      "traces",
      "cost",
      "settings",
      "admin",
      "audit-logs",
      "help",
    ],
    // Admin has access to all routes
    allowedRoutePatterns: ["/admin/", "/studio/"],
  },
  developer: {
    // Default to chat-first experience
    defaultRoute: "/studio/chat",
    sidebarItems: [
      "projects",
      "chat",
      "workflows",
      "mcp",
      "agents",
      "vectors",
      "observability",
      "files",
      "traces",
      "cost",
      "settings",
      "help",
    ],
    // Developer has access to all studio routes
    allowedRoutePatterns: ["/studio/"],
  },
  user: {
    // Default to chat-first experience
    defaultRoute: "/studio/chat",
    // Expanded access for standard users (AI-native UX improvement)
    // Improves Adoption (HEART) by giving Bob access to:
    // - workflows: Unified view of owned workflows + shared workflows (read-only)
    // - cost: Basic cost tracking for transparency
    sidebarItems: ["projects", "chat", "workflows", "cost", "help"],
    // User has limited access
    allowedRoutePatterns: [
      "/studio/projects",
      "/studio/chat",
      "/studio/workflows",
      "/studio/cost",
    ],
  },
};

interface PersonaState {
  persona: Persona;
  subPersona: SubPersona | null;
  username: string | null;
  email: string | null;
  permissions: string[];
  isPersonaLoading: boolean;
}

export const initialState: PersonaState = {
  persona: "user",
  subPersona: null,
  username: null,
  email: null,
  permissions: [],
  // Start with loading=true so PersonaGuard waits for /api/v1/me response
  isPersonaLoading: true,
};

/**
 * Derive persona from user roles.
 * Priority: admin > developer > user
 */
function derivePersona(roles: string[]): Persona {
  if (roles.includes("admin")) {
    return "admin";
  }
  if (roles.includes("developer")) {
    return "developer";
  }
  return "user";
}

export const personaSlice = createSlice({
  name: "persona",
  initialState,
  reducers: {
    setPersona: (state, action: PayloadAction<Persona>) => {
      state.persona = action.payload;
    },
    setSubPersona: (state, action: PayloadAction<SubPersona>) => {
      state.subPersona = action.payload;
      // Derive base persona from sub-persona
      state.persona = SUB_PERSONA_TO_BASE[action.payload];
    },
    setUserInfo: (
      state,
      action: PayloadAction<{
        username: string;
        email?: string | null;
        roles: string[];
        persona?: Persona;
      }>,
    ) => {
      state.username = action.payload.username;
      state.email = action.payload.email ?? null;
      // Use provided persona from API, or derive from roles as fallback
      state.persona =
        action.payload.persona ?? derivePersona(action.payload.roles);
      state.isPersonaLoading = false;
    },
    setPermissions: (state, action: PayloadAction<string[]>) => {
      state.permissions = action.payload;
    },
    setPersonaLoading: (state, action: PayloadAction<boolean>) => {
      state.isPersonaLoading = action.payload;
    },
    resetPersona: () => initialState,
  },
});

export const {
  setPersona,
  setSubPersona,
  setUserInfo,
  setPermissions,
  setPersonaLoading,
  resetPersona,
} = personaSlice.actions;

// Selectors
type PersonaRootState = { persona: PersonaState };

export const selectPersona = (state: PersonaRootState) => state.persona.persona;
export const selectSubPersona = (state: PersonaRootState) =>
  state.persona.subPersona;
export const selectUsername = (state: PersonaRootState) =>
  state.persona.username;
export const selectEmail = (state: PersonaRootState) => state.persona.email;
export const selectPermissions = (state: PersonaRootState) =>
  state.persona.permissions;
export const selectPersonaLoading = (state: PersonaRootState) =>
  state.persona.isPersonaLoading;

export const selectSidebarItems = (state: PersonaRootState) => {
  const persona = state.persona.persona;
  return PERSONA_CONFIGS[persona].sidebarItems;
};

export const selectDefaultRoute = (state: PersonaRootState) => {
  const { persona, subPersona } = state.persona;
  // Use sub-persona config if available
  if (subPersona && PERSONA_DEFAULT_VIEW[subPersona]) {
    return PERSONA_DEFAULT_VIEW[subPersona];
  }
  return PERSONA_CONFIGS[persona].defaultRoute;
};

export const selectVisibleModules = (state: PersonaRootState): ModuleId[] => {
  const { subPersona, persona } = state.persona;
  // Use sub-persona modules if available
  if (subPersona && PERSONA_VISIBLE_MODULES[subPersona]) {
    return PERSONA_VISIBLE_MODULES[subPersona];
  }
  // Fallback to base persona sidebar items (converted to ModuleIds)
  const sidebarItems = PERSONA_CONFIGS[persona].sidebarItems;
  return sidebarItems as ModuleId[];
};

export const selectCanAccessRoute =
  (route: string) => (state: PersonaRootState) => {
    const persona = state.persona.persona;
    const config = PERSONA_CONFIGS[persona];

    if (persona === "admin") {
      return true;
    }

    return config.allowedRoutePatterns.some((pattern) =>
      route.startsWith(pattern),
    );
  };

export const selectHasPermission =
  (permission: string) => (state: PersonaRootState) => {
    const { persona, permissions } = state.persona;

    if (persona === "admin") {
      return true;
    }

    return permissions.includes(permission);
  };

export default personaSlice.reducer;
