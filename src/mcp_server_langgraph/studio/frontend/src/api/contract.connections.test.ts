/**
 * API Contract Tests - Connection Templates, Audit, and Bulk Operations
 *
 * Tests for connection management endpoints.
 */

import { describe, it, expect, afterEach, vi } from "vitest";

import {
  isTemplateCategory,
  isCategoryListResponse,
  isConnectionTemplate,
  isTemplateListResponse,
  isConnectionAuditLogEntry,
  isAuditLogListResponse,
  isBulkDeleteResponse,
  isBulkTestResponse,
  isBulkStatusResponse,
  isConnectionTestResult,
} from "./contract.validators.test-utils";

// Clean up after each test
afterEach(() => {
  vi.clearAllMocks();
});

// =============================================================================
// Connection Templates Endpoints Tests
// =============================================================================

describe("Connection Templates Endpoints", () => {
  it("should validate TemplateCategory schema", () => {
    const validResponse = {
      id: "databases",
      name: "Databases",
      description: "Database connection templates",
    };
    expect(isTemplateCategory(validResponse)).toBe(true);
  });

  it("should validate CategoryListResponse schema", () => {
    const validResponse = {
      categories: [
        {
          id: "databases",
          name: "Databases",
          description: "Database connections",
        },
        { id: "apis", name: "APIs", description: "API connections" },
      ],
    };
    expect(isCategoryListResponse(validResponse)).toBe(true);
  });

  it("should validate ConnectionTemplate schema", () => {
    const validResponse = {
      id: "postgres-template",
      name: "PostgreSQL",
      description: "PostgreSQL database connection",
      category: "databases",
      icon: "postgres",
      default_url: "postgresql://localhost:5432",
      auth_type: "api_key",
    };
    expect(isConnectionTemplate(validResponse)).toBe(true);
  });

  it("should validate TemplateListResponse schema", () => {
    const validResponse = {
      templates: [
        {
          id: "postgres-template",
          name: "PostgreSQL",
          description: "PostgreSQL database",
          category: "databases",
          icon: "postgres",
          default_url: "postgresql://localhost:5432",
          auth_type: "none",
        },
      ],
    };
    expect(isTemplateListResponse(validResponse)).toBe(true);
  });
});

// =============================================================================
// Connection Audit Endpoints Tests
// =============================================================================

describe("Connection Audit Endpoints", () => {
  it("should validate ConnectionAuditLogEntry schema", () => {
    const validResponse = {
      id: "audit-001",
      timestamp: "2025-01-15T10:30:00Z",
      connection_id: "conn-123",
      event_type: "connection_created",
      user_id: "user-001",
      details: { name: "New Connection" },
    };
    expect(isConnectionAuditLogEntry(validResponse)).toBe(true);
  });

  it("should validate AuditLogListResponse schema", () => {
    const validResponse = {
      logs: [
        {
          id: "audit-001",
          timestamp: "2025-01-15T10:30:00Z",
          connection_id: "conn-123",
          event_type: "connection_created",
          user_id: "user-001",
        },
      ],
      total: 1,
    };
    expect(isAuditLogListResponse(validResponse)).toBe(true);
  });
});

// =============================================================================
// Connections Bulk Endpoints Tests
// =============================================================================

describe("Connections Bulk Endpoints", () => {
  it("should validate BulkDeleteResponse schema", () => {
    const validResponse = {
      deleted_count: 5,
      failed_ids: ["conn-003"],
    };
    expect(isBulkDeleteResponse(validResponse)).toBe(true);
  });

  it("should allow empty failed_ids in BulkDeleteResponse", () => {
    const validResponse = {
      deleted_count: 10,
    };
    expect(isBulkDeleteResponse(validResponse)).toBe(true);
  });

  it("should validate BulkTestResponse schema", () => {
    const validResponse = {
      results: [
        {
          connection_id: "conn-001",
          success: true,
          server_name: "Test Server",
          server_version: "1.0.0",
          tool_count: 5,
        },
        {
          connection_id: "conn-002",
          success: false,
          error: "Connection refused",
          tool_count: 0,
        },
      ],
      not_found: ["conn-003"],
    };
    expect(isBulkTestResponse(validResponse)).toBe(true);
  });

  it("should validate BulkStatusResponse schema", () => {
    const validResponse = {
      updated_count: 3,
      failed_ids: [],
    };
    expect(isBulkStatusResponse(validResponse)).toBe(true);
  });

  it("should validate ConnectionTestResult schema", () => {
    const validResponse = {
      connection_id: "conn-001",
      success: true,
      server_name: "MCP Server",
      server_version: "2.0.0",
      tool_count: 10,
    };
    expect(isConnectionTestResult(validResponse)).toBe(true);
  });

  it("should validate failed ConnectionTestResult", () => {
    const validResponse = {
      connection_id: "conn-002",
      success: false,
      error: "Authentication failed",
      tool_count: 0,
    };
    expect(isConnectionTestResult(validResponse)).toBe(true);
  });
});
