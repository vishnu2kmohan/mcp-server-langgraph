/**
 * Persona Slice Tests (TDD)
 *
 * Tests for Redux persona state management.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import personaReducer, {
  setPersona,
  setUserInfo,
  setPermissions,
  setPersonaLoading,
  resetPersona,
  setSubPersona,
  hydrateFromServer,
  selectPersona,
  selectSubPersona,
  selectUsername,
  selectEmail,
  selectPermissions,
  selectPersonaLoading,
  selectSidebarItems,
  selectDefaultRoute,
  selectCanAccessRoute,
  selectVisibleModules,
  selectHasPermission,
  selectFeatureFlags,
  selectFeatureFlag,
  selectApiVersion,
  initialState,
  type Persona,
  type SubPersona,
} from "./personaSlice";

describe("personaSlice", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("reducers", () => {
    it("should return the initial state", () => {
      expect(personaReducer(undefined, { type: "unknown" })).toEqual(
        initialState,
      );
    });

    it("should handle setPersona", () => {
      const actual = personaReducer(initialState, setPersona("admin"));
      expect(actual.persona).toBe("admin");
    });

    it("should handle setUserInfo", () => {
      const actual = personaReducer(
        initialState,
        setUserInfo({
          username: "alice",
          email: "alice@example.com",
          roles: ["developer"],
        }),
      );
      expect(actual.username).toBe("alice");
      expect(actual.email).toBe("alice@example.com");
      expect(actual.persona).toBe("developer");
      expect(actual.isPersonaLoading).toBe(false);
    });

    it("should detect admin persona from roles", () => {
      const actual = personaReducer(
        initialState,
        setUserInfo({
          username: "admin",
          email: "admin@example.com",
          roles: ["admin", "developer"],
        }),
      );
      expect(actual.persona).toBe("admin");
    });

    it("should detect developer persona from roles", () => {
      const actual = personaReducer(
        initialState,
        setUserInfo({
          username: "dev",
          roles: ["developer"],
        }),
      );
      expect(actual.persona).toBe("developer");
    });

    it("should default to user persona when no special roles", () => {
      const actual = personaReducer(
        initialState,
        setUserInfo({
          username: "bob",
          roles: [],
        }),
      );
      expect(actual.persona).toBe("user");
    });

    it("should handle setPermissions", () => {
      const permissions = ["read:projects", "write:projects"];
      const actual = personaReducer(initialState, setPermissions(permissions));
      expect(actual.permissions).toEqual(permissions);
    });

    it("should handle setPersonaLoading", () => {
      const actual = personaReducer(initialState, setPersonaLoading(true));
      expect(actual.isPersonaLoading).toBe(true);
    });

    it("should handle resetPersona", () => {
      const modifiedState = {
        ...initialState,
        persona: "admin" as Persona,
        username: "alice",
        email: "alice@example.com",
        permissions: ["read:all"],
        isPersonaLoading: true,
      };
      const actual = personaReducer(modifiedState, resetPersona());
      expect(actual).toEqual(initialState);
    });
  });

  describe("selectors", () => {
    const mockState = {
      persona: {
        persona: "developer" as Persona,
        username: "alice",
        email: "alice@example.com",
        permissions: ["read:projects"],
        isPersonaLoading: false,
      },
    };

    it("should select persona", () => {
      expect(selectPersona(mockState)).toBe("developer");
    });

    it("should select username", () => {
      expect(selectUsername(mockState)).toBe("alice");
    });

    it("should select email", () => {
      expect(selectEmail(mockState)).toBe("alice@example.com");
    });

    it("should select permissions", () => {
      expect(selectPermissions(mockState)).toEqual(["read:projects"]);
    });

    it("should select persona loading state", () => {
      expect(selectPersonaLoading(mockState)).toBe(false);
    });

    describe("selectSidebarItems", () => {
      it("should return all items for admin", () => {
        const adminState = {
          persona: { ...mockState.persona, persona: "admin" as Persona },
        };
        const items = selectSidebarItems(adminState);
        expect(items).toContain("admin");
        expect(items).toContain("workflows");
        expect(items).toContain("projects");
      });

      it("should return developer items for developer", () => {
        const items = selectSidebarItems(mockState);
        expect(items).toContain("workflows");
        expect(items).toContain("projects");
        expect(items).not.toContain("admin");
      });

      it("should return expanded items for user (AI-native UX)", () => {
        // Bob (standard user) has access to workflows (unified view) and basic cost
        // This improves Adoption (HEART) by reducing friction for free tier users
        // The unified workflows view shows owned workflows + shared workflows (read-only)
        const userState = {
          persona: { ...mockState.persona, persona: "user" as Persona },
        };
        const items = selectSidebarItems(userState);

        // Core items + expanded access
        expect(items).toContain("projects");
        expect(items).toContain("chat");
        expect(items).toContain("workflows"); // Unified view (owned + shared)
        expect(items).toContain("cost");

        // Still blocked from admin-only features
        expect(items).not.toContain("admin");
        expect(items).not.toContain("mcp");
        expect(items).not.toContain("agents");
        expect(items).not.toContain("audit-logs");
      });
    });

    describe("selectDefaultRoute", () => {
      it("should return admin default route for admin (v2 chat)", () => {
        const adminState = {
          persona: { ...mockState.persona, persona: "admin" as Persona },
        };
        expect(selectDefaultRoute(adminState)).toBe("/studio/chat");
      });

      it("should return developer default route for developer (v2 chat)", () => {
        expect(selectDefaultRoute(mockState)).toBe("/studio/chat");
      });

      it("should return user default route for user (v2 chat)", () => {
        const userState = {
          persona: { ...mockState.persona, persona: "user" as Persona },
        };
        expect(selectDefaultRoute(userState)).toBe("/studio/chat");
      });
    });

    describe("selectCanAccessRoute (expanded user access)", () => {
      it("should allow user to access workflows route (unified view)", () => {
        // Bob can access /studio/workflows - shows owned + shared (read-only) workflows
        const userState = {
          persona: { ...mockState.persona, persona: "user" as Persona },
        };
        const canAccess = selectCanAccessRoute("/studio/workflows")(userState);
        expect(canAccess).toBe(true);
      });

      it("should allow user to access cost route", () => {
        // Bob should be able to access basic cost view
        const userState = {
          persona: { ...mockState.persona, persona: "user" as Persona },
        };
        const canAccess = selectCanAccessRoute("/studio/cost")(userState);
        expect(canAccess).toBe(true);
      });

      it("should allow user to access projects route", () => {
        const userState = {
          persona: { ...mockState.persona, persona: "user" as Persona },
        };
        const canAccess = selectCanAccessRoute("/studio/projects")(userState);
        expect(canAccess).toBe(true);
      });

      it("should allow user to access chat route", () => {
        const userState = {
          persona: { ...mockState.persona, persona: "user" as Persona },
        };
        const canAccess = selectCanAccessRoute("/studio/chat")(userState);
        expect(canAccess).toBe(true);
      });

      it("should block user from admin routes", () => {
        const userState = {
          persona: { ...mockState.persona, persona: "user" as Persona },
        };
        const canAccess = selectCanAccessRoute("/admin/dashboard")(userState);
        expect(canAccess).toBe(false);
      });

      it("should block user from mcp routes", () => {
        const userState = {
          persona: { ...mockState.persona, persona: "user" as Persona },
        };
        const canAccess = selectCanAccessRoute("/studio/mcp")(userState);
        expect(canAccess).toBe(false);
      });

      it("should block user from agents routes", () => {
        const userState = {
          persona: { ...mockState.persona, persona: "user" as Persona },
        };
        const canAccess = selectCanAccessRoute("/studio/agents")(userState);
        expect(canAccess).toBe(false);
      });
    });

    describe("selectHasPermission", () => {
      it("should return true for admin regardless of permission", () => {
        const adminState = {
          persona: {
            ...mockState.persona,
            persona: "admin" as Persona,
            permissions: [],
          },
        };
        expect(selectHasPermission("any:permission")(adminState)).toBe(true);
      });

      it("should return true when user has the permission", () => {
        const state = {
          persona: {
            ...mockState.persona,
            persona: "developer" as Persona,
            permissions: ["read:projects", "write:projects"],
          },
        };
        expect(selectHasPermission("read:projects")(state)).toBe(true);
      });

      it("should return false when user lacks the permission", () => {
        const state = {
          persona: {
            ...mockState.persona,
            persona: "user" as Persona,
            permissions: ["read:projects"],
          },
        };
        expect(selectHasPermission("admin:manage")(state)).toBe(false);
      });
    });
  });

  // =============================================================================
  // Sub-Persona Tests (8 variants)
  // =============================================================================

  describe("sub-personas", () => {
    describe("setSubPersona reducer", () => {
      it("should set admin sub-persona", () => {
        const actual = personaReducer(initialState, setSubPersona("admin"));
        expect(actual.subPersona).toBe("admin");
        expect(actual.persona).toBe("admin");
      });

      it("should set security-admin sub-persona", () => {
        const actual = personaReducer(
          initialState,
          setSubPersona("security-admin"),
        );
        expect(actual.subPersona).toBe("security-admin");
        expect(actual.persona).toBe("admin");
      });

      it("should set auditor sub-persona", () => {
        const actual = personaReducer(initialState, setSubPersona("auditor"));
        expect(actual.subPersona).toBe("auditor");
        expect(actual.persona).toBe("admin");
      });

      it("should set alice-builder sub-persona", () => {
        const actual = personaReducer(
          initialState,
          setSubPersona("alice-builder"),
        );
        expect(actual.subPersona).toBe("alice-builder");
        expect(actual.persona).toBe("developer");
      });

      it("should set alice-analyst sub-persona", () => {
        const actual = personaReducer(
          initialState,
          setSubPersona("alice-analyst"),
        );
        expect(actual.subPersona).toBe("alice-analyst");
        expect(actual.persona).toBe("developer");
      });

      it("should set alice-devops sub-persona", () => {
        const actual = personaReducer(
          initialState,
          setSubPersona("alice-devops"),
        );
        expect(actual.subPersona).toBe("alice-devops");
        expect(actual.persona).toBe("developer");
      });

      it("should set compliance-officer sub-persona", () => {
        const actual = personaReducer(
          initialState,
          setSubPersona("compliance-officer"),
        );
        expect(actual.subPersona).toBe("compliance-officer");
        expect(actual.persona).toBe("developer");
      });

      it("should set bob sub-persona", () => {
        const actual = personaReducer(initialState, setSubPersona("bob"));
        expect(actual.subPersona).toBe("bob");
        expect(actual.persona).toBe("user");
      });
    });

    describe("selectSubPersona", () => {
      it("should return sub-persona from state", () => {
        const state = {
          persona: {
            ...initialState,
            subPersona: "alice-builder" as SubPersona,
            persona: "developer" as Persona,
          },
        };
        expect(selectSubPersona(state)).toBe("alice-builder");
      });
    });

    describe("selectVisibleModules", () => {
      it("should return all modules for admin", () => {
        const state = {
          persona: {
            ...initialState,
            subPersona: "admin" as SubPersona,
            persona: "admin" as Persona,
          },
        };
        const modules = selectVisibleModules(state);
        expect(modules).toContain("chat");
        expect(modules).toContain("admin");
        expect(modules).toContain("compliance");
        expect(modules).toContain("audit");
      });

      it("should return security-focused modules for security-admin", () => {
        const state = {
          persona: {
            ...initialState,
            subPersona: "security-admin" as SubPersona,
            persona: "admin" as Persona,
          },
        };
        const modules = selectVisibleModules(state);
        expect(modules).toContain("compliance");
        expect(modules).toContain("audit");
        expect(modules).toContain("admin");
      });

      it("should return audit modules for auditor", () => {
        const state = {
          persona: {
            ...initialState,
            subPersona: "auditor" as SubPersona,
            persona: "admin" as Persona,
          },
        };
        const modules = selectVisibleModules(state);
        expect(modules).toContain("audit");
        expect(modules).toContain("compliance");
        expect(modules).toContain("help");
        expect(modules).not.toContain("admin");
      });

      it("should return builder modules for alice-builder", () => {
        const state = {
          persona: {
            ...initialState,
            subPersona: "alice-builder" as SubPersona,
            persona: "developer" as Persona,
          },
        };
        const modules = selectVisibleModules(state);
        expect(modules).toContain("chat");
        expect(modules).toContain("workflows");
        expect(modules).toContain("agents");
        expect(modules).not.toContain("admin");
      });

      it("should return analyst modules for alice-analyst", () => {
        const state = {
          persona: {
            ...initialState,
            subPersona: "alice-analyst" as SubPersona,
            persona: "developer" as Persona,
          },
        };
        const modules = selectVisibleModules(state);
        expect(modules).toContain("chat");
        expect(modules).toContain("cost");
        expect(modules).toContain("observability");
      });

      it("should return devops modules for alice-devops", () => {
        const state = {
          persona: {
            ...initialState,
            subPersona: "alice-devops" as SubPersona,
            persona: "developer" as Persona,
          },
        };
        const modules = selectVisibleModules(state);
        expect(modules).toContain("chat");
        expect(modules).toContain("connections");
        expect(modules).toContain("observability");
      });

      it("should return compliance modules for compliance-officer", () => {
        const state = {
          persona: {
            ...initialState,
            subPersona: "compliance-officer" as SubPersona,
            persona: "developer" as Persona,
          },
        };
        const modules = selectVisibleModules(state);
        expect(modules).toContain("audit");
        expect(modules).toContain("compliance");
        expect(modules).not.toContain("admin");
      });

      it("should return limited modules for bob", () => {
        const state = {
          persona: {
            ...initialState,
            subPersona: "bob" as SubPersona,
            persona: "user" as Persona,
          },
        };
        const modules = selectVisibleModules(state);
        expect(modules).toContain("chat");
        expect(modules).toContain("projects");
        expect(modules).toContain("workflows");
        expect(modules).not.toContain("admin");
        expect(modules).not.toContain("mcp");
      });
    });

    describe("selectDefaultRoute with sub-personas", () => {
      it("should return admin default route for admin sub-persona", () => {
        const state = {
          persona: {
            ...initialState,
            subPersona: "admin" as SubPersona,
            persona: "admin" as Persona,
          },
        };
        expect(selectDefaultRoute(state)).toBe("/studio/admin");
      });

      it("should return compliance route for security-admin", () => {
        const state = {
          persona: {
            ...initialState,
            subPersona: "security-admin" as SubPersona,
            persona: "admin" as Persona,
          },
        };
        expect(selectDefaultRoute(state)).toBe("/studio/compliance");
      });

      it("should return audit route for auditor", () => {
        const state = {
          persona: {
            ...initialState,
            subPersona: "auditor" as SubPersona,
            persona: "admin" as Persona,
          },
        };
        expect(selectDefaultRoute(state)).toBe("/studio/audit");
      });

      it("should return chat route for alice-builder", () => {
        const state = {
          persona: {
            ...initialState,
            subPersona: "alice-builder" as SubPersona,
            persona: "developer" as Persona,
          },
        };
        expect(selectDefaultRoute(state)).toBe("/studio/chat");
      });

      it("should return observability route for alice-analyst", () => {
        const state = {
          persona: {
            ...initialState,
            subPersona: "alice-analyst" as SubPersona,
            persona: "developer" as Persona,
          },
        };
        expect(selectDefaultRoute(state)).toBe("/studio/observability");
      });

      it("should return connections route for alice-devops", () => {
        const state = {
          persona: {
            ...initialState,
            subPersona: "alice-devops" as SubPersona,
            persona: "developer" as Persona,
          },
        };
        expect(selectDefaultRoute(state)).toBe("/studio/connections");
      });

      it("should return compliance route for compliance-officer", () => {
        const state = {
          persona: {
            ...initialState,
            subPersona: "compliance-officer" as SubPersona,
            persona: "developer" as Persona,
          },
        };
        expect(selectDefaultRoute(state)).toBe("/studio/compliance");
      });

      it("should return chat route for bob", () => {
        const state = {
          persona: {
            ...initialState,
            subPersona: "bob" as SubPersona,
            persona: "user" as Persona,
          },
        };
        expect(selectDefaultRoute(state)).toBe("/studio/chat");
      });
    });
  });

  // =============================================================================
  // hydrateFromServer Tests (Sprint 4: Server-Provided Persona Data)
  // =============================================================================

  describe("hydrateFromServer", () => {
    it("should store visibleModules in state", () => {
      const serverModules = ["chat", "workflows", "agents", "cost"];
      const actual = personaReducer(
        initialState,
        hydrateFromServer({
          username: "alice",
          email: "alice@example.com",
          roles: ["developer"],
          persona: "developer",
          visibleModules: serverModules,
        }),
      );
      expect(actual.visibleModules).toEqual(serverModules);
    });

    it("should store featureFlags in state", () => {
      const serverFlags = { ai_suggestions: true, focus_mode: false };
      const actual = personaReducer(
        initialState,
        hydrateFromServer({
          username: "alice",
          roles: ["developer"],
          persona: "developer",
          featureFlags: serverFlags,
        }),
      );
      expect(actual.featureFlags).toEqual(serverFlags);
    });

    it("should store subPersona and apiVersion", () => {
      const actual = personaReducer(
        initialState,
        hydrateFromServer({
          username: "alice",
          roles: ["developer"],
          persona: "developer",
          subPersona: "alice-builder",
          apiVersion: "2",
        }),
      );
      expect(actual.subPersona).toBe("alice-builder");
      expect(actual.apiVersion).toBe("2");
    });

    it("should set isPersonaLoading to false after hydration", () => {
      const actual = personaReducer(
        { ...initialState, isPersonaLoading: true },
        hydrateFromServer({
          username: "alice",
          roles: ["developer"],
          persona: "developer",
        }),
      );
      expect(actual.isPersonaLoading).toBe(false);
    });

    it("should handle empty visibleModules gracefully", () => {
      const actual = personaReducer(
        initialState,
        hydrateFromServer({
          username: "alice",
          roles: ["developer"],
          persona: "developer",
          visibleModules: [],
        }),
      );
      expect(actual.visibleModules).toEqual([]);
    });

    it("should handle undefined optional fields", () => {
      const actual = personaReducer(
        initialState,
        hydrateFromServer({
          username: "alice",
          roles: ["developer"],
          persona: "developer",
          // subPersona, visibleModules, featureFlags, apiVersion all undefined
        }),
      );
      expect(actual.subPersona).toBeNull();
      expect(actual.visibleModules).toEqual([]);
      expect(actual.featureFlags).toEqual({});
      expect(actual.apiVersion).toBeNull();
    });
  });

  // =============================================================================
  // selectSidebarItems with Server-Provided Modules Tests
  // =============================================================================

  describe("selectSidebarItems with server modules", () => {
    it("should return server visibleModules when available", () => {
      const serverModules = ["chat", "workflows", "agents", "cost"];
      const state = {
        persona: {
          ...initialState,
          persona: "developer" as Persona,
          visibleModules: serverModules,
          isPersonaLoading: false,
        },
      };
      const items = selectSidebarItems(state);
      // Should return server modules (after filtering to known IDs)
      expect(items).toContain("chat");
      expect(items).toContain("workflows");
    });

    it("should filter server modules to known NAV_ITEM ids", () => {
      // Server returns some unknown module IDs - should be filtered out
      const serverModules = [
        "chat",
        "unknown_module",
        "workflows",
        "fake_module",
      ];
      const state = {
        persona: {
          ...initialState,
          persona: "developer" as Persona,
          visibleModules: serverModules,
          isPersonaLoading: false,
        },
      };
      const items = selectSidebarItems(state);
      // Should contain known modules
      expect(items).toContain("chat");
      expect(items).toContain("workflows");
      // Should NOT contain unknown modules
      expect(items).not.toContain("unknown_module");
      expect(items).not.toContain("fake_module");
    });

    it("should fall back to PERSONA_CONFIGS when visibleModules is empty", () => {
      const state = {
        persona: {
          ...initialState,
          persona: "developer" as Persona,
          visibleModules: [],
          isPersonaLoading: false,
        },
      };
      const items = selectSidebarItems(state);
      // Should fall back to hardcoded developer config
      expect(items).toContain("chat");
      expect(items).toContain("workflows");
      expect(items).not.toContain("admin"); // Developer doesn't have admin
    });

    it("should fall back to PERSONA_CONFIGS when all server modules are unknown", () => {
      const serverModules = ["unknown1", "unknown2", "unknown3"];
      const state = {
        persona: {
          ...initialState,
          persona: "admin" as Persona,
          visibleModules: serverModules,
          isPersonaLoading: false,
        },
      };
      const items = selectSidebarItems(state);
      // Should fall back to hardcoded admin config since all server modules are unknown
      expect(items).toContain("admin");
      expect(items).toContain("chat");
    });
  });

  // =============================================================================
  // Feature Flag Selectors Tests
  // =============================================================================

  describe("feature flag selectors", () => {
    describe("selectFeatureFlags", () => {
      it("should return feature flags from state", () => {
        const flags = { ai_suggestions: true, focus_mode: false };
        const state = {
          persona: {
            ...initialState,
            featureFlags: flags,
          },
        };
        expect(selectFeatureFlags(state)).toEqual(flags);
      });
    });

    describe("selectFeatureFlag", () => {
      it("should return true for enabled flag", () => {
        const state = {
          persona: {
            ...initialState,
            featureFlags: { ai_suggestions: true },
          },
        };
        expect(selectFeatureFlag("ai_suggestions")(state)).toBe(true);
      });

      it("should return false for disabled flag", () => {
        const state = {
          persona: {
            ...initialState,
            featureFlags: { ai_suggestions: false },
          },
        };
        expect(selectFeatureFlag("ai_suggestions")(state)).toBe(false);
      });

      it("should return false for unknown flag", () => {
        const state = {
          persona: {
            ...initialState,
            featureFlags: {},
          },
        };
        expect(selectFeatureFlag("unknown_flag")(state)).toBe(false);
      });
    });

    describe("selectApiVersion", () => {
      it("should return api version from state", () => {
        const state = {
          persona: {
            ...initialState,
            apiVersion: "2",
          },
        };
        expect(selectApiVersion(state)).toBe("2");
      });
    });
  });
});
