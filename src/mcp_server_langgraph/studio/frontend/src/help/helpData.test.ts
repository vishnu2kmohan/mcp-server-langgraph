/**
 * Help Data Tests
 *
 * Tests for help page constants including topics and keyboard shortcuts.
 * Ensures data integrity and completeness.
 */
import { describe, it, expect } from "vitest";
import {
  DEFAULT_HELP_TOPICS,
  DEFAULT_SHORTCUT_CATEGORIES,
} from "./helpData";

describe("Help Data", () => {
  describe("DEFAULT_HELP_TOPICS", () => {
    it("should be an array with at least 8 topics", () => {
      expect(Array.isArray(DEFAULT_HELP_TOPICS)).toBe(true);
      expect(DEFAULT_HELP_TOPICS.length).toBeGreaterThanOrEqual(8);
    });

    it("should have required properties on each topic", () => {
      DEFAULT_HELP_TOPICS.forEach((topic) => {
        expect(topic).toHaveProperty("id");
        expect(topic).toHaveProperty("title");
        expect(topic).toHaveProperty("category");
        expect(topic).toHaveProperty("content");
        expect(topic).toHaveProperty("keywords");
      });
    });

    it("should have unique topic IDs", () => {
      const ids = DEFAULT_HELP_TOPICS.map((t) => t.id);
      const uniqueIds = new Set(ids);
      expect(uniqueIds.size).toBe(ids.length);
    });

    it("should include basics category topics", () => {
      const basicsTopics = DEFAULT_HELP_TOPICS.filter(
        (t) => t.category === "basics"
      );
      expect(basicsTopics.length).toBeGreaterThan(0);
    });

    it("should include productivity category topics", () => {
      const productivityTopics = DEFAULT_HELP_TOPICS.filter(
        (t) => t.category === "productivity"
      );
      expect(productivityTopics.length).toBeGreaterThan(0);
    });

    it("should include compliance category topics", () => {
      const complianceTopics = DEFAULT_HELP_TOPICS.filter(
        (t) => t.category === "compliance"
      );
      expect(complianceTopics.length).toBeGreaterThan(0);
    });

    it("should include advanced category topics for MCP", () => {
      const advancedTopics = DEFAULT_HELP_TOPICS.filter(
        (t) => t.category === "advanced"
      );
      expect(advancedTopics.length).toBeGreaterThan(0);

      // MCP topics should be in advanced
      const mcpTopics = advancedTopics.filter((t) => t.id.startsWith("mcp"));
      expect(mcpTopics.length).toBeGreaterThanOrEqual(3);
    });

    it("should have keywords as non-empty arrays", () => {
      DEFAULT_HELP_TOPICS.forEach((topic) => {
        expect(Array.isArray(topic.keywords)).toBe(true);
        expect(topic.keywords.length).toBeGreaterThan(0);
      });
    });
  });

  describe("DEFAULT_SHORTCUT_CATEGORIES", () => {
    it("should be an array with at least 5 categories", () => {
      expect(Array.isArray(DEFAULT_SHORTCUT_CATEGORIES)).toBe(true);
      expect(DEFAULT_SHORTCUT_CATEGORIES.length).toBeGreaterThanOrEqual(5);
    });

    it("should have required properties on each category", () => {
      DEFAULT_SHORTCUT_CATEGORIES.forEach((category) => {
        expect(category).toHaveProperty("id");
        expect(category).toHaveProperty("name");
        expect(category).toHaveProperty("shortcuts");
        expect(Array.isArray(category.shortcuts)).toBe(true);
      });
    });

    it("should have unique category IDs", () => {
      const ids = DEFAULT_SHORTCUT_CATEGORIES.map((c) => c.id);
      const uniqueIds = new Set(ids);
      expect(uniqueIds.size).toBe(ids.length);
    });

    it("should have required properties on each shortcut", () => {
      DEFAULT_SHORTCUT_CATEGORIES.forEach((category) => {
        category.shortcuts.forEach((shortcut) => {
          expect(shortcut).toHaveProperty("id");
          expect(shortcut).toHaveProperty("keys");
          expect(shortcut).toHaveProperty("description");
          expect(Array.isArray(shortcut.keys)).toBe(true);
          expect(shortcut.keys.length).toBeGreaterThan(0);
        });
      });
    });

    describe("navigation category", () => {
      it("should include command palette shortcut", () => {
        const navCategory = DEFAULT_SHORTCUT_CATEGORIES.find(
          (c) => c.id === "navigation"
        );
        expect(navCategory).toBeDefined();

        const cmdPalette = navCategory?.shortcuts.find(
          (s) => s.id === "command-palette"
        );
        expect(cmdPalette).toBeDefined();
        expect(cmdPalette?.keys).toContain("Cmd");
        expect(cmdPalette?.keys).toContain("K");
      });
    });

    describe("mcp category", () => {
      it("should include MCP category", () => {
        const mcpCategory = DEFAULT_SHORTCUT_CATEGORIES.find(
          (c) => c.id === "mcp"
        );
        expect(mcpCategory).toBeDefined();
        expect(mcpCategory?.name).toBe("MCP (Model Context Protocol)");
      });

      it("should have 4 MCP shortcuts", () => {
        const mcpCategory = DEFAULT_SHORTCUT_CATEGORIES.find(
          (c) => c.id === "mcp"
        );
        expect(mcpCategory?.shortcuts).toHaveLength(4);
      });

      it("should include Cmd+M for toggle panel", () => {
        const mcpCategory = DEFAULT_SHORTCUT_CATEGORIES.find(
          (c) => c.id === "mcp"
        );
        const toggleShortcut = mcpCategory?.shortcuts.find(
          (s) => s.id === "mcp-toggle-panel"
        );
        expect(toggleShortcut).toBeDefined();
        expect(toggleShortcut?.keys).toEqual(["Cmd", "M"]);
      });

      it("should include Cmd+Shift+T for tool dialog", () => {
        const mcpCategory = DEFAULT_SHORTCUT_CATEGORIES.find(
          (c) => c.id === "mcp"
        );
        const toolShortcut = mcpCategory?.shortcuts.find(
          (s) => s.id === "mcp-tool-dialog"
        );
        expect(toolShortcut).toBeDefined();
        expect(toolShortcut?.keys).toEqual(["Cmd", "Shift", "T"]);
      });

      it("should include Cmd+Shift+R for resource viewer", () => {
        const mcpCategory = DEFAULT_SHORTCUT_CATEGORIES.find(
          (c) => c.id === "mcp"
        );
        const resourceShortcut = mcpCategory?.shortcuts.find(
          (s) => s.id === "mcp-resource-viewer"
        );
        expect(resourceShortcut).toBeDefined();
        expect(resourceShortcut?.keys).toEqual(["Cmd", "Shift", "R"]);
      });

      it("should include Cmd+Shift+P for prompt tester", () => {
        const mcpCategory = DEFAULT_SHORTCUT_CATEGORIES.find(
          (c) => c.id === "mcp"
        );
        const promptShortcut = mcpCategory?.shortcuts.find(
          (s) => s.id === "mcp-prompt-tester"
        );
        expect(promptShortcut).toBeDefined();
        expect(promptShortcut?.keys).toEqual(["Cmd", "Shift", "P"]);
      });
    });

    describe("admin category", () => {
      it("should include admin dashboard shortcuts", () => {
        const adminCategory = DEFAULT_SHORTCUT_CATEGORIES.find(
          (c) => c.id === "admin"
        );
        expect(adminCategory).toBeDefined();
        expect(adminCategory?.shortcuts.length).toBeGreaterThanOrEqual(3);
      });
    });
  });
});
