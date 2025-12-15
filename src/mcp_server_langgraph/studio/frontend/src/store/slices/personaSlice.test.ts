/**
 * Persona Slice Tests (TDD)
 *
 * Tests for Redux persona state management.
 */

import { describe, it, expect } from "vitest";
import personaReducer, {
  setPersona,
  setUserInfo,
  setPermissions,
  setPersonaLoading,
  resetPersona,
  selectPersona,
  selectUsername,
  selectEmail,
  selectPermissions,
  selectPersonaLoading,
  selectSidebarItems,
  selectDefaultRoute,
  selectCanAccessRoute,
  initialState,
  type Persona,
} from "./personaSlice";

describe("personaSlice", () => {
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
      it("should return admin default route for admin", () => {
        const adminState = {
          persona: { ...mockState.persona, persona: "admin" as Persona },
        };
        expect(selectDefaultRoute(adminState)).toBe("/studio/projects");
      });

      it("should return developer default route for developer", () => {
        expect(selectDefaultRoute(mockState)).toBe("/studio/projects");
      });

      it("should return user default route for user", () => {
        const userState = {
          persona: { ...mockState.persona, persona: "user" as Persona },
        };
        expect(selectDefaultRoute(userState)).toBe("/studio/projects");
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
  });
});
