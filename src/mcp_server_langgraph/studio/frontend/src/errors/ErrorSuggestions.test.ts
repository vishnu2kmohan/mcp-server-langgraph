/**
 * ErrorSuggestions Tests
 *
 * TDD - RED Phase: Tests written first to define expected behavior
 *
 * Tests the error suggestion system that provides contextual recovery
 * suggestions based on error classification.
 */

import { describe, it, expect } from "vitest";
import {
  getSuggestions,
  getUserMessage,
  getRecoveryActions,
  SuggestionContext,
} from "./ErrorSuggestions";
import { createClassifiedError } from "./ErrorTypes";

describe("ErrorSuggestions", () => {
  describe("getSuggestions", () => {
    describe("for network errors", () => {
      it("returns network-specific suggestions", () => {
        const error = createClassifiedError(new Error("offline"), "network");
        const suggestions = getSuggestions(error);

        expect(suggestions).toContain("Check your internet connection");
        expect(suggestions).toContain("Try again in a few moments");
        expect(suggestions.length).toBeGreaterThanOrEqual(2);
      });

      it("includes VPN suggestion for corporate networks", () => {
        const error = createClassifiedError(new Error("CORS blocked"), "network");
        const suggestions = getSuggestions(error, { isCorporateNetwork: true });

        expect(suggestions.some((s) => s.toLowerCase().includes("vpn"))).toBe(true);
      });
    });

    describe("for authentication errors", () => {
      it("returns auth-specific suggestions", () => {
        const error = createClassifiedError(new Error("expired"), "authentication");
        const suggestions = getSuggestions(error);

        expect(suggestions).toContain("Log in again");
        expect(suggestions.some((s) => s.toLowerCase().includes("session"))).toBe(
          true
        );
      });

      it("includes SSO suggestion when applicable", () => {
        const error = createClassifiedError(new Error("sso failed"), "authentication");
        const suggestions = getSuggestions(error, { hasSSOEnabled: true });

        expect(suggestions.some((s) => s.toLowerCase().includes("sso"))).toBe(true);
      });
    });

    describe("for authorization errors", () => {
      it("returns permission-related suggestions", () => {
        const error = createClassifiedError(new Error("forbidden"), "authorization");
        const suggestions = getSuggestions(error);

        expect(
          suggestions.some((s) => s.toLowerCase().includes("permission"))
        ).toBe(true);
        expect(
          suggestions.some((s) => s.toLowerCase().includes("administrator"))
        ).toBe(true);
      });
    });

    describe("for validation errors", () => {
      it("returns input-related suggestions", () => {
        const error = createClassifiedError(new Error("invalid"), "validation");
        const suggestions = getSuggestions(error);

        expect(suggestions.some((s) => s.toLowerCase().includes("input"))).toBe(
          true
        );
      });

      it("includes specific field guidance when available", () => {
        const error = createClassifiedError(new Error("invalid email"), "validation", {
          context: { field: "email", constraint: "must be valid email" },
        });
        const suggestions = getSuggestions(error);

        expect(suggestions.some((s) => s.toLowerCase().includes("email"))).toBe(
          true
        );
      });
    });

    describe("for server errors", () => {
      it("returns retry suggestions", () => {
        const error = createClassifiedError(new Error("500"), "server");
        const suggestions = getSuggestions(error);

        expect(suggestions.some((s) => s.toLowerCase().includes("try again"))).toBe(
          true
        );
        expect(
          suggestions.some((s) => s.toLowerCase().includes("few minutes"))
        ).toBe(true);
      });

      it("includes status page suggestion", () => {
        const error = createClassifiedError(new Error("503"), "server");
        const suggestions = getSuggestions(error, { hasStatusPage: true });

        expect(suggestions.some((s) => s.toLowerCase().includes("status"))).toBe(
          true
        );
      });
    });

    describe("for timeout errors", () => {
      it("returns timeout-specific suggestions", () => {
        const error = createClassifiedError(new Error("timeout"), "timeout");
        const suggestions = getSuggestions(error);

        expect(suggestions.some((s) => s.toLowerCase().includes("retry"))).toBe(
          true
        );
      });

      it("suggests simplifying request for large operations", () => {
        const error = createClassifiedError(new Error("timeout"), "timeout", {
          context: { operation: "batch_export" },
        });
        const suggestions = getSuggestions(error);

        expect(suggestions.some((s) => s.toLowerCase().includes("smaller"))).toBe(
          true
        );
      });
    });

    describe("for quota/rate limit errors", () => {
      it("returns rate limit suggestions", () => {
        const error = createClassifiedError(new Error("rate limited"), "quota");
        const suggestions = getSuggestions(error);

        expect(suggestions.some((s) => s.toLowerCase().includes("wait"))).toBe(
          true
        );
      });

      it("includes specific wait time when retryAfter is provided", () => {
        const error = createClassifiedError(new Error("rate limited"), "quota", {
          retryAfter: 60000,
        });
        const suggestions = getSuggestions(error);

        expect(suggestions.some((s) => s.includes("60 seconds"))).toBe(true);
      });

      it("suggests upgrade for frequent rate limiting", () => {
        const error = createClassifiedError(new Error("limited"), "quota");
        const suggestions = getSuggestions(error, { frequentRateLimits: true });

        expect(suggestions.some((s) => s.toLowerCase().includes("upgrading"))).toBe(
          true
        );
      });
    });

    describe("for unknown errors", () => {
      it("returns generic suggestions", () => {
        const error = createClassifiedError(new Error("unknown"), "unknown");
        const suggestions = getSuggestions(error);

        expect(suggestions).toContain("Try refreshing the page");
        expect(
          suggestions.some((s) => s.toLowerCase().includes("support"))
        ).toBe(true);
      });
    });
  });

  describe("getUserMessage", () => {
    it("returns user-friendly message for network errors", () => {
      const error = createClassifiedError(new Error("net::ERR"), "network");
      const message = getUserMessage(error);

      expect(message).not.toContain("ERR");
      expect(message.toLowerCase()).toContain("connection");
    });

    it("returns user-friendly message for authentication errors", () => {
      const error = createClassifiedError(new Error("401"), "authentication");
      const message = getUserMessage(error);

      expect(message.toLowerCase()).toContain("session");
    });

    it("returns user-friendly message for authorization errors", () => {
      const error = createClassifiedError(new Error("403"), "authorization");
      const message = getUserMessage(error);

      expect(message.toLowerCase()).toContain("permission");
    });

    it("returns user-friendly message for server errors", () => {
      const error = createClassifiedError(new Error("500"), "server");
      const message = getUserMessage(error);

      expect(message.toLowerCase()).toContain("problem");
      expect(message).not.toContain("500");
    });

    it("uses userMessage if provided", () => {
      const error = createClassifiedError(new Error("test"), "server", {
        userMessage: "The workflow could not be saved. Please try again.",
      });
      const message = getUserMessage(error);

      expect(message).toBe("The workflow could not be saved. Please try again.");
    });

    it("never exposes technical details to users", () => {
      const error = createClassifiedError(
        new Error("SQL syntax error near 'SELECT'"),
        "server"
      );
      const message = getUserMessage(error);

      expect(message.toLowerCase()).not.toContain("sql");
      expect(message.toLowerCase()).not.toContain("syntax");
    });
  });

  describe("getRecoveryActions", () => {
    it("returns retry action for recoverable errors", () => {
      const error = createClassifiedError(new Error("timeout"), "timeout");
      const actions = getRecoveryActions(error);

      const retryAction = actions.find((a) => a.type === "retry");
      expect(retryAction).toBeDefined();
      expect(retryAction?.label).toBe("Try Again");
    });

    it("returns login action for authentication errors", () => {
      const error = createClassifiedError(new Error("expired"), "authentication");
      const actions = getRecoveryActions(error);

      const loginAction = actions.find((a) => a.type === "login");
      expect(loginAction).toBeDefined();
      expect(loginAction?.label).toBe("Log In");
    });

    it("returns dismiss action for all errors", () => {
      const error = createClassifiedError(new Error("any"), "unknown");
      const actions = getRecoveryActions(error);

      const dismissAction = actions.find((a) => a.type === "dismiss");
      expect(dismissAction).toBeDefined();
    });

    it("returns report action for server errors", () => {
      const error = createClassifiedError(new Error("crash"), "server");
      const actions = getRecoveryActions(error);

      const reportAction = actions.find((a) => a.type === "report");
      expect(reportAction).toBeDefined();
    });

    it("returns wait action for rate limit errors with retryAfter", () => {
      const error = createClassifiedError(new Error("rate limited"), "quota", {
        retryAfter: 30000,
      });
      const actions = getRecoveryActions(error);

      const waitAction = actions.find((a) => a.type === "wait");
      expect(waitAction).toBeDefined();
      expect(waitAction?.metadata?.waitTime).toBe(30000);
    });

    it("does not return retry action for non-recoverable errors", () => {
      const error = createClassifiedError(new Error("denied"), "authorization");
      const actions = getRecoveryActions(error);

      const retryAction = actions.find((a) => a.type === "retry");
      expect(retryAction).toBeUndefined();
    });

    it("orders actions by priority", () => {
      const error = createClassifiedError(new Error("timeout"), "timeout");
      const actions = getRecoveryActions(error);

      // Primary action (retry) should be first
      expect(actions[0].type).toBe("retry");
      // Dismiss should be last
      expect(actions[actions.length - 1].type).toBe("dismiss");
    });

    describe("RecoveryAction interface", () => {
      it("includes all required fields", () => {
        const error = createClassifiedError(new Error("test"), "network");
        const actions = getRecoveryActions(error);

        actions.forEach((action) => {
          expect(action.type).toBeDefined();
          expect(action.label).toBeDefined();
          expect(typeof action.label).toBe("string");
        });
      });

      it("includes optional handler and metadata", () => {
        const error = createClassifiedError(new Error("test"), "quota", {
          retryAfter: 5000,
        });
        const actions = getRecoveryActions(error);

        const waitAction = actions.find((a) => a.type === "wait");
        expect(waitAction?.metadata).toBeDefined();
      });
    });
  });

  describe("context-aware suggestions", () => {
    it("provides page-specific suggestions", () => {
      const error = createClassifiedError(new Error("fail"), "server");
      const context: SuggestionContext = {
        currentPage: "/studio/workflows",
        lastAction: "save_workflow",
      };
      const suggestions = getSuggestions(error, context);

      expect(suggestions.some((s) => s.toLowerCase().includes("workflow"))).toBe(
        true
      );
    });

    it("provides persona-specific language for admin", () => {
      const error = createClassifiedError(new Error("fail"), "server");
      const context: SuggestionContext = { persona: "admin" };
      const suggestions = getSuggestions(error, context);

      // Admin should get more technical suggestions
      expect(
        suggestions.some((s) => s.toLowerCase().includes("logs") || s.toLowerCase().includes("trace"))
      ).toBe(true);
    });

    it("provides simpler language for bob persona", () => {
      const error = createClassifiedError(new Error("fail"), "server");
      const context: SuggestionContext = { persona: "bob" };
      const suggestions = getSuggestions(error, context);

      // Bob should get simpler suggestions without technical jargon
      suggestions.forEach((suggestion) => {
        expect(suggestion.toLowerCase()).not.toContain("trace");
        expect(suggestion.toLowerCase()).not.toContain("debug");
      });
    });
  });
});
