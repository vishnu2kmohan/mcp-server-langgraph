/**
 * cn (classNames) Utility Tests
 *
 * Tests for the shared className utility function.
 */
import { describe, it, expect, afterEach, vi } from "vitest";
import { cn } from "./cn";

describe("cn", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("should join multiple class strings", () => {
    expect(cn("foo", "bar", "baz")).toBe("foo bar baz");
  });

  it("should filter out undefined values", () => {
    expect(cn("foo", undefined, "bar")).toBe("foo bar");
  });

  it("should filter out false values", () => {
    expect(cn("foo", false, "bar")).toBe("foo bar");
  });

  it("should filter out empty strings", () => {
    expect(cn("foo", "", "bar")).toBe("foo bar");
  });

  it("should handle conditional classes", () => {
    const isActive = true;
    const isDisabled = false;
    expect(cn("base", isActive && "active", isDisabled && "disabled")).toBe(
      "base active",
    );
  });

  it("should return empty string for no valid classes", () => {
    expect(cn(undefined, false, "")).toBe("");
  });

  it("should handle single class", () => {
    expect(cn("single")).toBe("single");
  });

  it("should handle no arguments", () => {
    expect(cn()).toBe("");
  });

  it("should handle mixed truthy and falsy values", () => {
    expect(
      cn("a", null as unknown as string, "b", 0 as unknown as string, "c"),
    ).toBe("a b c");
  });
});
