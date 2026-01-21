/**
 * Conversation Module Export Tests
 *
 * Verifies that all expected exports are accessible from the module's index.
 * This ensures module organization and prevents accidental breaking changes.
 */
import { describe, it, expect, afterEach, vi } from "vitest";
import * as conversationModule from "./index";

describe("Conversation Module Exports", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("Components", () => {
    it("should export MessageBubble", () => {
      expect(conversationModule.MessageBubble).toBeDefined();
      // MessageBubble uses React.memo, which returns an object with $$typeof
      expect(
        typeof conversationModule.MessageBubble === "function" ||
          typeof conversationModule.MessageBubble === "object",
      ).toBe(true);
    });

    it("should export MessageList", () => {
      expect(conversationModule.MessageList).toBeDefined();
      expect(typeof conversationModule.MessageList).toBe("function");
    });

    it("should export UnifiedMessageList", () => {
      expect(conversationModule.UnifiedMessageList).toBeDefined();
      // UnifiedMessageList uses React.memo, which returns an object with $$typeof
      expect(
        typeof conversationModule.UnifiedMessageList === "function" ||
          typeof conversationModule.UnifiedMessageList === "object",
      ).toBe(true);
    });

    it("should export ConnectedChatInputForm", () => {
      expect(conversationModule.ConnectedChatInputForm).toBeDefined();
      expect(typeof conversationModule.ConnectedChatInputForm).toBe("function");
    });

    it("should export FollowUpSuggestions", () => {
      expect(conversationModule.FollowUpSuggestions).toBeDefined();
      expect(typeof conversationModule.FollowUpSuggestions).toBe("function");
    });

    it("should export ConversationPanel", () => {
      expect(conversationModule.ConversationPanel).toBeDefined();
      expect(typeof conversationModule.ConversationPanel).toBe("function");
    });

    it("should export ConnectedConversationPanel", () => {
      expect(conversationModule.ConnectedConversationPanel).toBeDefined();
      // ConnectedConversationPanel uses forwardRef, which returns an object with $$typeof
      expect(
        typeof conversationModule.ConnectedConversationPanel === "function" ||
          typeof conversationModule.ConnectedConversationPanel === "object",
      ).toBe(true);
    });
  });

  describe("Module Completeness", () => {
    it("should export exactly 7 components", () => {
      const componentExports = [
        "MessageBubble",
        "MessageList",
        "UnifiedMessageList",
        "ConnectedChatInputForm",
        "FollowUpSuggestions",
        "ConversationPanel",
        "ConnectedConversationPanel",
      ];

      for (const name of componentExports) {
        expect(conversationModule).toHaveProperty(name);
      }
    });

    it("should have stable public API", () => {
      // Snapshot of expected exports - update when intentionally changing API
      // Note: ChatInput and SlashCommandMenu were removed in favor of ConnectedChatInputForm
      // ADR-0104: Added UnifiedMessageList for message rendering consolidation
      const expectedExports = [
        "MessageBubble",
        "MessageList",
        "UnifiedMessageList",
        "ConnectedChatInputForm",
        "FollowUpSuggestions",
        "ConversationPanel",
        "ConnectedConversationPanel",
      ];

      // Filter for functions and objects (forwardRef components are objects)
      const actualExports = Object.keys(conversationModule).filter((key) => {
        const value =
          conversationModule[key as keyof typeof conversationModule];
        const type = typeof value;
        // Include functions and objects (forwardRef returns object)
        // Exclude type exports (undefined at runtime)
        return type === "function" || (type === "object" && value !== null);
      });

      expect(actualExports.sort()).toEqual(expectedExports.sort());
    });
  });
});
