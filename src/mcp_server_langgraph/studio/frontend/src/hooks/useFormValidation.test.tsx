/**
 * useFormValidation Hook Tests
 *
 * Tests for the form validation hook that provides validation timing
 * configuration and error handling patterns.
 *
 * TDD: These tests were written FIRST before implementation.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import { useFormValidation } from "./useFormValidation";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("useFormValidation", () => {
  // ===========================================================================
  // Initial State Tests
  // ===========================================================================

  describe("initial state", () => {
    it("returns empty errors initially", () => {
      const { result } = renderHook(() => useFormValidation());

      expect(result.current.errors).toEqual({});
    });

    it("returns isValid as true initially", () => {
      const { result } = renderHook(() => useFormValidation());

      expect(result.current.isValid).toBe(true);
    });

    it("returns touched as empty initially", () => {
      const { result } = renderHook(() => useFormValidation());

      expect(result.current.touched).toEqual({});
    });

    it("returns isDirty as false initially", () => {
      const { result } = renderHook(() => useFormValidation());

      expect(result.current.isDirty).toBe(false);
    });
  });

  // ===========================================================================
  // Error Management Tests
  // ===========================================================================

  describe("error management", () => {
    it("sets a single field error", () => {
      const { result } = renderHook(() => useFormValidation());

      act(() => {
        result.current.setError("email", "Invalid email address");
      });

      expect(result.current.errors.email).toBe("Invalid email address");
      expect(result.current.isValid).toBe(false);
    });

    it("sets multiple field errors", () => {
      const { result } = renderHook(() => useFormValidation());

      act(() => {
        result.current.setErrors({
          email: "Invalid email",
          password: "Too short",
        });
      });

      expect(result.current.errors.email).toBe("Invalid email");
      expect(result.current.errors.password).toBe("Too short");
      expect(result.current.isValid).toBe(false);
    });

    it("clears a single field error", () => {
      const { result } = renderHook(() => useFormValidation());

      act(() => {
        result.current.setError("email", "Invalid email");
      });

      act(() => {
        result.current.clearError("email");
      });

      expect(result.current.errors.email).toBeUndefined();
      expect(result.current.isValid).toBe(true);
    });

    it("clears all errors", () => {
      const { result } = renderHook(() => useFormValidation());

      act(() => {
        result.current.setErrors({
          email: "Invalid",
          password: "Too short",
        });
      });

      act(() => {
        result.current.clearAllErrors();
      });

      expect(result.current.errors).toEqual({});
      expect(result.current.isValid).toBe(true);
    });
  });

  // ===========================================================================
  // Touched State Tests
  // ===========================================================================

  describe("touched state", () => {
    it("marks a field as touched", () => {
      const { result } = renderHook(() => useFormValidation());

      act(() => {
        result.current.setTouched("email");
      });

      expect(result.current.touched.email).toBe(true);
    });

    it("marks multiple fields as touched", () => {
      const { result } = renderHook(() => useFormValidation());

      act(() => {
        result.current.setTouched("email");
        result.current.setTouched("password");
      });

      expect(result.current.touched.email).toBe(true);
      expect(result.current.touched.password).toBe(true);
    });

    it("sets isDirty when any field is touched", () => {
      const { result } = renderHook(() => useFormValidation());

      expect(result.current.isDirty).toBe(false);

      act(() => {
        result.current.setTouched("email");
      });

      expect(result.current.isDirty).toBe(true);
    });
  });

  // ===========================================================================
  // Validation Helpers Tests
  // ===========================================================================

  describe("validation helpers", () => {
    it("hasError returns true when field has error", () => {
      const { result } = renderHook(() => useFormValidation());

      act(() => {
        result.current.setError("email", "Invalid email");
      });

      expect(result.current.hasError("email")).toBe(true);
      expect(result.current.hasError("password")).toBe(false);
    });

    it("getError returns the error message for a field", () => {
      const { result } = renderHook(() => useFormValidation());

      act(() => {
        result.current.setError("email", "Invalid email");
      });

      expect(result.current.getError("email")).toBe("Invalid email");
      expect(result.current.getError("password")).toBeUndefined();
    });

    it("getFieldProps returns error state for touched fields", () => {
      const { result } = renderHook(() => useFormValidation());

      act(() => {
        result.current.setError("email", "Invalid email");
        result.current.setTouched("email");
      });

      const fieldProps = result.current.getFieldProps("email");

      expect(fieldProps.error).toBe("Invalid email");
      expect(fieldProps["aria-invalid"]).toBe(true);
    });

    it("getFieldProps does not return error for untouched fields", () => {
      const { result } = renderHook(() => useFormValidation());

      act(() => {
        result.current.setError("email", "Invalid email");
        // Not touching the field
      });

      const fieldProps = result.current.getFieldProps("email");

      expect(fieldProps.error).toBeUndefined();
      expect(fieldProps["aria-invalid"]).toBeUndefined();
    });
  });

  // ===========================================================================
  // Reset Tests
  // ===========================================================================

  describe("reset", () => {
    it("resets all state to initial values", () => {
      const { result } = renderHook(() => useFormValidation());

      act(() => {
        result.current.setErrors({ email: "Invalid", password: "Short" });
        result.current.setTouched("email");
        result.current.setTouched("password");
      });

      expect(result.current.isValid).toBe(false);
      expect(result.current.isDirty).toBe(true);

      act(() => {
        result.current.reset();
      });

      expect(result.current.errors).toEqual({});
      expect(result.current.touched).toEqual({});
      expect(result.current.isValid).toBe(true);
      expect(result.current.isDirty).toBe(false);
    });
  });

  // ===========================================================================
  // Validation Mode Tests
  // ===========================================================================

  describe("validation mode", () => {
    it("supports onBlur validation mode (default)", () => {
      const { result } = renderHook(() =>
        useFormValidation({ mode: "onBlur" }),
      );

      expect(result.current.mode).toBe("onBlur");
    });

    it("supports onChange validation mode", () => {
      const { result } = renderHook(() =>
        useFormValidation({ mode: "onChange" }),
      );

      expect(result.current.mode).toBe("onChange");
    });

    it("supports onSubmit validation mode", () => {
      const { result } = renderHook(() =>
        useFormValidation({ mode: "onSubmit" }),
      );

      expect(result.current.mode).toBe("onSubmit");
    });

    it("supports revalidateOnChange option", () => {
      const { result } = renderHook(() =>
        useFormValidation({ mode: "onBlur", revalidateOnChange: true }),
      );

      expect(result.current.revalidateOnChange).toBe(true);
    });
  });

  // ===========================================================================
  // Error Count Tests
  // ===========================================================================

  describe("error count", () => {
    it("returns correct error count", () => {
      const { result } = renderHook(() => useFormValidation());

      expect(result.current.errorCount).toBe(0);

      act(() => {
        result.current.setErrors({
          email: "Invalid",
          password: "Short",
          username: "Taken",
        });
      });

      expect(result.current.errorCount).toBe(3);
    });
  });
});
