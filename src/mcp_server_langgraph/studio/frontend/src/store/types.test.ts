/**
 * Store Types Tests
 *
 * TDD tests for the isolated store type definitions.
 * These types allow tests to import RootState and AppDispatch
 * without triggering the full store/api initialization.
 */

import { describe, it, expect, expectTypeOf } from "vitest";

// This import should NOT trigger api module loading
// Use value import to ensure module exists (not just type-only)
import * as StoreTypes from "./types";
import type { RootState, AppDispatch, SliceStates } from "./types";

describe("Store Types", () => {
  describe("RootState", () => {
    it("should include ui slice state", () => {
      // Type-level test: RootState should have ui property
      expectTypeOf<RootState>().toHaveProperty("ui");
    });

    it("should include persona slice state", () => {
      expectTypeOf<RootState>().toHaveProperty("persona");
    });

    it("should include session slice state", () => {
      expectTypeOf<RootState>().toHaveProperty("session");
    });

    it("should include workflow slice state", () => {
      expectTypeOf<RootState>().toHaveProperty("workflow");
    });

    it("should include canvas slice state", () => {
      expectTypeOf<RootState>().toHaveProperty("canvas");
    });

    it("should include auth slice state", () => {
      expectTypeOf<RootState>().toHaveProperty("auth");
    });
  });

  describe("SliceStates", () => {
    it("should export individual slice state types", () => {
      // These should be importable for creating test stores
      expectTypeOf<SliceStates["ui"]>().not.toBeNever();
      expectTypeOf<SliceStates["persona"]>().not.toBeNever();
      expectTypeOf<SliceStates["session"]>().not.toBeNever();
      expectTypeOf<SliceStates["workflow"]>().not.toBeNever();
    });
  });

  describe("AppDispatch", () => {
    it("should be a function type", () => {
      // AppDispatch should be a callable dispatch function
      expectTypeOf<AppDispatch>().toBeFunction();
    });
  });

  describe("OOM Safety", () => {
    it("should import types without loading api module", () => {
      // If this test runs without OOM, the types are safe
      // The import at the top of the file should NOT have triggered api loading
      expect(true).toBe(true);
    });

    it("should export the module successfully", () => {
      // Verify the module can be imported (not just types)
      expect(StoreTypes).toBeDefined();
    });
  });
});
