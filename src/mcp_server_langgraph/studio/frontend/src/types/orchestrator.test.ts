/**
 * Orchestrator Type Definitions Tests
 *
 * TDD tests for orchestrator mode types.
 * Tests type constraints, helper functions, and type guards.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import {
  type UserOrchestratorMode,
  type OrchestratorMode,
  USER_ORCHESTRATOR_MODES,
  ORCHESTRATOR_MODES,
  ORCHESTRATOR_MODE_DESCRIPTIONS,
  isUserOrchestratorMode,
  isOrchestratorMode,
  toUserOrchestratorMode,
} from "./orchestrator";

describe("Orchestrator Types", () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("USER_ORCHESTRATOR_MODES", () => {
    it("should only contain user-facing modes", () => {
      expect(USER_ORCHESTRATOR_MODES).toHaveLength(2);
      expect(USER_ORCHESTRATOR_MODES).toContain("standard");
      expect(USER_ORCHESTRATOR_MODES).toContain("swarm");
    });

    it("should not contain internal modes", () => {
      expect(USER_ORCHESTRATOR_MODES).not.toContain("studio");
      expect(USER_ORCHESTRATOR_MODES).not.toContain("ux");
      expect(USER_ORCHESTRATOR_MODES).not.toContain("alert");
    });
  });

  describe("ORCHESTRATOR_MODES", () => {
    it("should contain all orchestrator modes", () => {
      expect(ORCHESTRATOR_MODES).toHaveLength(5);
      expect(ORCHESTRATOR_MODES).toContain("standard");
      expect(ORCHESTRATOR_MODES).toContain("swarm");
      expect(ORCHESTRATOR_MODES).toContain("studio");
      expect(ORCHESTRATOR_MODES).toContain("ux");
      expect(ORCHESTRATOR_MODES).toContain("alert");
    });
  });

  describe("ORCHESTRATOR_MODE_DESCRIPTIONS", () => {
    it("should have descriptions for all modes", () => {
      expect(ORCHESTRATOR_MODE_DESCRIPTIONS.standard).toBeDefined();
      expect(ORCHESTRATOR_MODE_DESCRIPTIONS.swarm).toBeDefined();
      expect(ORCHESTRATOR_MODE_DESCRIPTIONS.studio).toBeDefined();
      expect(ORCHESTRATOR_MODE_DESCRIPTIONS.ux).toBeDefined();
      expect(ORCHESTRATOR_MODE_DESCRIPTIONS.alert).toBeDefined();
    });

    it("should have non-empty description strings", () => {
      for (const mode of ORCHESTRATOR_MODES) {
        expect(ORCHESTRATOR_MODE_DESCRIPTIONS[mode].length).toBeGreaterThan(0);
      }
    });
  });

  describe("isUserOrchestratorMode", () => {
    it("should return true for user-facing modes", () => {
      expect(isUserOrchestratorMode("standard")).toBe(true);
      expect(isUserOrchestratorMode("swarm")).toBe(true);
    });

    it("should return false for internal modes", () => {
      expect(isUserOrchestratorMode("studio")).toBe(false);
      expect(isUserOrchestratorMode("ux")).toBe(false);
      expect(isUserOrchestratorMode("alert")).toBe(false);
    });

    it("should return false for invalid values", () => {
      expect(isUserOrchestratorMode("invalid")).toBe(false);
      expect(isUserOrchestratorMode("")).toBe(false);
      expect(isUserOrchestratorMode(null as unknown as string)).toBe(false);
      expect(isUserOrchestratorMode(undefined as unknown as string)).toBe(
        false,
      );
    });
  });

  describe("isOrchestratorMode", () => {
    it("should return true for all valid modes", () => {
      expect(isOrchestratorMode("standard")).toBe(true);
      expect(isOrchestratorMode("swarm")).toBe(true);
      expect(isOrchestratorMode("studio")).toBe(true);
      expect(isOrchestratorMode("ux")).toBe(true);
      expect(isOrchestratorMode("alert")).toBe(true);
    });

    it("should return false for invalid values", () => {
      expect(isOrchestratorMode("invalid")).toBe(false);
      expect(isOrchestratorMode("")).toBe(false);
      expect(isOrchestratorMode(null as unknown as string)).toBe(false);
    });
  });

  describe("toUserOrchestratorMode", () => {
    it("should return the mode if it is user-facing", () => {
      expect(toUserOrchestratorMode("standard")).toBe("standard");
      expect(toUserOrchestratorMode("swarm")).toBe("swarm");
    });

    it("should return 'standard' for internal modes", () => {
      expect(toUserOrchestratorMode("studio")).toBe("standard");
      expect(toUserOrchestratorMode("ux")).toBe("standard");
      expect(toUserOrchestratorMode("alert")).toBe("standard");
    });

    it("should return 'standard' for invalid values", () => {
      expect(toUserOrchestratorMode("invalid")).toBe("standard");
      expect(toUserOrchestratorMode("")).toBe("standard");
    });
  });

  describe("Type compatibility", () => {
    it("should allow UserOrchestratorMode to be assigned to OrchestratorMode", () => {
      const userMode: UserOrchestratorMode = "standard";
      const mode: OrchestratorMode = userMode;
      expect(mode).toBe("standard");
    });
  });
});
