/**
 * chatConnectionSlice Tests
 *
 * Tests for Redux slice managing connection awareness in chat.
 * Handles auth_required events, connection setup state, and connector suggestions.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import chatConnectionReducer, {
  addAuthRequirement,
  dismissAuthRequirement,
  startConnectionSetup,
  updateConnectionSetupStatus,
  completeConnectionSetup,
  showSuggestions,
  hideSuggestions,
  setConfiguredTemplateIds,
  clearPendingAuthRequirements,
  selectPendingAuthRequirements,
  selectActiveConnectionSetup,
  selectConnectorSuggestions,
  selectConfiguredTemplateIds,
  type ChatConnectionState,
} from "./chatConnectionSlice";

afterEach(() => {
  vi.clearAllMocks();
});

describe("chatConnectionSlice", () => {
  const initialState: ChatConnectionState = {
    pendingAuthRequirements: [],
    activeConnectionSetup: null,
    connectorSuggestions: {
      visible: false,
      templates: [],
      query: "",
    },
    configuredTemplateIds: [],
  };

  describe("Initial State", () => {
    it("should have correct initial state", () => {
      const state = chatConnectionReducer(undefined, { type: "unknown" });
      expect(state).toEqual(initialState);
    });
  });

  describe("Auth Requirements", () => {
    it("should add auth requirement with generated id and timestamp", () => {
      const authReq = {
        toolName: "github:list_prs",
        templateId: "github",
        connectionId: null,
        message: "Authentication required",
        retryMessageId: "msg-123",
      };

      const state = chatConnectionReducer(
        initialState,
        addAuthRequirement(authReq),
      );

      expect(state.pendingAuthRequirements).toHaveLength(1);
      expect(state.pendingAuthRequirements[0].toolName).toBe("github:list_prs");
      expect(state.pendingAuthRequirements[0].templateId).toBe("github");
      expect(state.pendingAuthRequirements[0].id).toBeDefined();
      expect(state.pendingAuthRequirements[0].timestamp).toBeDefined();
    });

    it("should accumulate multiple auth requirements", () => {
      let state = chatConnectionReducer(
        initialState,
        addAuthRequirement({
          toolName: "github:list_prs",
          templateId: "github",
          connectionId: null,
          message: "Auth needed",
          retryMessageId: null,
        }),
      );

      state = chatConnectionReducer(
        state,
        addAuthRequirement({
          toolName: "slack:post_message",
          templateId: "slack",
          connectionId: "conn-1",
          message: "Re-auth needed",
          retryMessageId: "msg-2",
        }),
      );

      expect(state.pendingAuthRequirements).toHaveLength(2);
      expect(state.pendingAuthRequirements[0].toolName).toBe("github:list_prs");
      expect(state.pendingAuthRequirements[1].toolName).toBe(
        "slack:post_message",
      );
    });

    it("should dismiss auth requirement by id", () => {
      const state1 = chatConnectionReducer(
        initialState,
        addAuthRequirement({
          toolName: "github:list_prs",
          templateId: "github",
          connectionId: null,
          message: "Auth needed",
          retryMessageId: null,
        }),
      );

      const reqId = state1.pendingAuthRequirements[0].id;
      const state2 = chatConnectionReducer(
        state1,
        dismissAuthRequirement(reqId),
      );

      expect(state2.pendingAuthRequirements).toHaveLength(0);
    });

    it("should clear all pending auth requirements", () => {
      let state = chatConnectionReducer(
        initialState,
        addAuthRequirement({
          toolName: "github:list_prs",
          templateId: "github",
          connectionId: null,
          message: "Auth needed",
          retryMessageId: null,
        }),
      );

      state = chatConnectionReducer(
        state,
        addAuthRequirement({
          toolName: "slack:post_message",
          templateId: "slack",
          connectionId: null,
          message: "Auth needed",
          retryMessageId: null,
        }),
      );

      expect(state.pendingAuthRequirements).toHaveLength(2);

      state = chatConnectionReducer(state, clearPendingAuthRequirements());

      expect(state.pendingAuthRequirements).toHaveLength(0);
    });
  });

  describe("Connection Setup", () => {
    it("should start connection setup with template only", () => {
      const state = chatConnectionReducer(
        initialState,
        startConnectionSetup({ templateId: "github" }),
      );

      expect(state.activeConnectionSetup).toEqual({
        templateId: "github",
        connectionId: undefined,
        status: "configuring",
        error: undefined,
      });
    });

    it("should start connection setup with existing connection", () => {
      const state = chatConnectionReducer(
        initialState,
        startConnectionSetup({
          templateId: "slack",
          connectionId: "conn-456",
        }),
      );

      expect(state.activeConnectionSetup).toEqual({
        templateId: "slack",
        connectionId: "conn-456",
        status: "configuring",
        error: undefined,
      });
    });

    it("should update connection setup status", () => {
      let state = chatConnectionReducer(
        initialState,
        startConnectionSetup({ templateId: "github" }),
      );

      state = chatConnectionReducer(
        state,
        updateConnectionSetupStatus({ status: "authenticating" }),
      );

      expect(state.activeConnectionSetup?.status).toBe("authenticating");
    });

    it("should update connection setup with error", () => {
      let state = chatConnectionReducer(
        initialState,
        startConnectionSetup({ templateId: "github" }),
      );

      state = chatConnectionReducer(
        state,
        updateConnectionSetupStatus({
          status: "error",
          error: "OAuth popup was blocked",
        }),
      );

      expect(state.activeConnectionSetup?.status).toBe("error");
      expect(state.activeConnectionSetup?.error).toBe(
        "OAuth popup was blocked",
      );
    });

    it("should complete connection setup and add to configured list", () => {
      let state = chatConnectionReducer(
        initialState,
        startConnectionSetup({ templateId: "github" }),
      );

      state = chatConnectionReducer(state, completeConnectionSetup());

      expect(state.activeConnectionSetup).toBeNull();
      expect(state.configuredTemplateIds).toContain("github");
    });

    it("should not update status when no active setup", () => {
      const state = chatConnectionReducer(
        initialState,
        updateConnectionSetupStatus({ status: "authenticating" }),
      );

      expect(state.activeConnectionSetup).toBeNull();
    });
  });

  describe("Connector Suggestions", () => {
    it("should show suggestions with templates and query", () => {
      const templates = [
        { id: "github", name: "GitHub" },
        { id: "slack", name: "Slack" },
      ];

      const state = chatConnectionReducer(
        initialState,
        showSuggestions({ templates, query: "check my github prs" }),
      );

      expect(state.connectorSuggestions.visible).toBe(true);
      expect(state.connectorSuggestions.templates).toEqual(templates);
      expect(state.connectorSuggestions.query).toBe("check my github prs");
    });

    it("should hide suggestions", () => {
      const stateWithSuggestions = {
        ...initialState,
        connectorSuggestions: {
          visible: true,
          templates: [{ id: "github", name: "GitHub" }],
          query: "github",
        },
      };

      const state = chatConnectionReducer(
        stateWithSuggestions,
        hideSuggestions(),
      );

      expect(state.connectorSuggestions.visible).toBe(false);
      // Templates and query should remain for potential re-show
    });
  });

  describe("Configured Template IDs", () => {
    it("should set configured template IDs", () => {
      const state = chatConnectionReducer(
        initialState,
        setConfiguredTemplateIds(["github", "slack", "notion"]),
      );

      expect(state.configuredTemplateIds).toEqual([
        "github",
        "slack",
        "notion",
      ]);
    });

    it("should replace existing configured template IDs", () => {
      const stateWithIds = {
        ...initialState,
        configuredTemplateIds: ["old-id-1", "old-id-2"],
      };

      const state = chatConnectionReducer(
        stateWithIds,
        setConfiguredTemplateIds(["new-id-1"]),
      );

      expect(state.configuredTemplateIds).toEqual(["new-id-1"]);
    });
  });

  describe("Selectors", () => {
    const mockRootState = {
      chatConnection: {
        pendingAuthRequirements: [
          {
            id: "req-1",
            toolName: "github:list_prs",
            templateId: "github",
            connectionId: null,
            message: "Auth needed",
            retryMessageId: null,
            timestamp: Date.now(),
          },
        ],
        activeConnectionSetup: {
          templateId: "slack",
          connectionId: "conn-1",
          status: "authenticating" as const,
          error: undefined,
        },
        connectorSuggestions: {
          visible: true,
          templates: [{ id: "notion", name: "Notion" }],
          query: "create notion page",
        },
        configuredTemplateIds: ["jira", "linear"],
      },
    };

    it("should select pending auth requirements", () => {
      const result = selectPendingAuthRequirements(mockRootState);
      expect(result).toHaveLength(1);
      expect(result[0].toolName).toBe("github:list_prs");
    });

    it("should select active connection setup", () => {
      const result = selectActiveConnectionSetup(mockRootState);
      expect(result?.templateId).toBe("slack");
      expect(result?.status).toBe("authenticating");
    });

    it("should select connector suggestions", () => {
      const result = selectConnectorSuggestions(mockRootState);
      expect(result.visible).toBe(true);
      expect(result.query).toBe("create notion page");
    });

    it("should select configured template IDs", () => {
      const result = selectConfiguredTemplateIds(mockRootState);
      expect(result).toEqual(["jira", "linear"]);
    });
  });
});
