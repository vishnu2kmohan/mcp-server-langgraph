/**
 * Persona Store
 *
 * Zustand store for managing user persona and role-based access control.
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

export type Persona = 'admin' | 'developer' | 'user';

interface PersonaConfig {
  defaultRoute: string;
  sidebarItems: string[];
  allowedRoutePatterns: string[];
}

const PERSONA_CONFIGS: Record<Persona, PersonaConfig> = {
  admin: {
    defaultRoute: '/admin/dashboard',
    sidebarItems: ['dashboard', 'users', 'metrics', 'audit', 'orgs', 'studio'],
    allowedRoutePatterns: ['/admin/', '/studio/'],
  },
  developer: {
    defaultRoute: '/studio/workflows',
    sidebarItems: ['workflows', 'chat', 'mcp', 'observability', 'sessions'],
    allowedRoutePatterns: ['/studio/'],
  },
  user: {
    defaultRoute: '/studio/chat',
    sidebarItems: ['chat', 'sessions'],
    allowedRoutePatterns: ['/studio/chat', '/studio/sessions'],
  },
};

interface PersonaState {
  persona: Persona;
  permissions: string[];
  isPersonaLoading: boolean;

  // Actions
  setPersona: (persona: Persona) => void;
  setPermissions: (permissions: string[]) => void;
  detectPersona: (roles: string[]) => Promise<void>;

  // Selectors
  getDefaultRoute: () => string;
  getSidebarItems: () => string[];
  hasPermission: (permission: string) => boolean;
  canAccessRoute: (route: string) => boolean;

  // Reset
  reset: () => void;
}

const initialState = {
  persona: 'user' as Persona,
  permissions: [] as string[],
  isPersonaLoading: false,
};

export const usePersonaStore = create<PersonaState>()(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,

        setPersona: (persona: Persona) => {
          set({ persona }, false, 'setPersona');
        },

        setPermissions: (permissions: string[]) => {
          set({ permissions }, false, 'setPermissions');
        },

        detectPersona: async (roles: string[]) => {
          set({ isPersonaLoading: true }, false, 'detectPersona/start');

          // Priority: admin > developer > user
          let detectedPersona: Persona = 'user';

          if (roles.includes('admin')) {
            detectedPersona = 'admin';
          } else if (roles.includes('developer')) {
            detectedPersona = 'developer';
          }

          set(
            { persona: detectedPersona, isPersonaLoading: false },
            false,
            'detectPersona/complete'
          );
        },

        getDefaultRoute: () => {
          const { persona } = get();
          return PERSONA_CONFIGS[persona].defaultRoute;
        },

        getSidebarItems: () => {
          const { persona } = get();
          return PERSONA_CONFIGS[persona].sidebarItems;
        },

        hasPermission: (permission: string) => {
          const { persona, permissions } = get();

          // Admin has all permissions
          if (persona === 'admin') {
            return true;
          }

          return permissions.includes(permission);
        },

        canAccessRoute: (route: string) => {
          const { persona } = get();
          const config = PERSONA_CONFIGS[persona];

          // Admin can access everything
          if (persona === 'admin') {
            return true;
          }

          // Check if route matches any allowed pattern
          return config.allowedRoutePatterns.some((pattern) =>
            route.startsWith(pattern)
          );
        },

        reset: () => {
          set(initialState, false, 'reset');
        },
      }),
      {
        name: 'persona-storage',
        partialize: (state) => ({ persona: state.persona }),
      }
    ),
    { name: 'PersonaStore' }
  )
);
