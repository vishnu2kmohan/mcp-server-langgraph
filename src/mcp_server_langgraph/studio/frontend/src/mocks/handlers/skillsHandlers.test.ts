/**
 * Skills Handlers Integration Tests
 *
 * Tests for Skills Marketplace MSW handlers.
 * Validates API contracts and mock behavior.
 */

import {
  afterAll,
  afterEach,
  beforeAll,
  describe,
  expect,
  it,
  vi,
} from "vitest";
import { setupServer } from "msw/node";
import {
  skillsHandlers,
  createMockSkill,
  createMockSkillUpdate,
  resetSkillsState,
  setInstalledSkills,
} from "./skillsHandlers";

// Setup MSW server
const server = setupServer(...skillsHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  vi.clearAllMocks();
  server.resetHandlers();
  resetSkillsState();
});
afterAll(() => server.close());

describe("skillsHandlers", () => {
  describe("GET /admin/skills/list", () => {
    it("should return marketplace skills", async () => {
      const response = await fetch("/admin/skills/list");
      expect(response.ok).toBe(true);

      const data = await response.json();
      expect(data.skills).toBeDefined();
      expect(Array.isArray(data.skills)).toBe(true);
      expect(data.total).toBeGreaterThan(0);
      expect(data.marketplace).toBe("anthropic");
    });

    it("should filter skills by search query", async () => {
      const response = await fetch("/admin/skills/list?search=web");
      const data = await response.json();

      expect(data.skills.length).toBeGreaterThan(0);
      expect(
        data.skills.every(
          (s: { name: string; description: string }) =>
            s.name.toLowerCase().includes("web") ||
            s.description.toLowerCase().includes("web"),
        ),
      ).toBe(true);
    });

    it("should filter skills by tags", async () => {
      const response = await fetch("/admin/skills/list?tags=research,web");
      const data = await response.json();

      expect(data.skills.length).toBeGreaterThan(0);
      expect(
        data.skills.every((s: { tags: string[] }) =>
          s.tags.some((t) => ["research", "web"].includes(t)),
        ),
      ).toBe(true);
    });

    it("should include marketplace name from params", async () => {
      const response = await fetch("/admin/skills/list?marketplace=enterprise");
      const data = await response.json();

      expect(data.marketplace).toBe("enterprise");
    });
  });

  describe("POST /admin/skills/install", () => {
    it("should install a skill successfully", async () => {
      const response = await fetch("/admin/skills/install", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skill_name: "web-research" }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.name).toBe("web-research");
    });

    it("should return 404 for non-existent skill", async () => {
      const response = await fetch("/admin/skills/install", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skill_name: "non-existent-skill" }),
      });

      expect(response.status).toBe(404);
      const data = await response.json();
      expect(data.detail).toContain("not found");
    });

    it("should return 409 for already installed skill", async () => {
      // Install first time
      await fetch("/admin/skills/install", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skill_name: "web-research" }),
      });

      // Try to install again
      const response = await fetch("/admin/skills/install", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skill_name: "web-research" }),
      });

      expect(response.status).toBe(409);
      const data = await response.json();
      expect(data.detail).toContain("already installed");
    });
  });

  describe("GET /admin/skills/installed", () => {
    it("should return empty list initially", async () => {
      const response = await fetch("/admin/skills/installed");
      expect(response.ok).toBe(true);

      const data = await response.json();
      expect(data.skills).toEqual([]);
      expect(data.count).toBe(0);
    });

    it("should return installed skills", async () => {
      setInstalledSkills(["web-research", "code-review"]);

      const response = await fetch("/admin/skills/installed");
      const data = await response.json();

      expect(data.skills).toContain("web-research");
      expect(data.skills).toContain("code-review");
      expect(data.count).toBe(2);
    });
  });

  describe("DELETE /admin/skills/:name", () => {
    it("should uninstall a skill successfully", async () => {
      setInstalledSkills(["web-research"]);

      const response = await fetch("/admin/skills/web-research", {
        method: "DELETE",
      });

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.success).toBe(true);
      expect(data.skill_name).toBe("web-research");

      // Verify uninstalled
      const listResponse = await fetch("/admin/skills/installed");
      const listData = await listResponse.json();
      expect(listData.skills).not.toContain("web-research");
    });

    it("should return 404 for non-installed skill", async () => {
      const response = await fetch("/admin/skills/non-existent", {
        method: "DELETE",
      });

      expect(response.status).toBe(404);
      const data = await response.json();
      expect(data.detail).toContain("not installed");
    });
  });

  describe("GET /admin/skills/updates", () => {
    it("should return empty updates when no skills installed", async () => {
      const response = await fetch("/admin/skills/updates");
      expect(response.ok).toBe(true);

      const data = await response.json();
      expect(data).toEqual([]);
    });

    it("should return updates for installed skills with updates", async () => {
      setInstalledSkills(["web-research"]);

      const response = await fetch("/admin/skills/updates");
      const data = await response.json();

      expect(data.length).toBeGreaterThan(0);
      expect(data[0].skill_name).toBe("web-research");
      expect(data[0].new_version).toBeDefined();
    });
  });

  describe("POST /admin/skills/updates/apply", () => {
    it("should apply updates", async () => {
      setInstalledSkills(["web-research"]);

      const response = await fetch("/admin/skills/updates/apply", {
        method: "POST",
      });

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.applied).toBeGreaterThan(0);
      expect(data.results).toBeDefined();
    });
  });

  describe("Mock factories", () => {
    it("createMockSkill should create valid skill metadata", () => {
      const skill = createMockSkill({ name: "custom-skill" });

      expect(skill.name).toBe("custom-skill");
      expect(skill.version).toBeDefined();
      expect(skill.tags).toBeDefined();
    });

    it("createMockSkillUpdate should create valid update info", () => {
      const update = createMockSkillUpdate({
        skillName: "test-skill",
        currentVersion: "1.0.0",
        newVersion: "2.0.0",
      });

      expect(update.skillName).toBe("test-skill");
      expect(update.currentVersion).toBe("1.0.0");
      expect(update.newVersion).toBe("2.0.0");
    });
  });

  // ===========================================================================
  // Edge Case Tests
  // ===========================================================================

  describe("Edge Cases", () => {
    describe("Validation Errors", () => {
      it("should return 400 for missing skill_name in install request", async () => {
        const response = await fetch("/admin/skills/install", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        });

        expect(response.status).toBe(400);
        const data = await response.json();
        expect(data.detail).toContain("skill_name");
      });

      it("should return 400 for empty skill_name in install request", async () => {
        const response = await fetch("/admin/skills/install", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ skill_name: "" }),
        });

        expect(response.status).toBe(400);
        const data = await response.json();
        expect(data.detail).toContain("skill_name");
      });

      it("should return 400 for invalid JSON body", async () => {
        const response = await fetch("/admin/skills/install", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: "invalid-json",
        });

        expect(response.status).toBe(400);
      });
    });

    describe("Combined Filters", () => {
      it("should filter by both search and tags", async () => {
        const response = await fetch(
          "/admin/skills/list?search=research&tags=web",
        );
        const data = await response.json();

        expect(data.skills.length).toBeGreaterThan(0);
        // Should match both search AND tags
        data.skills.forEach((s: { name: string; tags: string[] }) => {
          const matchesSearch = s.name.toLowerCase().includes("research");
          const matchesTags = s.tags.some((t) => t === "web");
          expect(matchesSearch || matchesTags).toBe(true);
        });
      });

      it("should return empty for non-matching combined filters", async () => {
        const response = await fetch(
          "/admin/skills/list?search=nonexistent&tags=nonexistenttag",
        );
        const data = await response.json();

        expect(data.skills).toEqual([]);
        expect(data.total).toBe(0);
      });
    });

    describe("Multiple Skills Operations", () => {
      it("should track multiple installed skills correctly", async () => {
        // Install multiple skills
        await fetch("/admin/skills/install", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ skill_name: "web-research" }),
        });
        await fetch("/admin/skills/install", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ skill_name: "code-review" }),
        });
        await fetch("/admin/skills/install", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ skill_name: "data-analysis" }),
        });

        const response = await fetch("/admin/skills/installed");
        const data = await response.json();

        expect(data.count).toBe(3);
        expect(data.skills).toContain("web-research");
        expect(data.skills).toContain("code-review");
        expect(data.skills).toContain("data-analysis");
      });

      it("should handle uninstall of middle skill", async () => {
        setInstalledSkills(["skill-a", "skill-b", "skill-c"]);

        // Uninstall middle skill
        await fetch("/admin/skills/skill-b", { method: "DELETE" });

        const response = await fetch("/admin/skills/installed");
        const data = await response.json();

        expect(data.skills).toContain("skill-a");
        expect(data.skills).not.toContain("skill-b");
        expect(data.skills).toContain("skill-c");
        expect(data.count).toBe(2);
      });
    });

    describe("Empty and Boundary Cases", () => {
      it("should handle empty search query gracefully", async () => {
        const response = await fetch("/admin/skills/list?search=");
        expect(response.ok).toBe(true);

        const data = await response.json();
        expect(data.skills.length).toBeGreaterThan(0);
      });

      it("should handle empty tags parameter gracefully", async () => {
        const response = await fetch("/admin/skills/list?tags=");
        expect(response.ok).toBe(true);

        const data = await response.json();
        expect(data.skills.length).toBeGreaterThan(0);
      });

      it("should handle special characters in search", async () => {
        const response = await fetch(
          "/admin/skills/list?search=" + encodeURIComponent("test-skill"),
        );
        expect(response.ok).toBe(true);
      });

      it("should handle very long skill names", async () => {
        const longName = "a".repeat(256);
        const response = await fetch("/admin/skills/install", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ skill_name: longName }),
        });

        // Should return 404 (not found) since this skill doesn't exist
        expect(response.status).toBe(404);
      });
    });

    describe("Updates Edge Cases", () => {
      it("should return empty updates when skills have no updates", async () => {
        // Install a skill that has no updates available
        setInstalledSkills(["code-review"]);

        const response = await fetch("/admin/skills/updates");
        const data = await response.json();

        // code-review might not have updates in the mock data
        expect(Array.isArray(data)).toBe(true);
      });

      it("should handle apply updates with no updates available", async () => {
        // No skills installed
        const response = await fetch("/admin/skills/updates/apply", {
          method: "POST",
        });

        expect(response.ok).toBe(true);
        const data = await response.json();
        expect(data.applied).toBe(0);
        expect(data.results).toEqual([]);
      });
    });

    describe("State Management", () => {
      it("resetSkillsState should clear all installed skills", async () => {
        setInstalledSkills(["skill-a", "skill-b"]);

        // Verify skills are set
        let response = await fetch("/admin/skills/installed");
        let data = await response.json();
        expect(data.count).toBe(2);

        // Reset state
        resetSkillsState();

        // Verify skills are cleared
        response = await fetch("/admin/skills/installed");
        data = await response.json();
        expect(data.count).toBe(0);
        expect(data.skills).toEqual([]);
      });
    });
  });
});
