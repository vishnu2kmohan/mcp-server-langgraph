/**
 * Service Worker Registration Tests
 *
 * TDD tests for service worker registration utility.
 * Tests cover:
 * - Registration in production mode
 * - Skip in development mode
 * - Error handling
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  registerServiceWorker,
  unregisterServiceWorker,
} from "./serviceWorker";

describe("serviceWorker", () => {
  const originalServiceWorker = navigator.serviceWorker;
  const originalLocation = window.location;
  let mockRegister: ReturnType<typeof vi.fn>;
  let mockUnregister: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();

    mockRegister = vi.fn().mockResolvedValue({
      scope: "/",
      update: vi.fn(),
    });

    mockUnregister = vi.fn().mockResolvedValue(true);

    // Mock navigator.serviceWorker
    Object.defineProperty(navigator, "serviceWorker", {
      value: {
        register: mockRegister,
        getRegistrations: vi
          .fn()
          .mockResolvedValue([{ unregister: mockUnregister }]),
        ready: Promise.resolve({ active: {} }),
      },
      configurable: true,
      writable: true,
    });
  });

  afterEach(() => {
    Object.defineProperty(navigator, "serviceWorker", {
      value: originalServiceWorker,
      configurable: true,
      writable: true,
    });

    Object.defineProperty(window, "location", {
      value: originalLocation,
      configurable: true,
      writable: true,
    });
  });

  describe("registerServiceWorker", () => {
    it("should skip registration when service worker is not supported", async () => {
      // Delete the property so "serviceWorker" in navigator returns false
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      delete (navigator as any).serviceWorker;

      const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});
      const result = await registerServiceWorker();

      expect(result).toBe(false);
      expect(consoleSpy).toHaveBeenCalledWith(
        "[ServiceWorker] Service workers are not supported in this browser",
      );
      consoleSpy.mockRestore();
    });

    it("should register service worker in production mode", async () => {
      // Mock production environment
      const _originalEnv = import.meta.env.PROD;
      vi.stubEnv("PROD", true);

      const result = await registerServiceWorker();

      expect(mockRegister).toHaveBeenCalledWith("/sw.js", {
        scope: "/",
      });
      expect(result).toBe(true);

      vi.unstubAllEnvs();
    });

    it("should handle registration errors gracefully", async () => {
      mockRegister.mockRejectedValue(new Error("Registration failed"));

      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      const result = await registerServiceWorker();

      expect(result).toBe(false);
      expect(consoleSpy).toHaveBeenCalledWith(
        "Service worker registration failed:",
        expect.any(Error),
      );

      consoleSpy.mockRestore();
    });

    it("should log successful registration", async () => {
      const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});

      await registerServiceWorker();

      // devLogger adds [ServiceWorker] prefix in dev/test mode
      expect(consoleSpy).toHaveBeenCalledWith(
        "[ServiceWorker] Service worker registered:",
        expect.any(Object),
      );

      consoleSpy.mockRestore();
    });
  });

  describe("unregisterServiceWorker", () => {
    it("should unregister all service workers", async () => {
      const result = await unregisterServiceWorker();

      expect(mockUnregister).toHaveBeenCalled();
      expect(result).toBe(true);
    });

    it("should return false when service worker is not supported", async () => {
      // Delete the property so "serviceWorker" in navigator returns false
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      delete (navigator as any).serviceWorker;

      const result = await unregisterServiceWorker();
      expect(result).toBe(false);
    });

    it("should handle unregistration errors gracefully", async () => {
      mockUnregister.mockRejectedValue(new Error("Unregister failed"));

      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      const result = await unregisterServiceWorker();

      expect(result).toBe(false);
      expect(consoleSpy).toHaveBeenCalledWith(
        "Service worker unregistration failed:",
        expect.any(Error),
      );

      consoleSpy.mockRestore();
    });
  });
});
