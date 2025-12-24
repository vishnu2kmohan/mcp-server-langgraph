/**
 * Tests for API Transform Helpers
 *
 * Validates cursor pagination transforms between backend and frontend formats.
 */

import { afterEach, describe, expect, it, vi } from "vitest";

import type { BackendCursorPaginatedResponse } from "../types/api";
import {
  extractPaginationMetadata,
  isCursorPaginatedResponse,
  transformCursorPaginatedResponse,
  transformToLegacyPaginatedResponse,
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
