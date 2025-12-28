/**
 * Tests for intended route persistence (post-login redirect)
 *
 * TDD: These tests define the expected behavior for saving and restoring
 * the user's intended route after OAuth2 authentication.
 *
 * Problem solved: OAuth2 PKCE flow redirects to external IdP (Keycloak),
 * which loses React Router's location state. We persist the route to
 * sessionStorage before redirect and restore it after callback.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  setIntendedRoute,
  getIntendedRoute,
  clearIntendedRoute,
  saveCurrentRouteAsIntended,
  INTENDED_ROUTE_KEY,
} from "./intendedRoute";

describe("intendedRoute", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  afterEach(() => {
    sessionStorage.clear();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("INTENDED_ROUTE_KEY", () => {
    it("should be defined as a constant", () => {
      expect(INTENDED_ROUTE_KEY).toBeDefined();
      expect(typeof INTENDED_ROUTE_KEY).toBe("string");
    });

    it("should use sessionStorage (cleared on browser close)", () => {
      // sessionStorage is session-scoped, not persistent
      // This ensures intended route doesn't persist across browser sessions
      expect(INTENDED_ROUTE_KEY).toBe("studio-intended-route");
    });
  });

  describe("setIntendedRoute", () => {
    it("should save a simple path", () => {
      setIntendedRoute("/studio/chat/123");
      expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBe(
        "/studio/chat/123",
      );
    });

    it("should save a path with query string", () => {
      setIntendedRoute("/studio/canvas?artifact=abc&version=1");
      expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBe(
        "/studio/canvas?artifact=abc&version=1",
      );
    });

    it("should save a path with hash", () => {
      setIntendedRoute("/studio/settings#notifications");
      expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBe(
        "/studio/settings#notifications",
      );
    });

    it("should overwrite existing intended route", () => {
      setIntendedRoute("/studio/old-route");
      setIntendedRoute("/studio/new-route");
      expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBe(
        "/studio/new-route",
      );
    });

    it("should not save login/auth paths (to avoid redirect loops)", () => {
      setIntendedRoute("/login");
      expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBeNull();

      setIntendedRoute("/auth/callback");
      expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBeNull();
    });

    it("should not save empty or root paths", () => {
      setIntendedRoute("");
      expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBeNull();

      setIntendedRoute("/");
      expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBeNull();
    });
  });

  describe("getIntendedRoute", () => {
    it("should return null when no route is saved", () => {
      expect(getIntendedRoute()).toBeNull();
    });

    it("should return the saved route", () => {
      sessionStorage.setItem(INTENDED_ROUTE_KEY, "/studio/workflow/456");
      expect(getIntendedRoute()).toBe("/studio/workflow/456");
    });

    it("should return null after clearIntendedRoute is called", () => {
      sessionStorage.setItem(INTENDED_ROUTE_KEY, "/studio/chat");
      clearIntendedRoute();
      expect(getIntendedRoute()).toBeNull();
    });
  });

  describe("clearIntendedRoute", () => {
    it("should remove the intended route from storage", () => {
      sessionStorage.setItem(INTENDED_ROUTE_KEY, "/studio/test");
      clearIntendedRoute();
      expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBeNull();
    });

    it("should not throw if no route exists", () => {
      expect(() => clearIntendedRoute()).not.toThrow();
    });
  });

  describe("integration: save → get → clear cycle", () => {
    it("should complete full intended route lifecycle", () => {
      // 1. User visits protected route, AuthGuard saves it
      setIntendedRoute("/studio/canvas/artifact-123");

      // 2. After OAuth callback, read the intended route
      const route = getIntendedRoute();
      expect(route).toBe("/studio/canvas/artifact-123");

      // 3. Clear after redirect (one-time use)
      clearIntendedRoute();

      // 4. Verify cleared
      expect(getIntendedRoute()).toBeNull();
    });
  });

  describe("saveCurrentRouteAsIntended", () => {
    // Store original location for restoration
    const originalLocation = window.location;

    beforeEach(() => {
      // Mock window.location with configurable properties
      Object.defineProperty(window, "location", {
        configurable: true,
        value: {
          pathname: "/studio/chat/123",
          search: "",
          hash: "",
        },
      });
    });

    afterEach(() => {
      // Restore original location
      Object.defineProperty(window, "location", {
        configurable: true,
        value: originalLocation,
      });
    });

    it("should save current pathname to storage", () => {
      saveCurrentRouteAsIntended();
      expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBe(
        "/studio/chat/123",
      );
    });

    it("should save pathname with query string", () => {
      Object.defineProperty(window, "location", {
        configurable: true,
        value: {
          pathname: "/studio/canvas",
          search: "?artifact=abc&version=1",
          hash: "",
        },
      });

      saveCurrentRouteAsIntended();
      expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBe(
        "/studio/canvas?artifact=abc&version=1",
      );
    });

    it("should save pathname with hash", () => {
      Object.defineProperty(window, "location", {
        configurable: true,
        value: {
          pathname: "/studio/settings",
          search: "",
          hash: "#notifications",
        },
      });

      saveCurrentRouteAsIntended();
      expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBe(
        "/studio/settings#notifications",
      );
    });

    it("should save pathname with both query string and hash", () => {
      Object.defineProperty(window, "location", {
        configurable: true,
        value: {
          pathname: "/studio/workflow",
          search: "?id=456",
          hash: "#step-3",
        },
      });

      saveCurrentRouteAsIntended();
      expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBe(
        "/studio/workflow?id=456#step-3",
      );
    });

    it("should not save login paths (respects exclusion rules)", () => {
      Object.defineProperty(window, "location", {
        configurable: true,
        value: {
          pathname: "/login",
          search: "",
          hash: "",
        },
      });

      saveCurrentRouteAsIntended();
      expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBeNull();
    });

    it("should not save root path", () => {
      Object.defineProperty(window, "location", {
        configurable: true,
        value: {
          pathname: "/",
          search: "",
          hash: "",
        },
      });

      saveCurrentRouteAsIntended();
      expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBeNull();
    });
  });
});
