/**
 * Tests for Case Transformation Utilities
 *
 * ADR-0091 Phase 5: Snake to Camel Case Transformation Tests
 * Tests for toCamelCase, toSnakeCase, transformSnakeToCamel, and transformCamelToSnake.
 */

import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getTransformSnakeToCamel,
  getTransformCamelToSnake,
  getToCamelCase,
  getToSnakeCase,
} from "./transforms.test-utils";

afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

// =============================================================================
// toCamelCase utility
// =============================================================================

describe("toCamelCase utility", () => {
  it("converts snake_case to camelCase", async () => {
    const toCamelCase = await getToCamelCase();

    expect(toCamelCase("alert_id")).toBe("alertId");
    expect(toCamelCase("created_at")).toBe("createdAt");
    expect(toCamelCase("user_first_name")).toBe("userFirstName");
  });

  it("handles single word", async () => {
    const toCamelCase = await getToCamelCase();

    expect(toCamelCase("alert")).toBe("alert");
  });

  it("handles already camelCase", async () => {
    const toCamelCase = await getToCamelCase();

    expect(toCamelCase("alertId")).toBe("alertId");
  });

  it("handles uppercase letters in snake_case", async () => {
    const toCamelCase = await getToCamelCase();

    expect(toCamelCase("HTTP_STATUS")).toBe("httpStatus");
  });
});

// =============================================================================
// toSnakeCase utility
// =============================================================================

describe("toSnakeCase utility", () => {
  it("converts camelCase to snake_case", async () => {
    const toSnakeCase = await getToSnakeCase();

    expect(toSnakeCase("alertId")).toBe("alert_id");
    expect(toSnakeCase("createdAt")).toBe("created_at");
    expect(toSnakeCase("userFirstName")).toBe("user_first_name");
  });

  it("handles single word (lowercase)", async () => {
    const toSnakeCase = await getToSnakeCase();

    expect(toSnakeCase("alert")).toBe("alert");
  });

  it("preserves already snake_case", async () => {
    const toSnakeCase = await getToSnakeCase();

    expect(toSnakeCase("alert_id")).toBe("alert_id");
    expect(toSnakeCase("user_first_name")).toBe("user_first_name");
  });

  it("handles consecutive uppercase letters (acronyms)", async () => {
    const toSnakeCase = await getToSnakeCase();

    expect(toSnakeCase("getHTTPStatus")).toBe("get_h_t_t_p_status");
    expect(toSnakeCase("xmlHTTPRequest")).toBe("xml_h_t_t_p_request");
  });

  it("handles numbers in camelCase", async () => {
    const toSnakeCase = await getToSnakeCase();

    expect(toSnakeCase("modelV2Name")).toBe("model_v2_name");
    expect(toSnakeCase("item1Count")).toBe("item1_count");
  });

  it("handles leading uppercase", async () => {
    const toSnakeCase = await getToSnakeCase();

    expect(toSnakeCase("AlertId")).toBe("alert_id");
  });
});

// =============================================================================
// transformSnakeToCamel
// =============================================================================

describe("transformSnakeToCamel", () => {
  it("transforms simple object keys from snake_case to camelCase", async () => {
    const transformSnakeToCamel = await getTransformSnakeToCamel();

    const input = {
      alert_id: "123",
      created_at: "2024-01-01",
      user_name: "John",
    };

    const result = transformSnakeToCamel(input);

    expect(result).toEqual({
      alertId: "123",
      createdAt: "2024-01-01",
      userName: "John",
    });
  });

  it("handles nested objects recursively", async () => {
    const transformSnakeToCamel = await getTransformSnakeToCamel();

    const input = {
      user_id: "123",
      user_details: {
        first_name: "John",
        last_name: "Doe",
        contact_info: {
          email_address: "john@example.com",
        },
      },
    };

    const result = transformSnakeToCamel(input);

    expect(result).toEqual({
      userId: "123",
      userDetails: {
        firstName: "John",
        lastName: "Doe",
        contactInfo: {
          emailAddress: "john@example.com",
        },
      },
    });
  });

  it("handles arrays of objects", async () => {
    const transformSnakeToCamel = await getTransformSnakeToCamel();

    const input = {
      alert_items: [
        { alert_id: "1", alert_type: "warning" },
        { alert_id: "2", alert_type: "error" },
      ],
    };

    const result = transformSnakeToCamel(input);

    expect(result).toEqual({
      alertItems: [
        { alertId: "1", alertType: "warning" },
        { alertId: "2", alertType: "error" },
      ],
    });
  });

  it("preserves primitive values unchanged", async () => {
    const transformSnakeToCamel = await getTransformSnakeToCamel();

    const input = {
      count: 42,
      is_active: true,
      status: "pending",
      nullable_field: null,
    };

    const result = transformSnakeToCamel(input);

    expect(result).toEqual({
      count: 42,
      isActive: true,
      status: "pending",
      nullableField: null,
    });
  });

  it("handles empty objects and arrays", async () => {
    const transformSnakeToCamel = await getTransformSnakeToCamel();

    expect(transformSnakeToCamel({})).toEqual({});
    expect(transformSnakeToCamel({ empty_array: [] })).toEqual({
      emptyArray: [],
    });
  });

  it("handles keys that are already camelCase", async () => {
    const transformSnakeToCamel = await getTransformSnakeToCamel();

    const input = {
      alertId: "123", // Already camelCase
      user_name: "John", // snake_case
    };

    const result = transformSnakeToCamel(input);

    expect(result).toEqual({
      alertId: "123",
      userName: "John",
    });
  });

  it("handles keys with consecutive underscores", async () => {
    const transformSnakeToCamel = await getTransformSnakeToCamel();

    const input = {
      some__double__underscore: "value",
    };

    const result = transformSnakeToCamel(input);

    // Double underscores should be handled gracefully
    expect(result).toHaveProperty("someDoubleUnderscore");
  });

  it("handles keys with numbers", async () => {
    const transformSnakeToCamel = await getTransformSnakeToCamel();

    const input = {
      model_v2_name: "test",
      item_1_count: 5,
    };

    const result = transformSnakeToCamel(input);

    expect(result).toEqual({
      modelV2Name: "test",
      item1Count: 5,
    });
  });

  it("preserves array of primitives", async () => {
    const transformSnakeToCamel = await getTransformSnakeToCamel();

    const input = {
      tool_names: ["tool_1", "tool_2", "tool_3"],
    };

    const result = transformSnakeToCamel(input);

    // String values should NOT be transformed, only keys
    expect(result).toEqual({
      toolNames: ["tool_1", "tool_2", "tool_3"],
    });
  });

  it("handles Date objects correctly", async () => {
    const transformSnakeToCamel = await getTransformSnakeToCamel();

    const dateValue = new Date("2024-01-01");
    const input = {
      created_at: dateValue,
    };

    const result = transformSnakeToCamel(input);

    expect(result.createdAt).toBe(dateValue);
  });
});

// =============================================================================
// transformCamelToSnake
// =============================================================================

describe("transformCamelToSnake", () => {
  it("transforms simple object keys from camelCase to snake_case", async () => {
    const transformCamelToSnake = await getTransformCamelToSnake();

    const input = {
      alertId: "123",
      createdAt: "2024-01-01",
      userName: "John",
    };

    const result = transformCamelToSnake(input);

    expect(result).toEqual({
      alert_id: "123",
      created_at: "2024-01-01",
      user_name: "John",
    });
  });

  it("handles nested objects recursively", async () => {
    const transformCamelToSnake = await getTransformCamelToSnake();

    const input = {
      userId: "123",
      userDetails: {
        firstName: "John",
        lastName: "Doe",
        contactInfo: {
          emailAddress: "john@example.com",
        },
      },
    };

    const result = transformCamelToSnake(input);

    expect(result).toEqual({
      user_id: "123",
      user_details: {
        first_name: "John",
        last_name: "Doe",
        contact_info: {
          email_address: "john@example.com",
        },
      },
    });
  });

  it("handles arrays of objects", async () => {
    const transformCamelToSnake = await getTransformCamelToSnake();

    const input = {
      alertItems: [
        { alertId: "1", alertType: "warning" },
        { alertId: "2", alertType: "error" },
      ],
    };

    const result = transformCamelToSnake(input);

    expect(result).toEqual({
      alert_items: [
        { alert_id: "1", alert_type: "warning" },
        { alert_id: "2", alert_type: "error" },
      ],
    });
  });

  it("preserves primitive values unchanged", async () => {
    const transformCamelToSnake = await getTransformCamelToSnake();

    const input = {
      count: 42,
      isActive: true,
      status: "pending",
      nullableField: null,
    };

    const result = transformCamelToSnake(input);

    expect(result).toEqual({
      count: 42,
      is_active: true,
      status: "pending",
      nullable_field: null,
    });
  });

  it("handles empty objects and arrays", async () => {
    const transformCamelToSnake = await getTransformCamelToSnake();

    expect(transformCamelToSnake({})).toEqual({});
    expect(transformCamelToSnake({ emptyArray: [] })).toEqual({
      empty_array: [],
    });
  });

  it("handles keys that are already snake_case", async () => {
    const transformCamelToSnake = await getTransformCamelToSnake();

    const input = {
      alert_id: "123", // Already snake_case
      userName: "John", // camelCase
    };

    const result = transformCamelToSnake(input);

    expect(result).toEqual({
      alert_id: "123",
      user_name: "John",
    });
  });

  it("handles keys with numbers", async () => {
    const transformCamelToSnake = await getTransformCamelToSnake();

    const input = {
      modelV2Name: "test",
      item1Count: 5,
    };

    const result = transformCamelToSnake(input);

    expect(result).toEqual({
      model_v2_name: "test",
      item1_count: 5,
    });
  });

  it("preserves array of primitives (string values not transformed)", async () => {
    const transformCamelToSnake = await getTransformCamelToSnake();

    const input = {
      toolNames: ["toolOne", "toolTwo", "toolThree"],
    };

    const result = transformCamelToSnake(input);

    // String values should NOT be transformed, only keys
    expect(result).toEqual({
      tool_names: ["toolOne", "toolTwo", "toolThree"],
    });
  });

  it("handles Date objects correctly", async () => {
    const transformCamelToSnake = await getTransformCamelToSnake();

    const dateValue = new Date("2024-01-01");
    const input = {
      createdAt: dateValue,
    };

    const result = transformCamelToSnake(input);

    expect(result.created_at).toBe(dateValue);
  });

  it("handles null and undefined", async () => {
    const transformCamelToSnake = await getTransformCamelToSnake();

    expect(transformCamelToSnake(null)).toBe(null);
    expect(transformCamelToSnake(undefined)).toBe(undefined);
  });

  it("handles top-level arrays", async () => {
    const transformCamelToSnake = await getTransformCamelToSnake();

    const input = [
      { alertId: "1", alertType: "warning" },
      { alertId: "2", alertType: "error" },
    ];

    const result = transformCamelToSnake(input);

    expect(result).toEqual([
      { alert_id: "1", alert_type: "warning" },
      { alert_id: "2", alert_type: "error" },
    ]);
  });
});
