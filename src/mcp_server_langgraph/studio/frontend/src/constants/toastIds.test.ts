/**
 * Toast ID Constants Tests
 *
 * Verifies toast ID constants and helper functions for deduplication.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import {
  getConnectionToastId,
  getCriticalAlertToastId,
  TOAST_ID_CONNECTION_ERROR,
  TOAST_ID_BUDGET_WARNING,
  TOAST_ID_SESSION_DELETED,
  TOAST_ID_SESSION_CREATED,
  TOAST_ID_SESSION_RENAMED,
  TOAST_ID_MODELS_LOAD_FAILED,
  TOAST_ID_APP_UPDATE_REQUIRED,
  TOAST_ID_CHAT_ERROR,
  TOAST_ID_EXPORT,
  TOAST_ID_VOICE_ERROR,
  TOAST_ID_FILE_ERROR,
  TOAST_ID_URL_FETCH_ERROR,
  TOAST_ID_RATING_ERROR,
  TOAST_ID_FEEDBACK,
  TOAST_ID_SESSION_SUGGEST,
  TOAST_ID_CONVERSATION_CLEAR,
  TOAST_ID_COPY,
  TOAST_ID_SESSION_REFRESH,
  TOAST_ID_HALLUCINATION_REPORT,
  TOAST_ID_GOAL,
} from "./toastIds";

afterEach(() => {
  vi.clearAllMocks();
});

describe("Toast ID Constants", () => {
  describe("Connection Health Toast IDs", () => {
    describe("getConnectionToastId", () => {
      it("should generate unique ID for each connection name", () => {
        const id1 = getConnectionToastId("postgres");
        const id2 = getConnectionToastId("redis");

        expect(id1).toBe("conn-postgres");
        expect(id2).toBe("conn-redis");
        expect(id1).not.toBe(id2);
      });

      it("should handle connection names with special characters", () => {
        const id = getConnectionToastId("my-db-connection");
        expect(id).toBe("conn-my-db-connection");
      });

      it("should handle empty connection name", () => {
        const id = getConnectionToastId("");
        expect(id).toBe("conn-");
      });
    });

    it("should have TOAST_ID_CONNECTION_ERROR constant", () => {
      expect(TOAST_ID_CONNECTION_ERROR).toBe("conn-error");
    });
  });

  describe("Cost Tracking Toast IDs", () => {
    it("should have TOAST_ID_BUDGET_WARNING constant", () => {
      expect(TOAST_ID_BUDGET_WARNING).toBe("budget-warning");
    });
  });

  describe("Session Management Toast IDs", () => {
    it("should have TOAST_ID_SESSION_DELETED constant", () => {
      expect(TOAST_ID_SESSION_DELETED).toBe("session-deleted");
    });

    it("should have TOAST_ID_SESSION_CREATED constant", () => {
      expect(TOAST_ID_SESSION_CREATED).toBe("session-created");
    });

    it("should have TOAST_ID_SESSION_RENAMED constant", () => {
      expect(TOAST_ID_SESSION_RENAMED).toBe("session-renamed");
    });
  });

  describe("Model/Config Toast IDs", () => {
    it("should have TOAST_ID_MODELS_LOAD_FAILED constant", () => {
      expect(TOAST_ID_MODELS_LOAD_FAILED).toBe("models-load-failed");
    });
  });

  describe("Application State Toast IDs", () => {
    it("should have TOAST_ID_APP_UPDATE_REQUIRED constant", () => {
      expect(TOAST_ID_APP_UPDATE_REQUIRED).toBe("app-update-required");
    });

    it("should have TOAST_ID_CHAT_ERROR constant", () => {
      expect(TOAST_ID_CHAT_ERROR).toBe("chat-error");
    });

    it("should have TOAST_ID_EXPORT constant", () => {
      expect(TOAST_ID_EXPORT).toBe("export");
    });

    it("should have TOAST_ID_VOICE_ERROR constant", () => {
      expect(TOAST_ID_VOICE_ERROR).toBe("voice-error");
    });

    it("should have TOAST_ID_FILE_ERROR constant", () => {
      expect(TOAST_ID_FILE_ERROR).toBe("file-error");
    });

    it("should have TOAST_ID_URL_FETCH_ERROR constant", () => {
      expect(TOAST_ID_URL_FETCH_ERROR).toBe("url-fetch-error");
    });

    it("should have TOAST_ID_RATING_ERROR constant", () => {
      expect(TOAST_ID_RATING_ERROR).toBe("rating-error");
    });
  });

  describe("Feedback Toast IDs", () => {
    it("should have TOAST_ID_FEEDBACK constant", () => {
      expect(TOAST_ID_FEEDBACK).toBe("feedback");
    });

    it("should have TOAST_ID_SESSION_SUGGEST constant", () => {
      expect(TOAST_ID_SESSION_SUGGEST).toBe("session-suggest");
    });
  });

  describe("Conversation Action Toast IDs", () => {
    it("should have TOAST_ID_CONVERSATION_CLEAR constant", () => {
      expect(TOAST_ID_CONVERSATION_CLEAR).toBe("conversation-clear");
    });

    it("should have TOAST_ID_COPY constant", () => {
      expect(TOAST_ID_COPY).toBe("copy");
    });

    it("should have TOAST_ID_SESSION_REFRESH constant", () => {
      expect(TOAST_ID_SESSION_REFRESH).toBe("session-refresh");
    });

    it("should have TOAST_ID_HALLUCINATION_REPORT constant", () => {
      expect(TOAST_ID_HALLUCINATION_REPORT).toBe("hallucination-report");
    });

    it("should have TOAST_ID_GOAL constant", () => {
      expect(TOAST_ID_GOAL).toBe("goal");
    });
  });

  describe("Alert Toast IDs", () => {
    describe("getCriticalAlertToastId", () => {
      it("should generate unique ID for each alert", () => {
        const id1 = getCriticalAlertToastId("alert-123");
        const id2 = getCriticalAlertToastId("alert-456");

        expect(id1).toBe("alert-critical-alert-123");
        expect(id2).toBe("alert-critical-alert-456");
        expect(id1).not.toBe(id2);
      });

      it("should handle empty alert ID", () => {
        const id = getCriticalAlertToastId("");
        expect(id).toBe("alert-critical-");
      });
    });
  });

  describe("ID Uniqueness", () => {
    it("all static toast IDs should be unique", () => {
      const ids = [
        TOAST_ID_CONNECTION_ERROR,
        TOAST_ID_BUDGET_WARNING,
        TOAST_ID_SESSION_DELETED,
        TOAST_ID_SESSION_CREATED,
        TOAST_ID_SESSION_RENAMED,
        TOAST_ID_MODELS_LOAD_FAILED,
        TOAST_ID_APP_UPDATE_REQUIRED,
        TOAST_ID_CHAT_ERROR,
        TOAST_ID_EXPORT,
        TOAST_ID_VOICE_ERROR,
        TOAST_ID_FILE_ERROR,
        TOAST_ID_URL_FETCH_ERROR,
        TOAST_ID_RATING_ERROR,
        TOAST_ID_FEEDBACK,
        TOAST_ID_SESSION_SUGGEST,
        TOAST_ID_CONVERSATION_CLEAR,
        TOAST_ID_COPY,
        TOAST_ID_SESSION_REFRESH,
        TOAST_ID_HALLUCINATION_REPORT,
        TOAST_ID_GOAL,
      ];

      const uniqueIds = new Set(ids);
      expect(uniqueIds.size).toBe(ids.length);
    });

    it("generated connection IDs should not conflict with static IDs", () => {
      const staticIds = [
        TOAST_ID_CONNECTION_ERROR,
        TOAST_ID_BUDGET_WARNING,
        TOAST_ID_SESSION_DELETED,
        TOAST_ID_SESSION_CREATED,
        TOAST_ID_SESSION_RENAMED,
        TOAST_ID_MODELS_LOAD_FAILED,
        TOAST_ID_APP_UPDATE_REQUIRED,
        TOAST_ID_CHAT_ERROR,
        TOAST_ID_EXPORT,
        TOAST_ID_VOICE_ERROR,
        TOAST_ID_FILE_ERROR,
        TOAST_ID_URL_FETCH_ERROR,
        TOAST_ID_RATING_ERROR,
        TOAST_ID_FEEDBACK,
        TOAST_ID_SESSION_SUGGEST,
        TOAST_ID_CONVERSATION_CLEAR,
        TOAST_ID_COPY,
        TOAST_ID_SESSION_REFRESH,
        TOAST_ID_HALLUCINATION_REPORT,
        TOAST_ID_GOAL,
      ];

      // Generate some connection IDs
      const generatedIds = [
        getConnectionToastId("postgres"),
        getConnectionToastId("redis"),
        getConnectionToastId("api"),
        getCriticalAlertToastId("alert-1"),
        getCriticalAlertToastId("alert-2"),
      ];

      // Check none of the generated IDs match static IDs
      for (const generatedId of generatedIds) {
        expect(staticIds).not.toContain(generatedId);
      }
    });
  });
});
