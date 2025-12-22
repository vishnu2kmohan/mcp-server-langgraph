/**
 * Admin API Contract Tests
 *
 * Validates that the MSW handlers match the expected API contract for admin endpoints.
 * Uses raw fetch() to test the actual response shapes without RTK Query transformation.
 *
 * These tests document the Admin API contract and catch handler inconsistencies.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { server } from "../mocks/server";

describe("Admin API Contract Tests", () => {
  beforeEach(() => {
    // Server is already started in setup.ts
  });

  afterEach(() => {
    server.resetHandlers();
  });

  describe("GET /api/v1/admin/users", () => {
    it("should return paginated user list", async () => {
      const response = await fetch("/api/v1/admin/users");
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty("items");
      expect(data).toHaveProperty("total");

      expect(Array.isArray(data.items)).toBe(true);
      expect(typeof data.total).toBe("number");
    });

    it("should return users with required fields", async () => {
      const response = await fetch("/api/v1/admin/users");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(data.items.length).toBeGreaterThan(0);
      const user = data.items[0];

      // Required user fields
      expect(user).toHaveProperty("user_id");
      expect(user).toHaveProperty("username");
      expect(user).toHaveProperty("email");
      expect(user).toHaveProperty("roles");
      expect(user).toHaveProperty("active");

      // Type validation
      expect(typeof user.user_id).toBe("string");
      expect(typeof user.username).toBe("string");
      expect(typeof user.email).toBe("string");
      expect(Array.isArray(user.roles)).toBe(true);
      expect(typeof user.active).toBe("boolean");
    });

    it("should return multiple users", async () => {
      const response = await fetch("/api/v1/admin/users");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(data.items.length).toBeGreaterThanOrEqual(2);
      expect(data.total).toBeGreaterThanOrEqual(2);

      // Ensure unique user IDs
      const ids = data.items.map((u: { user_id: string }) => u.user_id);
      const uniqueIds = new Set(ids);
      expect(uniqueIds.size).toBe(ids.length);
    });
  });

  describe("GET /api/v1/admin/users/:userId", () => {
    it("should return user by ID", async () => {
      const response = await fetch("/api/v1/admin/users/user-123");
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty("user_id");
      expect(data).toHaveProperty("username");
      expect(data).toHaveProperty("email");
      expect(data).toHaveProperty("roles");
      expect(data).toHaveProperty("active");

      expect(data.user_id).toBe("user-123");
    });
  });

  describe("POST /api/v1/admin/users", () => {
    it("should create user and return 201", async () => {
      const response = await fetch("/api/v1/admin/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: "newuser",
          email: "newuser@example.com",
          roles: ["user", "developer"],
        }),
      });
      expect(response.status).toBe(201);

      const data = await response.json();

      expect(data).toHaveProperty("user_id");
      expect(data).toHaveProperty("username");
      expect(data).toHaveProperty("email");
      expect(data).toHaveProperty("roles");
      expect(data).toHaveProperty("active");

      expect(data.username).toBe("newuser");
      expect(data.email).toBe("newuser@example.com");
      expect(data.roles).toEqual(["user", "developer"]);
      expect(data.active).toBe(true);
    });

    it("should generate user_id for new users", async () => {
      const response = await fetch("/api/v1/admin/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: "testuser",
          email: "test@example.com",
        }),
      });
      expect(response.status).toBe(201);

      const data = await response.json();

      expect(data.user_id).toMatch(/^user-/);
    });
  });

  describe("PUT /api/v1/admin/users/:userId", () => {
    it("should update user", async () => {
      const response = await fetch("/api/v1/admin/users/user-123", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: "updated@example.com",
          roles: ["admin"],
          active: false,
        }),
      });
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty("user_id");
      expect(data.user_id).toBe("user-123");
      expect(data.email).toBe("updated@example.com");
      expect(data.roles).toEqual(["admin"]);
      expect(data.active).toBe(false);
    });
  });

  describe("DELETE /api/v1/admin/users/:userId", () => {
    it("should delete user and return 204", async () => {
      const response = await fetch("/api/v1/admin/users/user-123", {
        method: "DELETE",
      });
      expect(response.status).toBe(204);
    });
  });

  describe("GET /api/v1/admin/audit-logs", () => {
    it("should return paginated audit logs", async () => {
      const response = await fetch("/api/v1/admin/audit-logs");
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty("items");
      expect(data).toHaveProperty("next_cursor");
      expect(data).toHaveProperty("has_more");

      expect(Array.isArray(data.items)).toBe(true);
      expect(typeof data.has_more).toBe("boolean");
    });

    it("should return audit logs with required fields", async () => {
      const response = await fetch("/api/v1/admin/audit-logs");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(data.items.length).toBeGreaterThan(0);
      const log = data.items[0];

      // Required audit log fields
      expect(log).toHaveProperty("id");
      expect(log).toHaveProperty("timestamp");
      expect(log).toHaveProperty("user_id");
      expect(log).toHaveProperty("action");
      expect(log).toHaveProperty("resource_type");
      expect(log).toHaveProperty("resource_id");

      // Type validation
      expect(typeof log.id).toBe("string");
      expect(typeof log.timestamp).toBe("string");
      expect(typeof log.user_id).toBe("string");
      expect(typeof log.action).toBe("string");
      expect(typeof log.resource_type).toBe("string");
      expect(typeof log.resource_id).toBe("string");

      // Validate ISO timestamp
      expect(new Date(log.timestamp).toISOString()).toBe(log.timestamp);
    });

    it("should return multiple audit logs", async () => {
      const response = await fetch("/api/v1/admin/audit-logs");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(data.items.length).toBeGreaterThanOrEqual(2);

      // Ensure unique log IDs
      const ids = data.items.map((l: { id: string }) => l.id);
      const uniqueIds = new Set(ids);
      expect(uniqueIds.size).toBe(ids.length);
    });
  });

  describe("User Role Validation", () => {
    it("should have valid role values", async () => {
      const response = await fetch("/api/v1/admin/users");
      expect(response.ok).toBe(true);

      const data = await response.json();

      const validRoles = ["admin", "user", "developer", "analyst", "auditor"];

      for (const user of data.items) {
        for (const role of user.roles) {
          expect(validRoles).toContain(role);
        }
      }
    });
  });

  describe("Audit Action Validation", () => {
    it("should have valid action values", async () => {
      const response = await fetch("/api/v1/admin/audit-logs");
      expect(response.ok).toBe(true);

      const data = await response.json();

      const validActions = ["create", "read", "update", "delete"];

      for (const log of data.items) {
        expect(validActions).toContain(log.action);
      }
    });
  });
});
