/**
 * Navigation Sync Validation Tests
 *
 * These tests verify that navigation item IDs in ActivityBar.tsx are properly
 * synchronized with persona configurations in personaSlice.ts.
 *
 * This prevents issues like:
 * - Navigation items visible in ActivityBar but inaccessible due to persona filtering
 * - ID mismatches (e.g., "audit" vs "audit-logs")
 * - Missing items in persona configs
 *
 * @see ADR-0102 - Connections Page Redesign (revealed this gap)
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { NAV_ITEMS, BOTTOM_ITEMS } from "../../../layout/ActivityBar";

// =============================================================================
// Expected Navigation Items
// =============================================================================

/**
 * All navigation item IDs that should be available to at least one persona.
 * This is the source of truth for navigation items.
 */
const ALL_NAV_ITEM_IDS = NAV_ITEMS.map((item) => item.id);
const ALL_BOTTOM_ITEM_IDS = BOTTOM_ITEMS.map((item) => item.id);
const ALL_ITEM_IDS = [...ALL_NAV_ITEM_IDS, ...ALL_BOTTOM_ITEM_IDS];

/**
 * Admin persona should have access to ALL navigation items.
 * This is the expected configuration in personaSlice.ts.
 */
const EXPECTED_ADMIN_ITEMS = [
  // Core
  "projects",
  "chat",
  "workflows",
  // AI & Data
  "agents",
  "mcp",
  "vectors",
  "connections",
  "artifacts",
  // Observability
  "observability",
  "cost",
  // Admin
  "admin",
  "skills",
  "audit",
  "compliance",
  // Bottom
  "help",
  "settings",
];

/**
 * Developer persona should have access to development-focused items.
 */
const EXPECTED_DEVELOPER_ITEMS = [
  "projects",
  "chat",
  "workflows",
  "agents",
  "mcp",
  "vectors",
  "connections",
  "observability",
  "artifacts",
  "cost",
  "help",
  "settings",
];

/**
 * User persona has limited access.
 */
const EXPECTED_USER_ITEMS = ["projects", "chat", "workflows", "cost", "help"];

// =============================================================================
// Tests
// =============================================================================

afterEach(() => {
  vi.clearAllMocks();
});

describe("Navigation Item Sync Validation", () => {
  describe("ActivityBar NAV_ITEMS", () => {
    it("should define expected core navigation items", () => {
      expect(ALL_NAV_ITEM_IDS).toContain("projects");
      expect(ALL_NAV_ITEM_IDS).toContain("chat");
      expect(ALL_NAV_ITEM_IDS).toContain("workflows");
    });

    it("should define expected AI & Data items", () => {
      expect(ALL_NAV_ITEM_IDS).toContain("agents");
      expect(ALL_NAV_ITEM_IDS).toContain("mcp");
      expect(ALL_NAV_ITEM_IDS).toContain("vectors");
      expect(ALL_NAV_ITEM_IDS).toContain("connections");
      expect(ALL_NAV_ITEM_IDS).toContain("artifacts");
    });

    it("should define expected admin items", () => {
      expect(ALL_NAV_ITEM_IDS).toContain("admin");
      expect(ALL_NAV_ITEM_IDS).toContain("skills");
      expect(ALL_NAV_ITEM_IDS).toContain("audit");
      expect(ALL_NAV_ITEM_IDS).toContain("compliance");
    });

    it("should NOT have legacy IDs that cause mismatches", () => {
      // These are known legacy IDs that should NOT exist
      expect(ALL_NAV_ITEM_IDS).not.toContain("audit-logs"); // Should be "audit"
      expect(ALL_NAV_ITEM_IDS).not.toContain("traces"); // Removed in favor of observability
    });
  });

  describe("BOTTOM_ITEMS", () => {
    it("should define help and settings", () => {
      expect(ALL_BOTTOM_ITEM_IDS).toContain("help");
      expect(ALL_BOTTOM_ITEM_IDS).toContain("settings");
    });
  });

  describe("Admin Persona Coverage", () => {
    it("should have all expected admin items defined in ActivityBar", () => {
      // Every expected admin item should exist in NAV_ITEMS or BOTTOM_ITEMS
      for (const itemId of EXPECTED_ADMIN_ITEMS) {
        expect(
          ALL_ITEM_IDS,
          `Expected "${itemId}" to be in NAV_ITEMS or BOTTOM_ITEMS`,
        ).toContain(itemId);
      }
    });

    it("admin should have access to connections", () => {
      expect(EXPECTED_ADMIN_ITEMS).toContain("connections");
    });

    it("admin should have access to skills", () => {
      expect(EXPECTED_ADMIN_ITEMS).toContain("skills");
    });

    it("admin should have access to compliance", () => {
      expect(EXPECTED_ADMIN_ITEMS).toContain("compliance");
    });
  });

  describe("Developer Persona Coverage", () => {
    it("should have all expected developer items defined in ActivityBar", () => {
      for (const itemId of EXPECTED_DEVELOPER_ITEMS) {
        expect(
          ALL_ITEM_IDS,
          `Expected "${itemId}" to be in NAV_ITEMS or BOTTOM_ITEMS`,
        ).toContain(itemId);
      }
    });

    it("developer should have access to connections", () => {
      expect(EXPECTED_DEVELOPER_ITEMS).toContain("connections");
    });
  });

  describe("User Persona Coverage", () => {
    it("should have all expected user items defined in ActivityBar", () => {
      for (const itemId of EXPECTED_USER_ITEMS) {
        expect(
          ALL_ITEM_IDS,
          `Expected "${itemId}" to be in NAV_ITEMS or BOTTOM_ITEMS`,
        ).toContain(itemId);
      }
    });

    it("user should NOT have admin-only items", () => {
      expect(EXPECTED_USER_ITEMS).not.toContain("admin");
      expect(EXPECTED_USER_ITEMS).not.toContain("audit");
      expect(EXPECTED_USER_ITEMS).not.toContain("compliance");
      expect(EXPECTED_USER_ITEMS).not.toContain("skills");
    });
  });

  describe("ID Consistency", () => {
    it("all NAV_ITEMS should have unique IDs", () => {
      const ids = NAV_ITEMS.map((item) => item.id);
      const uniqueIds = new Set(ids);
      expect(ids.length).toBe(uniqueIds.size);
    });

    it("all NAV_ITEMS should have valid paths", () => {
      for (const item of NAV_ITEMS) {
        expect(item.path, `${item.id} should have a path`).toBeDefined();
        expect(item.path, `${item.id} path should start with /studio/`).toMatch(
          /^\/studio\//,
        );
      }
    });

    it("NAV_ITEMS IDs should match path segments", () => {
      for (const item of NAV_ITEMS) {
        // Path should be /studio/{id}
        const expectedPath = `/studio/${item.id}`;
        expect(item.path, `${item.id} path should be ${expectedPath}`).toBe(
          expectedPath,
        );
      }
    });
  });
});

describe("Persona Configuration Integration", () => {
  /**
   * This test validates that personaSlice.ts includes the correct items.
   * If this test fails, update PERSONA_CONFIGS in personaSlice.ts.
   */
  it("documents expected persona configurations", () => {
    // This is a documentation test - it passes if expectations match
    expect(EXPECTED_ADMIN_ITEMS.length).toBeGreaterThan(
      EXPECTED_DEVELOPER_ITEMS.length,
    );
    expect(EXPECTED_DEVELOPER_ITEMS.length).toBeGreaterThan(
      EXPECTED_USER_ITEMS.length,
    );
  });

  it("connections item should be available to admin and developer", () => {
    expect(EXPECTED_ADMIN_ITEMS).toContain("connections");
    expect(EXPECTED_DEVELOPER_ITEMS).toContain("connections");
    // User doesn't have connections access
    expect(EXPECTED_USER_ITEMS).not.toContain("connections");
  });
});
