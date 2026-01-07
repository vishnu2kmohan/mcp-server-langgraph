/**
 * API Contract Tests - AI URL Fetch Endpoint
 *
 * Tests for the AI fetch URL endpoint.
 */

import { describe, it, expect, afterEach, vi } from "vitest";

import {
  isFetchUrlResponse,
  isFetchUrlErrorResponse,
} from "./contract.validators.test-utils";

// Clean up after each test
afterEach(() => {
  vi.clearAllMocks();
});

// =============================================================================
// AI Fetch URL Endpoint Tests
// =============================================================================

describe("AI Fetch URL Endpoint", () => {
  it("should validate successful FetchUrlResponse schema", () => {
    const validResponse = {
      url: "https://example.com",
      title: "Example Domain",
      content: "This domain is for use in illustrative examples...",
      content_type: "text/html",
    };
    expect(isFetchUrlResponse(validResponse)).toBe(true);
  });

  it("should validate FetchUrlResponse with null optional fields", () => {
    const validResponse = {
      url: "https://example.com/api",
      title: null,
      content: '{"key": "value"}',
      content_type: "application/json",
    };
    expect(isFetchUrlResponse(validResponse)).toBe(true);
  });

  it("should validate FetchUrlResponse with error field", () => {
    const validResponse = {
      url: "https://example.com/notfound",
      error: "Page not found",
      status_code: 404,
    };
    expect(isFetchUrlResponse(validResponse)).toBe(true);
  });

  it("should validate minimal FetchUrlResponse (URL only)", () => {
    const minimalResponse = {
      url: "https://example.com",
    };
    expect(isFetchUrlResponse(minimalResponse)).toBe(true);
  });

  it("should validate SSRF error response schema", () => {
    const errorResponse = {
      detail: "URL blocked: Private IP addresses are not allowed",
    };
    expect(isFetchUrlErrorResponse(errorResponse)).toBe(true);
  });

  it("should reject FetchUrlResponse with missing url field", () => {
    const invalidResponse = {
      title: "Example",
      content: "Some content",
    };
    expect(isFetchUrlResponse(invalidResponse)).toBe(false);
  });

  it("should validate FetchUrlResponse with all optional fields", () => {
    const fullResponse = {
      url: "https://docs.example.com/guide",
      title: "Documentation Guide",
      content: "# Getting Started\n\nWelcome to our documentation...",
      content_type: "text/html; charset=utf-8",
      error: null,
      status_code: 200,
    };
    expect(isFetchUrlResponse(fullResponse)).toBe(true);
  });

  it("should validate FetchUrlResponse with timeout error", () => {
    const timeoutResponse = {
      url: "https://slow-server.example.com",
      error: "Request timed out after 30 seconds",
      status_code: null,
    };
    expect(isFetchUrlResponse(timeoutResponse)).toBe(true);
  });
});
