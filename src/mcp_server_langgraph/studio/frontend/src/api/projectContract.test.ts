/**
 * Project API Contract Tests
 *
 * Validates that the MSW handlers match the expected API contract for projects.
 * Uses raw fetch() to test the actual response shapes without RTK Query transformation.
 *
 * These tests document the API contract and catch handler inconsistencies.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { server } from "../mocks/server";

describe("Project API Contract Tests", () => {
  beforeEach(() => {
    // Server is already started in setup.ts
  });

  afterEach(() => {
    server.resetHandlers();
  });

  describe("GET /api/v1/projects", () => {
    it("should return paginated project list", async () => {
      const response = await fetch("/api/v1/projects");
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      // Verify pagination structure
      expect(data).toHaveProperty("items");
      expect(data).toHaveProperty("total");
      expect(data).toHaveProperty("page");
      expect(data).toHaveProperty("per_page");
      expect(data).toHaveProperty("total_pages");

      expect(Array.isArray(data.items)).toBe(true);
      expect(typeof data.total).toBe("number");
      expect(typeof data.page).toBe("number");
      expect(typeof data.per_page).toBe("number");
      expect(typeof data.total_pages).toBe("number");
    });

    it("should return projects with required fields", async () => {
      const response = await fetch("/api/v1/projects");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(data.items.length).toBeGreaterThan(0);
      const project = data.items[0];

      // Required project fields
      expect(project).toHaveProperty("id");
      expect(project).toHaveProperty("name");
      expect(project).toHaveProperty("description");
      expect(project).toHaveProperty("created_at");
      expect(project).toHaveProperty("updated_at");

      // Type validation
      expect(typeof project.id).toBe("string");
      expect(typeof project.name).toBe("string");
      expect(typeof project.description).toBe("string");
      expect(typeof project.created_at).toBe("string");
      expect(typeof project.updated_at).toBe("string");

      // Validate ISO date format
      expect(new Date(project.created_at).toISOString()).toBe(project.created_at);
      expect(new Date(project.updated_at).toISOString()).toBe(project.updated_at);
    });

    it("should return multiple projects", async () => {
      const response = await fetch("/api/v1/projects");
      expect(response.ok).toBe(true);

      const data = await response.json();

      // Mock should return at least 2 projects
      expect(data.items.length).toBeGreaterThanOrEqual(2);
      expect(data.total).toBeGreaterThanOrEqual(2);

      // Ensure unique IDs
      const ids = data.items.map((p: { id: string }) => p.id);
      const uniqueIds = new Set(ids);
      expect(uniqueIds.size).toBe(ids.length);
    });
  });

  describe("Project ID Validation", () => {
    it("should have project IDs starting with 'proj-' prefix", async () => {
      const response = await fetch("/api/v1/projects");
      expect(response.ok).toBe(true);

      const data = await response.json();

      for (const project of data.items) {
        expect(project.id).toMatch(/^proj-/);
      }
    });
  });
});
