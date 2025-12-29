/**
 * Version Configuration Tests
 *
 * TDD tests for application and protocol version configuration.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import {
  APP_VERSION,
  PROTOCOL_VERSION,
  IS_DEV,
  IS_PRERELEASE,
  getDisplayVersion,
  isProtocolVersionCompatible,
  parseSemanticVersion,
} from "./version";

describe("version", () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("APP_VERSION", () => {
    it("should be a valid semver string", () => {
      expect(APP_VERSION).toMatch(/^\d+\.\d+\.\d+(-[\w.]+)?$/);
    });

    it("should export IS_DEV flag", () => {
      expect(typeof IS_DEV).toBe("boolean");
    });

    it("should export IS_PRERELEASE flag", () => {
      expect(typeof IS_PRERELEASE).toBe("boolean");
    });
  });

  describe("getDisplayVersion", () => {
    it("should return version with v prefix by default", () => {
      expect(getDisplayVersion()).toMatch(/^v\d+\.\d+\.\d+/);
    });

    it("should return version without prefix when specified", () => {
      expect(getDisplayVersion(false)).not.toMatch(/^v/);
    });
  });

  describe("PROTOCOL_VERSION", () => {
    it("should be a valid semver string", () => {
      expect(PROTOCOL_VERSION).toMatch(/^\d+\.\d+\.\d+$/);
    });

    it("should be 1.0.0 for initial protocol version", () => {
      // Protocol version starts at 1.0.0
      expect(PROTOCOL_VERSION).toBe("1.0.0");
    });
  });

  describe("parseSemanticVersion", () => {
    it("should parse valid semver string", () => {
      expect(parseSemanticVersion("1.0.0")).toEqual([1, 0, 0]);
      expect(parseSemanticVersion("2.10.5")).toEqual([2, 10, 5]);
    });

    it("should return null for invalid format", () => {
      expect(parseSemanticVersion("1.0")).toBeNull();
      expect(parseSemanticVersion("invalid")).toBeNull();
      expect(parseSemanticVersion("")).toBeNull();
    });

    it("should return null for null/undefined input", () => {
      expect(parseSemanticVersion(null as unknown as string)).toBeNull();
      expect(parseSemanticVersion(undefined as unknown as string)).toBeNull();
    });
  });

  describe("isProtocolVersionCompatible", () => {
    it("should return true for same version", () => {
      expect(isProtocolVersionCompatible("1.0.0", "1.0.0")).toBe(true);
    });

    it("should return true when client minor is lower than server", () => {
      expect(isProtocolVersionCompatible("1.0.0", "1.1.0")).toBe(true);
      expect(isProtocolVersionCompatible("1.0.0", "1.5.0")).toBe(true);
    });

    it("should return false when client minor is higher than server", () => {
      expect(isProtocolVersionCompatible("1.2.0", "1.1.0")).toBe(false);
    });

    it("should return false when major versions differ", () => {
      expect(isProtocolVersionCompatible("2.0.0", "1.0.0")).toBe(false);
      expect(isProtocolVersionCompatible("1.0.0", "2.0.0")).toBe(false);
    });

    it("should ignore patch version differences", () => {
      expect(isProtocolVersionCompatible("1.0.5", "1.0.0")).toBe(true);
      expect(isProtocolVersionCompatible("1.0.0", "1.0.99")).toBe(true);
    });

    it("should use current PROTOCOL_VERSION as default server version", () => {
      expect(isProtocolVersionCompatible("1.0.0")).toBe(true);
    });

    it("should return false for invalid version strings", () => {
      expect(isProtocolVersionCompatible("invalid", "1.0.0")).toBe(false);
      expect(isProtocolVersionCompatible("1.0.0", "invalid")).toBe(false);
    });
  });
});
