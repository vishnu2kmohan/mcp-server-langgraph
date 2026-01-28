/**
 * Skills Types Tests
 *
 * TDD tests for skill type definitions.
 * Validates type exports and structure.
 */

import { describe, it, expect } from "vitest";
import type {
  SkillMetadata,
  SkillUpdate,
  MarketplaceInfo,
  MarketplaceType,
  ListMarketplaceSkillsParams,
  ListMarketplaceSkillsResponse,
  ListInstalledSkillsResponse,
  InstallSkillParams,
  ApplySkillUpdatesResponse,
} from "./skills";

describe("Skills Types", () => {
  describe("SkillMetadata", () => {
    it("should accept valid skill metadata", () => {
      const skill: SkillMetadata = {
        name: "web-research",
        description: "Search the web for information",
        version: "1.0.0",
        tags: ["research", "web"],
      };
      expect(skill.name).toBe("web-research");
      expect(skill.version).toBe("1.0.0");
    });

    it("should accept optional author field", () => {
      const skill: SkillMetadata = {
        name: "code-review",
        description: "Review code",
        version: "2.0.0",
        author: "Anthropic",
        tags: ["code"],
      };
      expect(skill.author).toBe("Anthropic");
    });

    it("should accept optional source field", () => {
      const skill: SkillMetadata = {
        name: "data-analysis",
        description: "Analyze data",
        version: "1.5.0",
        tags: [],
        source: "anthropic",
      };
      expect(skill.source).toBe("anthropic");
    });
  });

  describe("SkillUpdate", () => {
    it("should accept valid skill update", () => {
      const update: SkillUpdate = {
        skillName: "web-research",
        currentVersion: "1.0.0",
        newVersion: "1.1.0",
        marketplace: "anthropic",
      };
      expect(update.skillName).toBe("web-research");
      expect(update.currentVersion).toBe("1.0.0");
      expect(update.newVersion).toBe("1.1.0");
    });

    it("should accept optional changelog field", () => {
      const update: SkillUpdate = {
        skillName: "code-review",
        currentVersion: "1.0.0",
        newVersion: "2.0.0",
        marketplace: "anthropic",
        changelog: "Added new features",
      };
      expect(update.changelog).toBe("Added new features");
    });
  });

  describe("MarketplaceInfo", () => {
    it("should accept valid marketplace info", () => {
      const marketplace: MarketplaceInfo = {
        name: "anthropic",
        uri: "https://github.com/anthropics/skills",
        type: "github",
        trusted: true,
        autoSync: true,
        requiresApproval: false,
      };
      expect(marketplace.name).toBe("anthropic");
      expect(marketplace.type).toBe("github");
    });

    it("should accept oci marketplace type", () => {
      const marketplace: MarketplaceInfo = {
        name: "enterprise",
        uri: "oci://ghcr.io/company/skills",
        type: "oci",
        trusted: false,
        autoSync: false,
        requiresApproval: true,
      };
      expect(marketplace.type).toBe("oci");
    });

    it("should accept registry marketplace type", () => {
      const marketplace: MarketplaceInfo = {
        name: "custom",
        uri: "https://skills.example.com/api/v1",
        type: "registry",
        trusted: false,
        autoSync: false,
        requiresApproval: true,
      };
      expect(marketplace.type).toBe("registry");
    });
  });

  describe("MarketplaceType", () => {
    it("should be a union of valid types", () => {
      const types: MarketplaceType[] = ["github", "oci", "registry"];
      expect(types).toContain("github");
      expect(types).toContain("oci");
      expect(types).toContain("registry");
    });
  });

  describe("ListMarketplaceSkillsParams", () => {
    it("should accept search parameter", () => {
      const params: ListMarketplaceSkillsParams = {
        search: "web",
      };
      expect(params.search).toBe("web");
    });

    it("should accept marketplace parameter", () => {
      const params: ListMarketplaceSkillsParams = {
        marketplace: "anthropic",
      };
      expect(params.marketplace).toBe("anthropic");
    });

    it("should accept tags parameter", () => {
      const params: ListMarketplaceSkillsParams = {
        tags: ["research", "web"],
      };
      expect(params.tags).toEqual(["research", "web"]);
    });

    it("should accept limit parameter", () => {
      const params: ListMarketplaceSkillsParams = {
        limit: 20,
      };
      expect(params.limit).toBe(20);
    });

    it("should accept min_score parameter", () => {
      const params: ListMarketplaceSkillsParams = {
        min_score: 0.5,
      };
      expect(params.min_score).toBe(0.5);
    });
  });

  describe("ListMarketplaceSkillsResponse", () => {
    it("should contain skills array and metadata", () => {
      const response: ListMarketplaceSkillsResponse = {
        skills: [
          {
            name: "test",
            description: "Test skill",
            version: "1.0.0",
            tags: [],
          },
        ],
        total: 1,
        marketplace: "anthropic",
        cached: false,
      };
      expect(response.skills).toHaveLength(1);
      expect(response.total).toBe(1);
      expect(response.marketplace).toBe("anthropic");
      expect(response.cached).toBe(false);
    });
  });

  describe("ListInstalledSkillsResponse", () => {
    it("should contain skills array and count", () => {
      const response: ListInstalledSkillsResponse = {
        skills: ["web-research", "code-review"],
        count: 2,
      };
      expect(response.skills).toHaveLength(2);
      expect(response.count).toBe(2);
    });
  });

  describe("InstallSkillParams", () => {
    it("should require skillName", () => {
      const params: InstallSkillParams = {
        skillName: "web-research",
      };
      expect(params.skillName).toBe("web-research");
    });

    it("should accept optional marketplace", () => {
      const params: InstallSkillParams = {
        skillName: "web-research",
        marketplace: "anthropic",
      };
      expect(params.marketplace).toBe("anthropic");
    });

    it("should accept optional version", () => {
      const params: InstallSkillParams = {
        skillName: "web-research",
        version: "1.2.0",
      };
      expect(params.version).toBe("1.2.0");
    });
  });

  describe("ApplySkillUpdatesResponse", () => {
    it("should contain applied count and results", () => {
      const response: ApplySkillUpdatesResponse = {
        applied: 2,
        results: [
          { skillName: "skill1", success: true },
          { skillName: "skill2", success: true },
        ],
      };
      expect(response.applied).toBe(2);
      expect(response.results).toHaveLength(2);
    });
  });
});
