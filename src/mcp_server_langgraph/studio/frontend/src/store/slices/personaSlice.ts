/**
 * Persona Slice
 *
 * Manages user persona and role-based access control state.
 */

import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export type Persona = "admin" | "developer" | "user";

interface PersonaConfig {
  defaultRoute: string;
  sidebarItems: string[];
  allowedRoutePatterns: string[];
}

const PERSONA_CONFIGS: Record<Persona, PersonaConfig> = {
  admin: {
    defaultRoute: "/studio/projects",
    sidebarItems: [
      "projects",
      "chat",
      "workflows",
      "mcp",
      "agents",
      "vectors",
      "observability",
      "cost",
      "settings",
      "admin",
      "audit-logs",
    ],
    allowedRoutePatterns: ["/admin/", "/studio/"],
  },
  developer: {
    defaultRoute: "/studio/projects",
    sidebarItems: [
      "projects",
      "chat",
      "workflows",
      "mcp",
      "agents",
      "vectors",
      "observability",
      "cost",
      "settings",
    ],
    allowedRoutePatterns: ["/studio/"],
  },
  user: {
    defaultRoute: "/studio/projects",
    // Expanded access for standard users (AI-native UX improvement)
    // Improves Adoption (HEART) by giving Bob access to:
    // - workflows: Unified view of owned workflows + shared workflows (read-only)
    // - cost: Basic cost tracking for transparency
    sidebarItems: ["projects", "chat", "workflows", "cost"],
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
  username: string | null;
  email: string | null;
  permissions: string[];
  isPersonaLoading: boolean;
}

export const initialState: PersonaState = {
  persona: "user",
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
  setUserInfo,
  setPermissions,
  setPersonaLoading,
  resetPersona,
} = personaSlice.actions;

// Selectors
type PersonaRootState = { persona: PersonaState };

export const selectPersona = (state: PersonaRootState) => state.persona.persona;
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
  const persona = state.persona.persona;
  return PERSONA_CONFIGS[persona].defaultRoute;
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
