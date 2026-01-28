/**
 * Skills Handlers
 *
 * MSW handlers for Skills Marketplace API endpoints.
 * These define the API contracts for skill management.
 *
 * Endpoints:
 * - GET /admin/skills/list - List skills from marketplace
 * - POST /admin/skills/install - Install a skill
 * - GET /admin/skills/installed - List installed skills
 * - DELETE /admin/skills/:name - Uninstall a skill
 * - GET /admin/skills/updates - Check for updates
 * - POST /admin/skills/updates/apply - Apply updates
 *
 * Marketplace Management Endpoints:
 * - GET /admin/marketplaces - List registered marketplaces
 * - POST /admin/marketplaces - Add a new marketplace
 * - DELETE /admin/marketplaces/:name - Remove a marketplace
 * - POST /admin/marketplaces/:name/sync - Sync skills from marketplace
 */

import { http, delay } from "msw";
import { apiJsonResponse, apiErrorResponse } from "../utils/apiResponse";
import type {
  SkillMetadata,
  SkillUpdate,
  ListMarketplaceSkillsResponse,
  ListInstalledSkillsResponse,
  ApplySkillUpdatesResponse,
  MarketplaceInfo,
  MarketplaceType,
} from "../../types/skills";

// =============================================================================
// Mock Data Factories
// =============================================================================

/**
 * Create a mock skill metadata with optional overrides
 */
export const createMockSkill = (
  overrides: Partial<SkillMetadata> = {},
): SkillMetadata => ({
  name: `skill-${crypto.randomUUID().slice(0, 8)}`,
  description: "A helpful skill for various tasks",
  version: "1.0.0",
  author: "Anthropic",
  tags: ["utility", "general"],
  ...overrides,
});

/**
 * Create a mock skill update with optional overrides
 */
export const createMockSkillUpdate = (
  overrides: Partial<SkillUpdate> = {},
): SkillUpdate => ({
  skillName: `skill-${crypto.randomUUID().slice(0, 8)}`,
  currentVersion: "1.0.0",
  newVersion: "1.1.0",
  marketplace: "anthropic",
  changelog: "Bug fixes and performance improvements",
  ...overrides,
});

/**
 * Create a mock marketplace info with optional overrides
 */
export const createMockMarketplace = (
  overrides: Partial<MarketplaceInfo> = {},
): MarketplaceInfo => ({
  name: `marketplace-${crypto.randomUUID().slice(0, 8)}`,
  uri: "https://github.com/example/skills-marketplace",
  type: "github",
  trusted: false,
  autoSync: false,
  requiresApproval: true,
  ...overrides,
});

// =============================================================================
// Mock State (for realistic stateful testing)
// =============================================================================

// In-memory state for installed skills (reset between tests)
let installedSkills: string[] = [];

// In-memory state for registered marketplaces (reset between tests)
let registeredMarketplaces: MarketplaceInfo[] = [
  {
    name: "anthropic",
    uri: "https://github.com/anthropics/skills-marketplace",
    type: "github",
    trusted: true,
    autoSync: true,
    requiresApproval: false,
  },
];

/**
 * Reset skills handler state. Call in test setup/teardown.
 */
export function resetSkillsState(): void {
  installedSkills = [];
  registeredMarketplaces = [
    {
      name: "anthropic",
      uri: "https://github.com/anthropics/skills-marketplace",
      type: "github",
      trusted: true,
      autoSync: true,
      requiresApproval: false,
    },
  ];
}

/**
 * Set installed skills for testing.
 */
export function setInstalledSkills(skills: string[]): void {
  installedSkills = [...skills];
}

/**
 * Set registered marketplaces for testing.
 */
export function setRegisteredMarketplaces(
  marketplaces: MarketplaceInfo[],
): void {
  registeredMarketplaces = [...marketplaces];
}

/**
 * Add a marketplace for testing.
 */
export function addMarketplace(marketplace: MarketplaceInfo): void {
  registeredMarketplaces.push(marketplace);
}

// =============================================================================
// MSW Handlers
// =============================================================================

/**
 * Default marketplace skills for listing
 */
const defaultMarketplaceSkills: SkillMetadata[] = [
  {
    name: "web-research",
    description: "Search the web for information and retrieve relevant content",
    version: "1.2.0",
    author: "Anthropic",
    tags: ["research", "web", "search"],
  },
  {
    name: "code-review",
    description: "Review and analyze code for improvements and issues",
    version: "2.1.0",
    author: "Community",
    tags: ["development", "code", "review"],
  },
  {
    name: "data-analysis",
    description: "Analyze datasets and generate insights",
    version: "1.0.0",
    author: "Anthropic",
    tags: ["data", "analytics", "insights"],
  },
  {
    name: "document-summary",
    description: "Summarize documents and extract key points",
    version: "1.5.0",
    author: "Enterprise",
    tags: ["documents", "summary", "text"],
  },
];

export const skillsHandlers = [
  /**
   * GET /admin/skills/list - List skills from marketplace
   */
  http.get("*/admin/skills/list", async ({ request }) => {
    await delay(100);

    const url = new URL(request.url);
    const marketplace = url.searchParams.get("marketplace") || "anthropic";
    const search = url.searchParams.get("search");
    const tagsParam = url.searchParams.get("tags");

    let skills = [...defaultMarketplaceSkills];

    // Apply search filter
    if (search) {
      const searchLower = search.toLowerCase();
      skills = skills.filter(
        (s) =>
          s.name.toLowerCase().includes(searchLower) ||
          s.description.toLowerCase().includes(searchLower),
      );
    }

    // Apply tags filter
    if (tagsParam) {
      const tags = tagsParam.split(",");
      skills = skills.filter((s) => tags.some((tag) => s.tags.includes(tag)));
    }

    const response: ListMarketplaceSkillsResponse = {
      skills,
      total: skills.length,
      marketplace,
      cached: false,
    };

    return apiJsonResponse(response);
  }),

  /**
   * POST /admin/skills/install - Install a skill
   */
  http.post("*/admin/skills/install", async ({ request }) => {
    await delay(200);

    // Parse request body with error handling
    let body: { skill_name?: string; marketplace?: string; version?: string };
    try {
      body = (await request.json()) as typeof body;
    } catch {
      return apiErrorResponse("Invalid JSON body", 400);
    }

    const skillName = body.skill_name;

    // Validate skill_name is present and non-empty
    if (!skillName || skillName.trim() === "") {
      return apiErrorResponse(
        "skill_name is required and cannot be empty",
        400,
      );
    }

    // Check if skill exists in marketplace
    const skill = defaultMarketplaceSkills.find((s) => s.name === skillName);
    if (!skill) {
      return apiErrorResponse(`Skill '${skillName}' not found`, 404);
    }

    // Check if already installed
    if (installedSkills.includes(skillName)) {
      return apiErrorResponse(`Skill '${skillName}' is already installed`, 409);
    }

    // Install the skill
    installedSkills.push(skillName);

    return apiJsonResponse({
      name: skill.name,
      description: skill.description,
      version: skill.version,
      author: skill.author,
      tags: skill.tags,
    });
  }),

  /**
   * GET /admin/skills/installed - List installed skills
   */
  http.get("*/admin/skills/installed", async () => {
    await delay(100);

    const response: ListInstalledSkillsResponse = {
      skills: installedSkills,
      count: installedSkills.length,
    };

    return apiJsonResponse(response);
  }),

  /**
   * DELETE /admin/skills/:name - Uninstall a skill
   */
  http.delete("*/admin/skills/:name", async ({ params }) => {
    await delay(150);

    const skillName = params.name as string;

    // Check if installed
    const index = installedSkills.indexOf(skillName);
    if (index === -1) {
      return apiErrorResponse(`Skill '${skillName}' is not installed`, 404);
    }

    // Uninstall
    installedSkills.splice(index, 1);

    return apiJsonResponse({
      success: true,
      skill_name: skillName,
      message: `Successfully uninstalled ${skillName}`,
    });
  }),

  /**
   * GET /admin/skills/updates - Check for updates
   */
  http.get("*/admin/skills/updates", async () => {
    await delay(100);

    // Return updates only for installed skills that have updates available
    const updates: SkillUpdate[] = installedSkills
      .filter((name) => name === "web-research") // Only web-research has an update
      .map((name) => ({
        skillName: name,
        currentVersion: "1.1.0",
        newVersion: "1.2.0",
        marketplace: "anthropic",
        changelog: "Performance improvements and bug fixes",
      }));

    return apiJsonResponse(updates);
  }),

  /**
   * POST /admin/skills/updates/apply - Apply updates
   */
  http.post("*/admin/skills/updates/apply", async () => {
    await delay(300);

    // Simulate applying updates
    const response: ApplySkillUpdatesResponse = {
      applied: installedSkills.length > 0 ? 1 : 0,
      results: installedSkills
        .filter((name) => name === "web-research")
        .map((name) => ({
          skillName: name,
          success: true,
          newVersion: "1.2.0",
        })),
    };

    return apiJsonResponse(response);
  }),

  // ===========================================================================
  // Marketplace Management Handlers
  // ===========================================================================

  /**
   * GET /admin/marketplaces - List registered marketplaces
   */
  http.get("*/admin/marketplaces", async () => {
    await delay(100);

    return apiJsonResponse({
      marketplaces: registeredMarketplaces,
    });
  }),

  /**
   * POST /admin/marketplaces - Add a new marketplace
   */
  http.post("*/admin/marketplaces", async ({ request }) => {
    await delay(200);

    // Parse request body with error handling
    let body: {
      name?: string;
      uri?: string;
      type?: MarketplaceType;
      trusted?: boolean;
      auto_sync?: boolean;
      requires_approval?: boolean;
    };
    try {
      body = (await request.json()) as typeof body;
    } catch {
      return apiErrorResponse("Invalid JSON body", 400);
    }

    // Validate required fields
    if (!body.name || body.name.trim() === "") {
      return apiErrorResponse("name is required and cannot be empty", 400);
    }
    if (!body.uri || body.uri.trim() === "") {
      return apiErrorResponse("uri is required and cannot be empty", 400);
    }

    // Check for duplicate name
    if (registeredMarketplaces.some((m) => m.name === body.name)) {
      return apiErrorResponse(`Marketplace '${body.name}' already exists`, 409);
    }

    // Add the new marketplace
    const newMarketplace: MarketplaceInfo = {
      name: body.name,
      uri: body.uri,
      type: body.type || "github",
      trusted: body.trusted ?? false,
      autoSync: body.auto_sync ?? false,
      requiresApproval: body.requires_approval ?? true,
    };

    registeredMarketplaces.push(newMarketplace);

    return apiJsonResponse({
      success: true,
      message: `Marketplace '${body.name}' added successfully`,
    });
  }),

  /**
   * DELETE /admin/marketplaces/:name - Remove a marketplace
   */
  http.delete("*/admin/marketplaces/:name", async ({ params }) => {
    await delay(150);

    const marketplaceName = params.name as string;

    // Find the marketplace
    const index = registeredMarketplaces.findIndex(
      (m) => m.name === marketplaceName,
    );

    if (index === -1) {
      return apiErrorResponse(
        `Marketplace '${marketplaceName}' not found`,
        404,
      );
    }

    // Prevent removal of default anthropic marketplace
    if (marketplaceName === "anthropic") {
      return apiErrorResponse(
        "Cannot remove the default Anthropic marketplace",
        403,
      );
    }

    // Remove the marketplace
    registeredMarketplaces.splice(index, 1);

    return apiJsonResponse({
      success: true,
      message: `Marketplace '${marketplaceName}' removed successfully`,
    });
  }),

  /**
   * POST /admin/marketplaces/:name/sync - Sync skills from marketplace
   */
  http.post("*/admin/marketplaces/:name/sync", async ({ params }) => {
    await delay(500);

    const marketplaceName = params.name as string;

    // Find the marketplace
    const marketplace = registeredMarketplaces.find(
      (m) => m.name === marketplaceName,
    );

    if (!marketplace) {
      return apiErrorResponse(
        `Marketplace '${marketplaceName}' not found`,
        404,
      );
    }

    // Simulate sync results
    return apiJsonResponse({
      synced: 5,
      new: 2,
      updated: 3,
    });
  }),
];
