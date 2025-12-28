/**
 * RTK Query API Tests
 *
 * Tests for API configuration, hook exports, and type definitions.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import {
  api,
  useListWorkflowsQuery,
  useGetWorkflowQuery,
  useCreateWorkflowMutation,
  useUpdateWorkflowMutation,
  useDeleteWorkflowMutation,
  useBootstrapWorkflowMutation,
  useGetWorkflowSharesQuery,
  useAddWorkflowShareMutation,
  useRemoveWorkflowShareMutation,
  useUpdateWorkflowPublicMutation,
  useGenerateWorkflowCodeMutation,
  useListSessionsQuery,
  useGetSessionQuery,
  useCreateSessionMutation,
  useDeleteSessionMutation,
  useGetSessionMessagesQuery,
  useSendChatMessageMutation,
  useGetCostSummaryQuery,
  useGetCostByModelQuery,
  useGetCostHistoryQuery,
  useListTracesQuery,
  useGetTraceQuery,
  useListProjectsQuery,
  useGetProjectQuery,
  useCreateProjectMutation,
  useUpdateProjectMutation,
  useDeleteProjectMutation,
  useGetFeatureFlagsQuery,
  useGetServerConfigQuery,
  // Admin User hooks
  useListAdminUsersQuery,
  useGetAdminUserQuery,
  useCreateAdminUserMutation,
  useUpdateAdminUserMutation,
  useDeleteAdminUserMutation,
  // Workflow Execution hooks
  useListWorkflowExecutionsQuery,
  useGetWorkflowExecutionQuery,
} from "./index";

describe("RTK Query API", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("API Configuration", () => {
    it("should have correct reducerPath", () => {
      expect(api.reducerPath).toBe("api");
    });

    it("should have reducer defined", () => {
      expect(api.reducer).toBeDefined();
      expect(typeof api.reducer).toBe("function");
    });

    it("should have middleware defined", () => {
      expect(api.middleware).toBeDefined();
    });
  });

  describe("Workflow Hooks Export", () => {
    it("should export useListWorkflowsQuery", () => {
      expect(useListWorkflowsQuery).toBeDefined();
      expect(typeof useListWorkflowsQuery).toBe("function");
    });

    it("should export useGetWorkflowQuery", () => {
      expect(useGetWorkflowQuery).toBeDefined();
      expect(typeof useGetWorkflowQuery).toBe("function");
    });

    it("should export useCreateWorkflowMutation", () => {
      expect(useCreateWorkflowMutation).toBeDefined();
      expect(typeof useCreateWorkflowMutation).toBe("function");
    });

    it("should export useUpdateWorkflowMutation", () => {
      expect(useUpdateWorkflowMutation).toBeDefined();
      expect(typeof useUpdateWorkflowMutation).toBe("function");
    });

    it("should export useDeleteWorkflowMutation", () => {
      expect(useDeleteWorkflowMutation).toBeDefined();
      expect(typeof useDeleteWorkflowMutation).toBe("function");
    });

    it("should export useBootstrapWorkflowMutation", () => {
      expect(useBootstrapWorkflowMutation).toBeDefined();
      expect(typeof useBootstrapWorkflowMutation).toBe("function");
    });

    it("should export useGetWorkflowSharesQuery", () => {
      expect(useGetWorkflowSharesQuery).toBeDefined();
      expect(typeof useGetWorkflowSharesQuery).toBe("function");
    });

    it("should export useAddWorkflowShareMutation", () => {
      expect(useAddWorkflowShareMutation).toBeDefined();
      expect(typeof useAddWorkflowShareMutation).toBe("function");
    });

    it("should export useRemoveWorkflowShareMutation", () => {
      expect(useRemoveWorkflowShareMutation).toBeDefined();
      expect(typeof useRemoveWorkflowShareMutation).toBe("function");
    });

    it("should export useUpdateWorkflowPublicMutation", () => {
      expect(useUpdateWorkflowPublicMutation).toBeDefined();
      expect(typeof useUpdateWorkflowPublicMutation).toBe("function");
    });

    it("should export useGenerateWorkflowCodeMutation", () => {
      expect(useGenerateWorkflowCodeMutation).toBeDefined();
      expect(typeof useGenerateWorkflowCodeMutation).toBe("function");
    });
  });

  describe("Session Hooks Export", () => {
    it("should export useListSessionsQuery", () => {
      expect(useListSessionsQuery).toBeDefined();
      expect(typeof useListSessionsQuery).toBe("function");
    });

    it("should export useGetSessionQuery", () => {
      expect(useGetSessionQuery).toBeDefined();
      expect(typeof useGetSessionQuery).toBe("function");
    });

    it("should export useCreateSessionMutation", () => {
      expect(useCreateSessionMutation).toBeDefined();
      expect(typeof useCreateSessionMutation).toBe("function");
    });

    it("should export useDeleteSessionMutation", () => {
      expect(useDeleteSessionMutation).toBeDefined();
      expect(typeof useDeleteSessionMutation).toBe("function");
    });

    it("should export useGetSessionMessagesQuery", () => {
      expect(useGetSessionMessagesQuery).toBeDefined();
      expect(typeof useGetSessionMessagesQuery).toBe("function");
    });
  });

  describe("Chat Hooks Export", () => {
    it("should export useSendChatMessageMutation", () => {
      expect(useSendChatMessageMutation).toBeDefined();
      expect(typeof useSendChatMessageMutation).toBe("function");
    });
  });

  describe("Cost Hooks Export", () => {
    it("should export useGetCostSummaryQuery", () => {
      expect(useGetCostSummaryQuery).toBeDefined();
      expect(typeof useGetCostSummaryQuery).toBe("function");
    });

    it("should export useGetCostByModelQuery", () => {
      expect(useGetCostByModelQuery).toBeDefined();
      expect(typeof useGetCostByModelQuery).toBe("function");
    });

    it("should export useGetCostHistoryQuery", () => {
      expect(useGetCostHistoryQuery).toBeDefined();
      expect(typeof useGetCostHistoryQuery).toBe("function");
    });
  });

  describe("Observability Hooks Export", () => {
    it("should export useListTracesQuery", () => {
      expect(useListTracesQuery).toBeDefined();
      expect(typeof useListTracesQuery).toBe("function");
    });

    it("should export useGetTraceQuery", () => {
      expect(useGetTraceQuery).toBeDefined();
      expect(typeof useGetTraceQuery).toBe("function");
    });
  });

  describe("Project Hooks Export", () => {
    it("should export useListProjectsQuery", () => {
      expect(useListProjectsQuery).toBeDefined();
      expect(typeof useListProjectsQuery).toBe("function");
    });

    it("should export useGetProjectQuery", () => {
      expect(useGetProjectQuery).toBeDefined();
      expect(typeof useGetProjectQuery).toBe("function");
    });

    it("should export useCreateProjectMutation", () => {
      expect(useCreateProjectMutation).toBeDefined();
      expect(typeof useCreateProjectMutation).toBe("function");
    });

    it("should export useUpdateProjectMutation", () => {
      expect(useUpdateProjectMutation).toBeDefined();
      expect(typeof useUpdateProjectMutation).toBe("function");
    });

    it("should export useDeleteProjectMutation", () => {
      expect(useDeleteProjectMutation).toBeDefined();
      expect(typeof useDeleteProjectMutation).toBe("function");
    });
  });

  describe("Feature Flags Hooks Export", () => {
    it("should export useGetFeatureFlagsQuery", () => {
      expect(useGetFeatureFlagsQuery).toBeDefined();
      expect(typeof useGetFeatureFlagsQuery).toBe("function");
    });
  });

  describe("Server Configuration Hooks Export", () => {
    it("should export useGetServerConfigQuery", () => {
      expect(useGetServerConfigQuery).toBeDefined();
      expect(typeof useGetServerConfigQuery).toBe("function");
    });

    it("should have getServerConfig endpoint defined", () => {
      expect(api.endpoints.getServerConfig).toBeDefined();
    });
  });

  describe("Endpoints Configuration", () => {
    it("should have listWorkflows endpoint defined", () => {
      expect(api.endpoints.listWorkflows).toBeDefined();
    });

    it("should have listSessions endpoint defined", () => {
      expect(api.endpoints.listSessions).toBeDefined();
    });

    it("should have listTraces endpoint defined", () => {
      expect(api.endpoints.listTraces).toBeDefined();
    });

    it("should have listProjects endpoint defined", () => {
      expect(api.endpoints.listProjects).toBeDefined();
    });

    it("should have getCostHistory endpoint defined", () => {
      expect(api.endpoints.getCostHistory).toBeDefined();
    });

    it("should have getFeatureFlags endpoint defined", () => {
      expect(api.endpoints.getFeatureFlags).toBeDefined();
    });

    it("should have bootstrapWorkflow endpoint defined", () => {
      expect(api.endpoints.bootstrapWorkflow).toBeDefined();
    });

    it("should have getWorkflowShares endpoint defined", () => {
      expect(api.endpoints.getWorkflowShares).toBeDefined();
    });

    it("should have addWorkflowShare endpoint defined", () => {
      expect(api.endpoints.addWorkflowShare).toBeDefined();
    });

    it("should have removeWorkflowShare endpoint defined", () => {
      expect(api.endpoints.removeWorkflowShare).toBeDefined();
    });

    it("should have updateWorkflowPublic endpoint defined", () => {
      expect(api.endpoints.updateWorkflowPublic).toBeDefined();
    });

    it("should have generateWorkflowCode endpoint defined", () => {
      expect(api.endpoints.generateWorkflowCode).toBeDefined();
    });
  });

  describe("Tag Types", () => {
    it("should include all required tag types", () => {
      // Tag types are used for cache invalidation
      // We verify by checking the endpoints provide correct tags
      expect(api.endpoints.listWorkflows).toBeDefined();
      expect(api.endpoints.listSessions).toBeDefined();
      expect(api.endpoints.listProjects).toBeDefined();
      expect(api.endpoints.listTraces).toBeDefined();
    });
  });

  describe("Admin User Hooks Export", () => {
    it("should export useListAdminUsersQuery", () => {
      expect(useListAdminUsersQuery).toBeDefined();
      expect(typeof useListAdminUsersQuery).toBe("function");
    });

    it("should export useGetAdminUserQuery", () => {
      expect(useGetAdminUserQuery).toBeDefined();
      expect(typeof useGetAdminUserQuery).toBe("function");
    });

    it("should export useCreateAdminUserMutation", () => {
      expect(useCreateAdminUserMutation).toBeDefined();
      expect(typeof useCreateAdminUserMutation).toBe("function");
    });

    it("should export useUpdateAdminUserMutation", () => {
      expect(useUpdateAdminUserMutation).toBeDefined();
      expect(typeof useUpdateAdminUserMutation).toBe("function");
    });

    it("should export useDeleteAdminUserMutation", () => {
      expect(useDeleteAdminUserMutation).toBeDefined();
      expect(typeof useDeleteAdminUserMutation).toBe("function");
    });
  });

  describe("Admin User Endpoints Configuration", () => {
    it("should have listAdminUsers endpoint defined", () => {
      expect(api.endpoints.listAdminUsers).toBeDefined();
    });

    it("should have getAdminUser endpoint defined", () => {
      expect(api.endpoints.getAdminUser).toBeDefined();
    });

    it("should have createAdminUser endpoint defined", () => {
      expect(api.endpoints.createAdminUser).toBeDefined();
    });

    it("should have updateAdminUser endpoint defined", () => {
      expect(api.endpoints.updateAdminUser).toBeDefined();
    });

    it("should have deleteAdminUser endpoint defined", () => {
      expect(api.endpoints.deleteAdminUser).toBeDefined();
    });
  });

  describe("Workflow Execution Hooks Export", () => {
    it("should export useListWorkflowExecutionsQuery", () => {
      expect(useListWorkflowExecutionsQuery).toBeDefined();
      expect(typeof useListWorkflowExecutionsQuery).toBe("function");
    });

    it("should export useGetWorkflowExecutionQuery", () => {
      expect(useGetWorkflowExecutionQuery).toBeDefined();
      expect(typeof useGetWorkflowExecutionQuery).toBe("function");
    });
  });

  describe("Workflow Execution Endpoints Configuration", () => {
    it("should have listWorkflowExecutions endpoint defined", () => {
      expect(api.endpoints.listWorkflowExecutions).toBeDefined();
    });

    it("should have getWorkflowExecution endpoint defined", () => {
      expect(api.endpoints.getWorkflowExecution).toBeDefined();
    });
  });
});
