/**
 * EmptyStateRegistry Tests
 *
 * Tests the persona-specific empty state configuration registry
 */

import { describe, it, expect } from "vitest";
import {
  getEmptyStateConfig,
  getSupportedContexts,
  getSupportedPersonas,
  hasPersonaConfig,
  type Persona,
} from "./EmptyStateRegistry";
import type { EmptyStateContext } from "./EmptyState";

describe("EmptyStateRegistry", () => {
  describe("getEmptyStateConfig", () => {
    it("returns default config when persona is not specified", () => {
      const config = getEmptyStateConfig("sessions");

      expect(config).toBeDefined();
      expect(config.title).toBe("No sessions yet");
      expect(config.motivation).toContain("conversation");
      expect(config.action).toBe("Start Chat");
      expect(config.target).toBe("/studio/chat/new");
    });

    it("returns default config when persona is 'default'", () => {
      const config = getEmptyStateConfig("sessions", "default");

      expect(config.title).toBe("No sessions yet");
    });

    it("returns persona-specific config when available", () => {
      const adminConfig = getEmptyStateConfig("sessions", "admin");

      expect(adminConfig.motivation).toContain("Monitor team");
      expect(adminConfig.action).toBe("View Dashboard");
      expect(adminConfig.target).toBe("/studio/admin/dashboard");
    });

    it("merges persona overrides with default config", () => {
      const aliceConfig = getEmptyStateConfig("workflows", "alice-builder");

      // Should have persona override
      expect(aliceConfig.motivation).toContain("AI-powered nodes");
      expect(aliceConfig.ability).toContain("Drag-and-drop");

      // Should still have default title
      expect(aliceConfig.title).toBe("No workflows");
    });

    it("returns default config for personas without overrides", () => {
      const defaultConfig = getEmptyStateConfig("files");
      const bobConfig = getEmptyStateConfig("files", "bob");

      // No persona override for 'files' context for 'bob'
      expect(bobConfig.title).toBe(defaultConfig.title);
      expect(bobConfig.motivation).toBe(defaultConfig.motivation);
    });
  });

  describe("getSupportedContexts", () => {
    it("returns all 8 supported contexts", () => {
      const contexts = getSupportedContexts();

      expect(contexts).toHaveLength(8);
      expect(contexts).toContain("sessions");
      expect(contexts).toContain("projects");
      expect(contexts).toContain("workflows");
      expect(contexts).toContain("traces");
      expect(contexts).toContain("messages");
      expect(contexts).toContain("files");
      expect(contexts).toContain("alerts");
      expect(contexts).toContain("connections");
    });
  });

  describe("getSupportedPersonas", () => {
    it("returns all 9 personas including default", () => {
      const personas = getSupportedPersonas();

      expect(personas).toHaveLength(9);
      expect(personas).toContain("admin");
      expect(personas).toContain("security-admin");
      expect(personas).toContain("auditor");
      expect(personas).toContain("alice-builder");
      expect(personas).toContain("alice-analyst");
      expect(personas).toContain("alice-devops");
      expect(personas).toContain("compliance-officer");
      expect(personas).toContain("bob");
      expect(personas).toContain("default");
    });
  });

  describe("hasPersonaConfig", () => {
    it("returns true when persona has custom config", () => {
      expect(hasPersonaConfig("sessions", "admin")).toBe(true);
      expect(hasPersonaConfig("workflows", "alice-builder")).toBe(true);
      expect(hasPersonaConfig("alerts", "security-admin")).toBe(true);
    });

    it("returns false when persona has no custom config", () => {
      expect(hasPersonaConfig("files", "bob")).toBe(false);
      expect(hasPersonaConfig("messages", "admin")).toBe(false);
    });
  });

  describe("config completeness", () => {
    it("all contexts have required fields in default config", () => {
      const contexts = getSupportedContexts();

      contexts.forEach((context: EmptyStateContext) => {
        const config = getEmptyStateConfig(context);

        expect(config.title).toBeDefined();
        expect(config.title.length).toBeGreaterThan(0);
        expect(config.motivation).toBeDefined();
        expect(config.motivation.length).toBeGreaterThan(0);
        expect(config.action).toBeDefined();
        expect(config.action.length).toBeGreaterThan(0);
        expect(config.target).toBeDefined();
        expect(config.target.length).toBeGreaterThan(0);
      });
    });

    it("persona overrides maintain required fields", () => {
      const contexts = getSupportedContexts();
      const personas = getSupportedPersonas().filter((p) => p !== "default");

      contexts.forEach((context: EmptyStateContext) => {
        personas.forEach((persona: Persona) => {
          if (hasPersonaConfig(context, persona)) {
            const config = getEmptyStateConfig(context, persona);

            expect(config.title).toBeDefined();
            expect(config.motivation).toBeDefined();
            expect(config.action).toBeDefined();
            expect(config.target).toBeDefined();
          }
        });
      });
    });
  });

  describe("persona-specific behaviors", () => {
    describe("admin persona", () => {
      it("has dashboard-focused CTAs", () => {
        const sessionsConfig = getEmptyStateConfig("sessions", "admin");
        const workflowsConfig = getEmptyStateConfig("workflows", "admin");

        expect(sessionsConfig.target).toContain("/admin");
        expect(workflowsConfig.target).toContain("/admin");
      });
    });

    describe("bob persona", () => {
      it("has user-friendly messaging", () => {
        const sessionsConfig = getEmptyStateConfig("sessions", "bob");
        const workflowsConfig = getEmptyStateConfig("workflows", "bob");

        expect(sessionsConfig.motivation).toContain("explore");
        expect(workflowsConfig.motivation).toContain("shared");
      });
    });

    describe("alice-analyst persona", () => {
      it("has analytics-focused CTAs", () => {
        const workflowsConfig = getEmptyStateConfig(
          "workflows",
          "alice-analyst",
        );

        expect(workflowsConfig.action).toContain("Analytics");
        expect(workflowsConfig.target).toContain("observability");
      });
    });

    describe("compliance-officer persona", () => {
      it("has compliance-focused alerts", () => {
        const alertsConfig = getEmptyStateConfig(
          "alerts",
          "compliance-officer",
        );

        expect(alertsConfig.action).toContain("Compliance");
        expect(alertsConfig.target).toContain("compliance");
      });
    });
  });
});
