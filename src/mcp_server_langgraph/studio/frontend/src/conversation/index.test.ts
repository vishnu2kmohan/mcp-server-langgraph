/**
 * Conversation Module Export Tests
 *
 * Verifies that all expected exports are accessible from the module's index.
 * This ensures module organization and prevents accidental breaking changes.
 */
import { describe, it, expect } from "vitest";
import * as conversationModule from "./index";

describe("Conversation Module Exports", () => {
  describe("Components", () => {
    it("should export MessageBubble", () => {
      expect(conversationModule.MessageBubble).toBeDefined();
      expect(typeof conversationModule.MessageBubble).toBe("function");
    });

    it("should export MessageList", () => {
      expect(conversationModule.MessageList).toBeDefined();
      expect(typeof conversationModule.MessageList).toBe("function");
    });

    it("should export ChatInput", () => {
      expect(conversationModule.ChatInput).toBeDefined();
      expect(typeof conversationModule.ChatInput).toBe("function");
    });

    it("should export SlashCommandMenu", () => {
      expect(conversationModule.SlashCommandMenu).toBeDefined();
      expect(typeof conversationModule.SlashCommandMenu).toBe("function");
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
      expect(typeof conversationModule.ConnectedConversationPanel).toBe(
        "function",
      );
    });
  });

  describe("Module Completeness", () => {
    it("should export exactly 7 components", () => {
      const componentExports = [
        "MessageBubble",
        "MessageList",
        "ChatInput",
        "SlashCommandMenu",
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
      const expectedExports = [
        "MessageBubble",
        "MessageList",
        "ChatInput",
        "SlashCommandMenu",
        "FollowUpSuggestions",
        "ConversationPanel",
        "ConnectedConversationPanel",
      ];

      const actualExports = Object.keys(conversationModule).filter(
        (key) =>
          typeof conversationModule[key as keyof typeof conversationModule] ===
          "function",
      );

      expect(actualExports.sort()).toEqual(expectedExports.sort());
    });
  });
});
