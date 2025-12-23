/**
 * Notification API Contract Tests
 *
 * Validates that the MSW handlers match the expected API contract for notification endpoints.
 * Uses raw fetch() to test the actual response shapes without RTK Query transformation.
 *
 * These tests document the Notification Preferences API contract and catch handler inconsistencies.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { server } from "../mocks/server";

describe("Notification API Contract Tests", () => {
  beforeEach(() => {
    // Server is already started in setup.ts
  });

  afterEach(() => {
    server.resetHandlers();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("GET /api/v1/notifications/preferences", () => {
    it("should return notification preferences", async () => {
      const response = await fetch("/api/v1/notifications/preferences");
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      // Required preference fields
      expect(data).toHaveProperty("info_enabled");
      expect(data).toHaveProperty("success_enabled");
      expect(data).toHaveProperty("warning_enabled");
      expect(data).toHaveProperty("error_enabled");
    });

    it("should return boolean values for all preferences", async () => {
      const response = await fetch("/api/v1/notifications/preferences");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(typeof data.info_enabled).toBe("boolean");
      expect(typeof data.success_enabled).toBe("boolean");
      expect(typeof data.warning_enabled).toBe("boolean");
      expect(typeof data.error_enabled).toBe("boolean");
    });
  });

  describe("PATCH /api/v1/notifications/preferences", () => {
    it("should update notification preferences", async () => {
      const response = await fetch("/api/v1/notifications/preferences", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          info_enabled: false,
          warning_enabled: true,
        }),
      });
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      // Should return updated preferences
      expect(data).toHaveProperty("info_enabled");
      expect(data).toHaveProperty("success_enabled");
      expect(data).toHaveProperty("warning_enabled");
      expect(data).toHaveProperty("error_enabled");
    });

    it("should reflect updated values in response", async () => {
      const response = await fetch("/api/v1/notifications/preferences", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          info_enabled: false,
          error_enabled: false,
        }),
      });
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(data.info_enabled).toBe(false);
      expect(data.error_enabled).toBe(false);
    });

    it("should preserve unspecified preferences", async () => {
      const response = await fetch("/api/v1/notifications/preferences", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          info_enabled: false,
        }),
      });
      expect(response.ok).toBe(true);

      const data = await response.json();

      // Unspecified preferences should default to true
      expect(data.success_enabled).toBe(true);
      expect(data.warning_enabled).toBe(true);
      expect(data.error_enabled).toBe(true);
    });
  });

  describe("POST /api/v1/notifications/preferences/reset", () => {
    it("should reset preferences to defaults", async () => {
      const response = await fetch("/api/v1/notifications/preferences/reset", {
        method: "POST",
      });
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      // All should be reset to enabled
      expect(data.info_enabled).toBe(true);
      expect(data.success_enabled).toBe(true);
      expect(data.warning_enabled).toBe(true);
      expect(data.error_enabled).toBe(true);
    });

    it("should return all preference fields", async () => {
      const response = await fetch("/api/v1/notifications/preferences/reset", {
        method: "POST",
      });
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(data).toHaveProperty("info_enabled");
      expect(data).toHaveProperty("success_enabled");
      expect(data).toHaveProperty("warning_enabled");
      expect(data).toHaveProperty("error_enabled");

      // Type validation
      expect(typeof data.info_enabled).toBe("boolean");
      expect(typeof data.success_enabled).toBe("boolean");
      expect(typeof data.warning_enabled).toBe("boolean");
      expect(typeof data.error_enabled).toBe("boolean");
    });
  });
});
