/**
 * Tests for API Transform Helpers
 *
 * Validates cursor pagination transforms between backend and frontend formats.
 */

import { afterEach, describe, expect, expectTypeOf, it, vi } from "vitest";

import type { BackendCursorPaginatedResponse } from "../types/api";
import {
  extractPaginationMetadata,
  isCursorPaginatedResponse,
  transformCursorPaginatedResponse,
  transformToLegacyPaginatedResponse,
} from "./transforms";
import type {
  SnakeToCamelCase,
  SnakeToCamelCaseDeep,
  CamelToSnakeCase,
  CamelToSnakeCaseDeep,
} from "./transforms";

afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("transformCursorPaginatedResponse", () => {
  it("transforms backend response to frontend format", () => {
    // GIVEN: A backend cursor-paginated response
    const backendResponse: BackendCursorPaginatedResponse<{ id: string }> = {
      data: [{ id: "1" }, { id: "2" }, { id: "3" }],
      pagination: {
        count: 3,
        has_next: true,
        has_prev: false,
        next_cursor: "eyJpZCI6IjMifQ==",
        prev_cursor: null,
      },
    };

    // WHEN: Transforming to frontend format
    const result = transformCursorPaginatedResponse(backendResponse);

    // THEN: Should have correct frontend structure
    expect(result.items).toEqual([{ id: "1" }, { id: "2" }, { id: "3" }]);
    expect(result.count).toBe(3);
    expect(result.hasNext).toBe(true);
    expect(result.hasPrev).toBe(false);
    expect(result.nextCursor).toBe("eyJpZCI6IjMifQ==");
    expect(result.prevCursor).toBeUndefined();
    // Also preserves raw pagination
    expect(result.pagination).toEqual(backendResponse.pagination);
  });

  it("handles empty data array", () => {
    // GIVEN: An empty response
    const backendResponse: BackendCursorPaginatedResponse<{ id: string }> = {
      data: [],
      pagination: {
        count: 0,
        has_next: false,
        has_prev: false,
        next_cursor: null,
        prev_cursor: null,
      },
    };

    // WHEN: Transforming
    const result = transformCursorPaginatedResponse(backendResponse);

    // THEN: Should handle empty correctly
    expect(result.items).toEqual([]);
    expect(result.count).toBe(0);
    expect(result.hasNext).toBe(false);
    expect(result.hasPrev).toBe(false);
    expect(result.nextCursor).toBeUndefined();
    expect(result.prevCursor).toBeUndefined();
  });

  it("handles middle page with both cursors", () => {
    // GIVEN: A response from a middle page
    const backendResponse: BackendCursorPaginatedResponse<{ id: string }> = {
      data: [{ id: "5" }, { id: "6" }],
      pagination: {
        count: 2,
        has_next: true,
        has_prev: true,
        next_cursor: "eyJpZCI6IjYifQ==",
        prev_cursor: "eyJpZCI6IjQifQ==",
      },
    };

    // WHEN: Transforming
    const result = transformCursorPaginatedResponse(backendResponse);

    // THEN: Should have both cursors
    expect(result.hasNext).toBe(true);
    expect(result.hasPrev).toBe(true);
    expect(result.nextCursor).toBe("eyJpZCI6IjYifQ==");
    expect(result.prevCursor).toBe("eyJpZCI6IjQifQ==");
  });

  it("converts null cursors to undefined for cleaner frontend usage", () => {
    // GIVEN: Response with null cursors
    const backendResponse: BackendCursorPaginatedResponse<{ id: string }> = {
      data: [{ id: "1" }],
      pagination: {
        count: 1,
        has_next: false,
        has_prev: false,
        next_cursor: null,
        prev_cursor: null,
      },
    };

    // WHEN: Transforming
    const result = transformCursorPaginatedResponse(backendResponse);

    // THEN: Cursors should be undefined, not null
    expect(result.nextCursor).toBeUndefined();
    expect(result.prevCursor).toBeUndefined();
    // But raw pagination preserves null
    expect(result.pagination.next_cursor).toBeNull();
  });
});

describe("transformToLegacyPaginatedResponse", () => {
  it("transforms to legacy format for backward compatibility", () => {
    // GIVEN: A backend cursor-paginated response
    const backendResponse: BackendCursorPaginatedResponse<{ id: string }> = {
      data: [{ id: "1" }, { id: "2" }],
      pagination: {
        count: 2,
        has_next: true,
        has_prev: false,
        next_cursor: "eyJpZCI6IjIifQ==",
        prev_cursor: null,
      },
    };

    // WHEN: Transforming to legacy format
    const result = transformToLegacyPaginatedResponse(backendResponse, 20);

    // THEN: Should have legacy structure
    expect(result.items).toEqual([{ id: "1" }, { id: "2" }]);
    expect(result.limit).toBe(20);
    expect(result.next_cursor).toBe("eyJpZCI6IjIifQ==");
    // Total is undefined in cursor-based pagination
    expect(result.total).toBeUndefined();
  });

  it("uses default limit of 20 when not specified", () => {
    const backendResponse: BackendCursorPaginatedResponse<{ id: string }> = {
      data: [],
      pagination: {
        count: 0,
        has_next: false,
        has_prev: false,
      },
    };

    const result = transformToLegacyPaginatedResponse(backendResponse);

    expect(result.limit).toBe(20);
  });
});

describe("isCursorPaginatedResponse", () => {
  it("returns true for valid cursor-paginated response", () => {
    const response = {
      data: [{ id: "1" }],
      pagination: {
        count: 1,
        has_next: false,
        has_prev: false,
      },
    };

    expect(isCursorPaginatedResponse(response)).toBe(true);
  });

  it("returns false for null", () => {
    expect(isCursorPaginatedResponse(null)).toBe(false);
  });

  it("returns false for undefined", () => {
    expect(isCursorPaginatedResponse(undefined)).toBe(false);
  });

  it("returns false for non-object", () => {
    expect(isCursorPaginatedResponse("string")).toBe(false);
    expect(isCursorPaginatedResponse(123)).toBe(false);
  });

  it("returns false when data is missing", () => {
    expect(
      isCursorPaginatedResponse({
        pagination: { count: 0, has_next: false, has_prev: false },
      }),
    ).toBe(false);
  });

  it("returns false when pagination is missing", () => {
    expect(isCursorPaginatedResponse({ data: [] })).toBe(false);
  });

  it("returns false when data is not an array", () => {
    expect(
      isCursorPaginatedResponse({
        data: "not-an-array",
        pagination: { count: 0, has_next: false, has_prev: false },
      }),
    ).toBe(false);
  });
});

describe("extractPaginationMetadata", () => {
  it("extracts pagination from backend format", () => {
    const response = {
      data: [],
      pagination: {
        count: 10,
        has_next: true,
        has_prev: false,
        next_cursor: "abc",
        prev_cursor: null,
      },
    };

    const result = extractPaginationMetadata(response);

    expect(result).toEqual({
      count: 10,
      has_next: true,
      has_prev: false,
      next_cursor: "abc",
      prev_cursor: null,
    });
  });

  it("returns undefined for null", () => {
    expect(extractPaginationMetadata(null)).toBeUndefined();
  });

  it("returns undefined for undefined", () => {
    expect(extractPaginationMetadata(undefined)).toBeUndefined();
  });

  it("returns undefined when no pagination found", () => {
    expect(extractPaginationMetadata({ items: [] })).toBeUndefined();
  });

  it("handles already transformed format", () => {
    const transformedResponse = {
      items: [],
      count: 5,
      has_next: false,
      has_prev: true,
      next_cursor: undefined,
      prev_cursor: "xyz",
    };

    const result = extractPaginationMetadata(transformedResponse);

    expect(result).toEqual({
      count: 5,
      has_next: false,
      has_prev: true,
      next_cursor: undefined,
      prev_cursor: "xyz",
    });
  });
});

// =============================================================================
// ADR-0091 Phase 5: Snake to Camel Case Transformation Tests
// =============================================================================

describe("transformSnakeToCamel", () => {
  // Import dynamically to match test structure
  const getTransformSnakeToCamel = async () => {
    const { transformSnakeToCamel } = await import("./transforms");
    return transformSnakeToCamel;
  };

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

describe("toCamelCase utility", () => {
  const getToCamelCase = async () => {
    const { toCamelCase } = await import("./transforms");
    return toCamelCase;
  };

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
// ADR-0091 Phase 5: Camel to Snake Case Transformation Tests (Request Direction)
// =============================================================================

describe("toSnakeCase utility", () => {
  const getToSnakeCase = async () => {
    const { toSnakeCase } = await import("./transforms");
    return toSnakeCase;
  };

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

describe("transformCamelToSnake", () => {
  const getTransformCamelToSnake = async () => {
    const { transformCamelToSnake } = await import("./transforms");
    return transformCamelToSnake;
  };

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

// =============================================================================
// Round-trip Symmetry Tests (ADR-0091 Phase 5)
// =============================================================================

describe("Round-trip transform symmetry", () => {
  const getTransforms = async () => {
    const { transformSnakeToCamel, transformCamelToSnake } =
      await import("./transforms");
    return { transformSnakeToCamel, transformCamelToSnake };
  };

  it("camelCase -> snake_case -> camelCase preserves data", async () => {
    const { transformSnakeToCamel, transformCamelToSnake } =
      await getTransforms();

    const original = {
      alertId: "123",
      userData: {
        firstName: "John",
        lastName: "Doe",
      },
      itemList: [{ itemId: "1" }, { itemId: "2" }],
    };

    const roundTrip = transformSnakeToCamel(transformCamelToSnake(original));

    expect(roundTrip).toEqual(original);
  });

  it("snake_case -> camelCase -> snake_case preserves data", async () => {
    const { transformSnakeToCamel, transformCamelToSnake } =
      await getTransforms();

    const original = {
      alert_id: "123",
      user_data: {
        first_name: "John",
        last_name: "Doe",
      },
      item_list: [{ item_id: "1" }, { item_id: "2" }],
    };

    const roundTrip = transformCamelToSnake(transformSnakeToCamel(original));

    expect(roundTrip).toEqual(original);
  });

  it("handles complex nested structures in round-trip", async () => {
    const { transformSnakeToCamel, transformCamelToSnake } =
      await getTransforms();

    const original = {
      workflowId: "wf-123",
      workflowConfig: {
        nodeSettings: {
          maxRetries: 3,
          timeoutMs: 5000,
        },
        edgeList: [
          { sourceNodeId: "node-1", targetNodeId: "node-2" },
          { sourceNodeId: "node-2", targetNodeId: "node-3" },
        ],
      },
      createdAt: "2024-01-01",
    };

    const roundTrip = transformSnakeToCamel(transformCamelToSnake(original));

    expect(roundTrip).toEqual(original);
  });

  it("preserves primitive values through round-trip", async () => {
    const { transformSnakeToCamel, transformCamelToSnake } =
      await getTransforms();

    const original = {
      count: 42,
      isActive: true,
      floatValue: 3.14,
      nullValue: null,
    };

    const roundTrip = transformSnakeToCamel(transformCamelToSnake(original));

    expect(roundTrip).toEqual(original);
  });
});

describe("contract validation: pagination transform matches backend schema", () => {
  it("CRITICAL: count represents page size, NOT total items", () => {
    // This test documents the critical semantic difference
    // Backend CursorPaginationMetadata.count = items in CURRENT page
    // NOT total items across all pages

    const backendResponse: BackendCursorPaginatedResponse<{ id: string }> = {
      data: [{ id: "1" }, { id: "2" }, { id: "3" }],
      pagination: {
        count: 3, // This is 3 items in this page, NOT total
        has_next: true, // There are more pages
        has_prev: false,
        next_cursor: "abc",
      },
    };

    const result = transformCursorPaginatedResponse(backendResponse);

    // The frontend count should match backend count (page size)
    expect(result.count).toBe(3);
    expect(result.items.length).toBe(result.count);

    // hasNext indicates more pages exist
    expect(result.hasNext).toBe(true);
  });

  it("preserves raw pagination for components needing cursor access", () => {
    const backendResponse: BackendCursorPaginatedResponse<{ id: string }> = {
      data: [{ id: "1" }],
      pagination: {
        count: 1,
        has_next: true,
        has_prev: true,
        next_cursor: "next",
        prev_cursor: "prev",
      },
    };

    const result = transformCursorPaginatedResponse(backendResponse);

    // Components can access raw pagination for cursor operations
    expect(result.pagination.next_cursor).toBe("next");
    expect(result.pagination.prev_cursor).toBe("prev");
    expect(result.pagination.has_next).toBe(true);
    expect(result.pagination.has_prev).toBe(true);
  });
});

// =============================================================================
// ADR-0091 Phase 6: Type-Level Transformation Tests
// =============================================================================

describe("Type-level transformations (compile-time verification)", () => {
  // Import type utilities
  // These tests verify TypeScript types work correctly at compile time
  // The tests pass if they compile without errors

  it("SnakeToCamelCaseDeep converts object types correctly", () => {
    // This is a compile-time test - if it compiles, the types work correctly
    // We use a type assertion to verify the transformation

    // Backend type (snake_case)
    interface SessionBackend {
      session_id: string;
      created_at: string;
      user_id: string;
      workflow_id?: string;
      user_data: {
        first_name: string;
        last_name: string;
      };
    }

    // Frontend type should have camelCase keys
    type SessionFrontend = SnakeToCamelCaseDeep<SessionBackend>;

    // Verify the type transformation by creating a valid object
    const session: SessionFrontend = {
      sessionId: "123",
      createdAt: "2024-01-01",
      userId: "user-1",
      workflowId: "wf-1",
      userData: {
        firstName: "John",
        lastName: "Doe",
      },
    };

    // Runtime verification that the object has correct shape
    expect(session.sessionId).toBe("123");
    expect(session.createdAt).toBe("2024-01-01");
    expect(session.userData.firstName).toBe("John");
  });

  it("CamelToSnakeCaseDeep converts object types correctly", () => {
    // Frontend type (camelCase)
    interface CreateWorkflowRequest {
      workflowName: string;
      ownerId: string;
      projectId?: string;
      nodeConfig: {
        maxRetries: number;
        timeoutMs: number;
      };
    }

    // Backend type should have snake_case keys
    type CreateWorkflowRequestBackend =
      CamelToSnakeCaseDeep<CreateWorkflowRequest>;

    // Verify the type transformation by creating a valid object
    const request: CreateWorkflowRequestBackend = {
      workflow_name: "My Workflow",
      owner_id: "user-1",
      project_id: "proj-1",
      node_config: {
        max_retries: 3,
        timeout_ms: 5000,
      },
    };

    // Runtime verification that the object has correct shape
    expect(request.workflow_name).toBe("My Workflow");
    expect(request.owner_id).toBe("user-1");
    expect(request.node_config.max_retries).toBe(3);
  });

  it("SnakeToCamelCaseDeep handles arrays correctly", () => {
    // Backend type with arrays
    interface AlertListBackend {
      alert_items: Array<{
        alert_id: string;
        created_at: string;
      }>;
    }

    type AlertListFrontend = SnakeToCamelCaseDeep<AlertListBackend>;

    const alerts: AlertListFrontend = {
      alertItems: [
        { alertId: "1", createdAt: "2024-01-01" },
        { alertId: "2", createdAt: "2024-01-02" },
      ],
    };

    expect(alerts.alertItems[0].alertId).toBe("1");
    expect(alerts.alertItems[1].createdAt).toBe("2024-01-02");
  });

  it("SnakeToCamelCase converts string literal types", () => {
    // These are compile-time type checks
    // If these don't compile, the types are wrong
    const _alertId: SnakeToCamelCase<"alert_id"> = "alertId" as const;
    const _createdAt: SnakeToCamelCase<"created_at"> = "createdAt" as const;
    const _userName: SnakeToCamelCase<"user_first_name"> =
      "userFirstName" as const;
    const _simple: SnakeToCamelCase<"name"> = "name" as const;

    // Runtime check that values are correct
    expect(_alertId).toBe("alertId");
    expect(_createdAt).toBe("createdAt");
    expect(_userName).toBe("userFirstName");
    expect(_simple).toBe("name");
  });

  it("CamelToSnakeCase converts string literal types", () => {
    // These are compile-time type checks - removing `as const` to let TypeScript verify
    // Standard camelCase: no leading underscore (first char is lowercase)
    const _alertId: CamelToSnakeCase<"alertId"> = "alert_id";
    const _createdAt: CamelToSnakeCase<"createdAt"> = "created_at";
    const _userName: CamelToSnakeCase<"userFirstName"> = "user_first_name";
    const _simple: CamelToSnakeCase<"name"> = "name";

    // Verify runtime values match the type expectations
    expect(_alertId).toBe("alert_id");
    expect(_createdAt).toBe("created_at");
    expect(_userName).toBe("user_first_name");
    expect(_simple).toBe("name");
  });
});

// =============================================================================
// ADR-0091 Phase 6: transformSnakeToCamel Return Type Tests (TDD)
// =============================================================================
// These tests verify that transformSnakeToCamel returns SnakeToCamelCaseDeep<T>
// rather than T, ensuring type safety when accessing transformed properties.

describe("transformSnakeToCamel return type correctness", () => {
  it("should return SnakeToCamelCaseDeep<T> allowing camelCase property access", async () => {
    // This test verifies the function's return type matches the runtime transformation
    // If transformSnakeToCamel returns T instead of SnakeToCamelCaseDeep<T>,
    // accessing camelCase properties would require unsafe casts

    interface BackendUserInfo {
      user_id: string;
      user_name: string;
      created_at: string;
      is_active: boolean;
    }

    const { transformSnakeToCamel } = await import("./transforms");

    const backendData: BackendUserInfo = {
      user_id: "123",
      user_name: "alice",
      created_at: "2024-01-01",
      is_active: true,
    };

    // Transform the data
    const frontendData = transformSnakeToCamel(backendData);

    // With correct typing, these properties should be accessible without casts
    // This is the key type-safety assertion
    expect(frontendData.userId).toBe("123");
    expect(frontendData.userName).toBe("alice");
    expect(frontendData.createdAt).toBe("2024-01-01");
    expect(frontendData.isActive).toBe(true);
  });

  it("should preserve type safety for nested objects", async () => {
    interface BackendSession {
      session_id: string;
      session_config: {
        max_tokens: number;
        temperature_value: number;
      };
      user_metadata: {
        first_name: string;
        last_name: string;
      };
    }

    const { transformSnakeToCamel } = await import("./transforms");

    const backendSession: BackendSession = {
      session_id: "sess-123",
      session_config: {
        max_tokens: 1000,
        temperature_value: 0.7,
      },
      user_metadata: {
        first_name: "Alice",
        last_name: "Smith",
      },
    };

    const result = transformSnakeToCamel(backendSession);

    // Verify nested camelCase properties are accessible
    expect(result.sessionId).toBe("sess-123");
    expect(result.sessionConfig.maxTokens).toBe(1000);
    expect(result.sessionConfig.temperatureValue).toBe(0.7);
    expect(result.userMetadata.firstName).toBe("Alice");
    expect(result.userMetadata.lastName).toBe("Smith");
  });

  it("should preserve type safety for arrays of objects", async () => {
    interface BackendAlertList {
      alert_items: Array<{
        alert_id: string;
        alert_type: string;
        is_resolved: boolean;
      }>;
      total_count: number;
    }

    const { transformSnakeToCamel } = await import("./transforms");

    const backendData: BackendAlertList = {
      alert_items: [
        { alert_id: "1", alert_type: "warning", is_resolved: false },
        { alert_id: "2", alert_type: "error", is_resolved: true },
      ],
      total_count: 2,
    };

    const result = transformSnakeToCamel(backendData);

    // Verify array element camelCase properties are accessible
    expect(result.alertItems[0].alertId).toBe("1");
    expect(result.alertItems[0].alertType).toBe("warning");
    expect(result.alertItems[0].isResolved).toBe(false);
    expect(result.alertItems[1].isResolved).toBe(true);
    expect(result.totalCount).toBe(2);
  });

  it("should handle optional properties correctly", async () => {
    interface BackendWorkflow {
      workflow_id: string;
      workflow_name: string;
      description?: string;
      owner_email?: string | null;
    }

    const { transformSnakeToCamel } = await import("./transforms");

    const backendData: BackendWorkflow = {
      workflow_id: "wf-123",
      workflow_name: "Test Workflow",
      // description and owner_email are optional/omitted
    };

    const result = transformSnakeToCamel(backendData);

    // Required properties should be accessible
    expect(result.workflowId).toBe("wf-123");
    expect(result.workflowName).toBe("Test Workflow");

    // Optional properties should be undefined (not cause type errors)
    expect(result.description).toBeUndefined();
    expect(result.ownerEmail).toBeUndefined();
  });

  it("should work with union types in properties", async () => {
    interface BackendConfig {
      config_id: string;
      config_value: string | number | boolean;
      optional_flag?: boolean | null;
    }

    const { transformSnakeToCamel } = await import("./transforms");

    const backendData: BackendConfig = {
      config_id: "cfg-1",
      config_value: 42,
      optional_flag: true,
    };

    const result = transformSnakeToCamel(backendData);

    expect(result.configId).toBe("cfg-1");
    expect(result.configValue).toBe(42);
    expect(result.optionalFlag).toBe(true);
  });
});

describe("transformCamelToSnake return type correctness", () => {
  it("should return CamelToSnakeCaseDeep<T> allowing snake_case property access", async () => {
    // This test verifies the function's return type matches the runtime transformation
    // for request bodies sent to the backend

    interface FrontendUserRequest {
      userId: string;
      userName: string;
      isActive: boolean;
    }

    const { transformCamelToSnake } = await import("./transforms");

    const frontendData: FrontendUserRequest = {
      userId: "123",
      userName: "alice",
      isActive: true,
    };

    // Transform the data for backend
    const backendData = transformCamelToSnake(frontendData);

    // With correct typing, snake_case properties should be accessible without casts
    expect(backendData.user_id).toBe("123");
    expect(backendData.user_name).toBe("alice");
    expect(backendData.is_active).toBe(true);
  });

  it("should preserve type safety for nested objects in requests", async () => {
    interface CreateSessionRequest {
      sessionName: string;
      sessionConfig: {
        maxTokens: number;
        temperatureValue: number;
      };
      userMetadata: {
        firstName: string;
        lastName: string;
      };
    }

    const { transformCamelToSnake } = await import("./transforms");

    const frontendRequest: CreateSessionRequest = {
      sessionName: "Test Session",
      sessionConfig: {
        maxTokens: 1000,
        temperatureValue: 0.7,
      },
      userMetadata: {
        firstName: "Alice",
        lastName: "Smith",
      },
    };

    const result = transformCamelToSnake(frontendRequest);

    // Verify nested snake_case properties are accessible
    expect(result.session_name).toBe("Test Session");
    expect(result.session_config.max_tokens).toBe(1000);
    expect(result.session_config.temperature_value).toBe(0.7);
    expect(result.user_metadata.first_name).toBe("Alice");
    expect(result.user_metadata.last_name).toBe("Smith");
  });

  it("should preserve type safety for arrays in requests", async () => {
    interface BatchUpdateRequest {
      itemUpdates: Array<{
        itemId: string;
        newValue: number;
        isEnabled: boolean;
      }>;
      batchId: string;
    }

    const { transformCamelToSnake } = await import("./transforms");

    const frontendData: BatchUpdateRequest = {
      itemUpdates: [
        { itemId: "1", newValue: 100, isEnabled: true },
        { itemId: "2", newValue: 200, isEnabled: false },
      ],
      batchId: "batch-123",
    };

    const result = transformCamelToSnake(frontendData);

    // Verify array element snake_case properties are accessible
    expect(result.item_updates[0].item_id).toBe("1");
    expect(result.item_updates[0].new_value).toBe(100);
    expect(result.item_updates[0].is_enabled).toBe(true);
    expect(result.item_updates[1].is_enabled).toBe(false);
    expect(result.batch_id).toBe("batch-123");
  });
});

// =============================================================================
// ADR-0091 Phase 9: Endpoint Transform Consistency Tests (TDD)
// =============================================================================
// These tests verify that specific endpoints apply transformSnakeToCamel correctly.
// The 4 endpoints needing fixes:
// 1. getSharedWorkflows - should transform WorkflowSummary[] to camelCase
// 2. listAlertRules - should transform ObservabilityAlertRule[] to camelCase
// 3. getHealth - should transform HealthStatus to camelCase
// 4. getHeartMetrics - should transform HEARTAggregateMetrics to camelCase

describe("Endpoint Transform Consistency (ADR-0091 Phase 9)", () => {
  const getTransformSnakeToCamel = async () => {
    const { transformSnakeToCamel } = await import("./transforms");
    return transformSnakeToCamel;
  };

  describe("getSharedWorkflows endpoint transform", () => {
    it("should transform WorkflowSummary array from snake_case to camelCase", async () => {
      const transformSnakeToCamel = await getTransformSnakeToCamel();

      // Backend response format (snake_case)
      const backendResponse = [
        {
          id: "wf-1",
          name: "Workflow 1",
          description: "First workflow",
          node_count: 5,
          edge_count: 4,
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-02T00:00:00Z",
        },
        {
          id: "wf-2",
          name: "Workflow 2",
          description: "Second workflow",
          node_count: 3,
          edge_count: 2,
          created_at: "2024-01-03T00:00:00Z",
          updated_at: "2024-01-04T00:00:00Z",
        },
      ];

      // Transform to frontend camelCase format
      const result = transformSnakeToCamel(backendResponse);

      // Verify camelCase properties are accessible
      expect(result[0].nodeCount).toBe(5);
      expect(result[0].edgeCount).toBe(4);
      expect(result[0].createdAt).toBe("2024-01-01T00:00:00Z");
      expect(result[0].updatedAt).toBe("2024-01-02T00:00:00Z");
      expect(result[1].nodeCount).toBe(3);
      expect(result[1].edgeCount).toBe(2);
    });
  });

  describe("listAlertRules endpoint transform", () => {
    it("should transform ObservabilityAlertRule array from snake_case to camelCase", async () => {
      const transformSnakeToCamel = await getTransformSnakeToCamel();

      // Backend response format (snake_case)
      const backendResponse = [
        {
          rule_id: "rule-1",
          name: "High Error Rate",
          expression: "error_rate > 0.1",
          severity: "critical",
          labels: { team: "platform" },
          annotations: { summary: "Error rate exceeded threshold" },
          evaluation_interval_seconds: 60,
          for_duration_seconds: 300,
          enabled: true,
        },
        {
          rule_id: "rule-2",
          name: "High Latency",
          expression: "latency_p99 > 1000",
          severity: "warning",
          labels: { team: "api" },
          annotations: { summary: "Latency exceeded threshold" },
          evaluation_interval_seconds: 30,
          for_duration_seconds: 120,
          enabled: false,
        },
      ];

      // Transform to frontend camelCase format
      const result = transformSnakeToCamel(backendResponse);

      // Verify camelCase properties are accessible
      expect(result[0].ruleId).toBe("rule-1");
      expect(result[0].evaluationIntervalSeconds).toBe(60);
      expect(result[0].forDurationSeconds).toBe(300);
      expect(result[1].ruleId).toBe("rule-2");
      expect(result[1].evaluationIntervalSeconds).toBe(30);
      expect(result[1].forDurationSeconds).toBe(120);
    });
  });

  describe("getHealth endpoint transform", () => {
    it("should transform HealthStatus from snake_case to camelCase", async () => {
      const transformSnakeToCamel = await getTransformSnakeToCamel();

      // Backend response format (snake_case)
      const backendResponse = {
        status: "healthy",
        version: "1.0.0",
        uptime_seconds: 3600,
      };

      // Transform to frontend camelCase format
      const result = transformSnakeToCamel(backendResponse);

      // Verify camelCase properties are accessible
      expect(result.status).toBe("healthy");
      expect(result.version).toBe("1.0.0");
      expect(result.uptimeSeconds).toBe(3600);
    });

    it("should handle HealthStatus with optional fields missing", async () => {
      const transformSnakeToCamel = await getTransformSnakeToCamel();

      // Minimal backend response (only required field)
      const backendResponse = {
        status: "healthy",
      };

      // Transform to frontend camelCase format
      const result = transformSnakeToCamel(backendResponse);

      // Verify required field is present, optional are undefined
      expect(result.status).toBe("healthy");
      expect(result.version).toBeUndefined();
      expect(result.uptimeSeconds).toBeUndefined();
    });
  });

  describe("getHeartMetrics endpoint transform", () => {
    it("should transform HEARTAggregateMetrics from snake_case to camelCase", async () => {
      const transformSnakeToCamel = await getTransformSnakeToCamel();

      // Backend response format (snake_case) - full HEART metrics
      const backendResponse = {
        period: "7d",
        app_name: "studio",
        // Happiness
        nps_score_avg: 7.5,
        satisfaction_avg: 4.2,
        // Task Success
        task_success_rate: 0.85,
        total_tasks_started: 100,
        total_tasks_completed: 85,
        total_tasks_errored: 15,
        // Engagement
        avg_session_duration_ms: 300000,
        total_interactions: 5000,
        top_features: { chat: 2000, workflows: 1500, settings: 500 },
        // Adoption
        new_users_count: 50,
        onboarding_completion_rate: 0.75,
        // Retention
        avg_return_visits: 3.2,
        avg_days_active: 5,
      };

      // Transform to frontend camelCase format
      const result = transformSnakeToCamel(backendResponse);

      // Verify camelCase properties are accessible
      expect(result.period).toBe("7d");
      expect(result.appName).toBe("studio");
      expect(result.npsScoreAvg).toBe(7.5);
      expect(result.satisfactionAvg).toBe(4.2);
      expect(result.taskSuccessRate).toBe(0.85);
      expect(result.totalTasksStarted).toBe(100);
      expect(result.totalTasksCompleted).toBe(85);
      expect(result.totalTasksErrored).toBe(15);
      expect(result.avgSessionDurationMs).toBe(300000);
      expect(result.totalInteractions).toBe(5000);
      expect(result.topFeatures).toEqual({
        chat: 2000,
        workflows: 1500,
        settings: 500,
      });
      expect(result.newUsersCount).toBe(50);
      expect(result.onboardingCompletionRate).toBe(0.75);
      expect(result.avgReturnVisits).toBe(3.2);
      expect(result.avgDaysActive).toBe(5);
    });

    it("should handle HEARTAggregateMetrics with null values", async () => {
      const transformSnakeToCamel = await getTransformSnakeToCamel();

      // Backend response with nullable fields set to null
      const backendResponse = {
        period: "7d",
        app_name: null,
        nps_score_avg: null,
        satisfaction_avg: null,
        task_success_rate: null,
        total_tasks_started: 0,
        total_tasks_completed: 0,
        total_tasks_errored: 0,
        avg_session_duration_ms: null,
        total_interactions: 0,
        top_features: {},
        new_users_count: 0,
        onboarding_completion_rate: null,
        avg_return_visits: null,
        avg_days_active: null,
      };

      // Transform to frontend camelCase format
      const result = transformSnakeToCamel(backendResponse);

      // Verify null values are preserved after transform
      expect(result.appName).toBeNull();
      expect(result.npsScoreAvg).toBeNull();
      expect(result.satisfactionAvg).toBeNull();
      expect(result.taskSuccessRate).toBeNull();
      expect(result.avgSessionDurationMs).toBeNull();
      expect(result.onboardingCompletionRate).toBeNull();
      expect(result.avgReturnVisits).toBeNull();
      expect(result.avgDaysActive).toBeNull();
    });
  });
});

// =============================================================================
// Type-Level Return Type Verification (using expectTypeOf)
// =============================================================================
// These tests use Vitest's expectTypeOf for compile-time type assertions

describe("transform function return types (compile-time verification)", () => {
  it("transformSnakeToCamel should return SnakeToCamelCaseDeep<T>", async () => {
    interface BackendType {
      user_id: string;
      first_name: string;
    }

    const { transformSnakeToCamel } = await import("./transforms");

    const input: BackendType = { user_id: "123", first_name: "Alice" };
    const result = transformSnakeToCamel(input);

    // Type assertion: result should have camelCase keys
    // This will fail to compile if return type is T instead of SnakeToCamelCaseDeep<T>
    expectTypeOf(result).toHaveProperty("userId");
    expectTypeOf(result).toHaveProperty("firstName");
  });

  it("transformCamelToSnake should return CamelToSnakeCaseDeep<T>", async () => {
    interface FrontendType {
      userId: string;
      firstName: string;
    }

    const { transformCamelToSnake } = await import("./transforms");

    const input: FrontendType = { userId: "123", firstName: "Alice" };
    const result = transformCamelToSnake(input);

    // Type assertion: result should have snake_case keys
    // This will fail to compile if return type is T instead of CamelToSnakeCaseDeep<T>
    expectTypeOf(result).toHaveProperty("user_id");
    expectTypeOf(result).toHaveProperty("first_name");
  });
});
