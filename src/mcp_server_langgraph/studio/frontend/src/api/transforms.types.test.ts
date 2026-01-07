/**
 * Tests for Type-Level Transformations
 *
 * ADR-0091 Phase 6: Type-Level Transformation Tests
 * These tests verify TypeScript types work correctly at compile time.
 * The tests pass if they compile without errors.
 */

import { afterEach, describe, expect, expectTypeOf, it, vi } from "vitest";

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
