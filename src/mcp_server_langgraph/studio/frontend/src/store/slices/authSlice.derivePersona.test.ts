/**
 * authSlice derivePersona Tests
 *
 * Tests for the pure persona derivation function.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { derivePersona } from "./authSlice";

afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("derivePersona", () => {
  it("should return admin when roles include admin", () => {
    expect(derivePersona(["admin", "user"])).toBe("admin");
  });

  it("should return developer when roles include developer but not admin", () => {
    expect(derivePersona(["developer", "user"])).toBe("developer");
  });

  it("should return user as default persona", () => {
    expect(derivePersona(["user"])).toBe("user");
    expect(derivePersona([])).toBe("user");
  });

  it("should prioritize admin over developer", () => {
    expect(derivePersona(["developer", "admin"])).toBe("admin");
  });
});
