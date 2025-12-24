/**
 * Tests for WebSocket helper utilities.
 *
 * @module utils/websocketHelpers.test
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import {
  parseMessageEnvelope,
  isMessageEnvelope,
  extractPayload,
  type MessageEnvelope,
} from "./websocketHelpers";

describe("websocketHelpers", () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });
  describe("parseMessageEnvelope", () => {
    it("should extract payload from valid envelope", () => {
      const envelope: MessageEnvelope<{ message: string }> = {
        type: "notification",
        payload: { message: "Hello" },
        id: "123",
        timestamp: "2025-12-24T00:00:00Z",
      };

      const result = parseMessageEnvelope<{ message: string }>(envelope);
      expect(result).toEqual({ message: "Hello" });
    });

    it("should return null for non-object data", () => {
      expect(parseMessageEnvelope("string")).toBeNull();
      expect(parseMessageEnvelope(123)).toBeNull();
      expect(parseMessageEnvelope(null)).toBeNull();
      expect(parseMessageEnvelope(undefined)).toBeNull();
    });

    it("should return null for object without payload", () => {
      const flatMessage = { type: "notification", message: "Hello" };
      expect(parseMessageEnvelope(flatMessage)).toBeNull();
    });

    it("should return null for empty object", () => {
      expect(parseMessageEnvelope({})).toBeNull();
    });

    it("should handle envelope with null payload", () => {
      const envelope = { type: "notification", payload: null };
      const result = parseMessageEnvelope(envelope);
      expect(result).toBeNull();
    });

    it("should handle envelope with undefined payload", () => {
      const envelope = { type: "notification", payload: undefined };
      const result = parseMessageEnvelope(envelope);
      expect(result).toBeUndefined();
    });

    it("should handle array payloads", () => {
      const envelope = {
        type: "list",
        payload: [1, 2, 3],
      };
      const result = parseMessageEnvelope<number[]>(envelope);
      expect(result).toEqual([1, 2, 3]);
    });

    it("should handle nested payloads", () => {
      interface NestedPayload {
        data: {
          items: string[];
        };
      }
      const envelope = {
        type: "nested",
        payload: {
          data: {
            items: ["a", "b", "c"],
          },
        },
      };
      const result = parseMessageEnvelope<NestedPayload>(envelope);
      expect(result).toEqual({
        data: {
          items: ["a", "b", "c"],
        },
      });
    });
  });

  describe("isMessageEnvelope", () => {
    it("should return true for valid envelope with required fields", () => {
      const envelope = {
        type: "notification",
        payload: { message: "Hello" },
      };
      expect(isMessageEnvelope(envelope)).toBe(true);
    });

    it("should return true for envelope with all optional fields", () => {
      const envelope = {
        type: "notification",
        payload: { message: "Hello" },
        id: "123",
        timestamp: "2025-12-24T00:00:00Z",
      };
      expect(isMessageEnvelope(envelope)).toBe(true);
    });

    it("should return false for null", () => {
      expect(isMessageEnvelope(null)).toBe(false);
    });

    it("should return false for undefined", () => {
      expect(isMessageEnvelope(undefined)).toBe(false);
    });

    it("should return false for string", () => {
      expect(isMessageEnvelope("string")).toBe(false);
    });

    it("should return false for number", () => {
      expect(isMessageEnvelope(123)).toBe(false);
    });

    it("should return false for object without type", () => {
      expect(isMessageEnvelope({ payload: {} })).toBe(false);
    });

    it("should return false for object without payload", () => {
      expect(isMessageEnvelope({ type: "notification" })).toBe(false);
    });

    it("should return false for empty object", () => {
      expect(isMessageEnvelope({})).toBe(false);
    });
  });

  describe("extractPayload", () => {
    it("should extract payload from envelope", () => {
      const envelope = {
        type: "notification",
        payload: { message: "Hello" },
      };
      const result = extractPayload<{ message: string }>(envelope);
      expect(result).toEqual({ message: "Hello" });
    });

    it("should return original data if not an envelope", () => {
      const flatMessage = { message: "Hello" };
      const result = extractPayload<{ message: string }>(flatMessage);
      expect(result).toEqual({ message: "Hello" });
    });

    it("should return null for null input", () => {
      const result = extractPayload(null);
      expect(result).toBeNull();
    });

    it("should return undefined for undefined input", () => {
      const result = extractPayload(undefined);
      expect(result).toBeUndefined();
    });

    it("should handle legacy flat messages during migration", () => {
      // This tests backward compatibility during WebSocket migration
      const legacyMessage = {
        status: "connected",
        connections: [],
        timestamp: "2025-12-24T00:00:00Z",
      };
      const result = extractPayload<typeof legacyMessage>(legacyMessage);
      expect(result).toEqual(legacyMessage);
    });
  });
});
