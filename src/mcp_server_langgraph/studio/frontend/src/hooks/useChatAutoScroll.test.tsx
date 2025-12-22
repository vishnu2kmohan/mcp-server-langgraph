/**
 * useChatAutoScroll Hook Test Suite
 *
 * TDD tests for auto-scroll functionality in chat interfaces.
 * Extracted from ChatMessages.tsx for reusability.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useChatAutoScroll } from "./useChatAutoScroll";

describe("useChatAutoScroll", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("ref creation", () => {
    it("should return a ref object", () => {
      const { result } = renderHook(() => useChatAutoScroll([]));
      expect(result.current.messagesEndRef).toBeDefined();
      expect(result.current.messagesEndRef.current).toBeNull();
    });
  });

  describe("scroll behavior", () => {
    it("should call scrollIntoView when messages change", () => {
      const mockScrollIntoView = vi.fn();
      const mockElement = {
        scrollIntoView: mockScrollIntoView,
      } as unknown as HTMLDivElement;

      const { result, rerender } = renderHook(
        ({ messages }) => useChatAutoScroll(messages),
        { initialProps: { messages: [] } }
      );

      // Simulate ref being attached
      Object.defineProperty(result.current.messagesEndRef, "current", {
        value: mockElement,
        writable: true,
      });

      // Trigger re-render with new messages
      rerender({ messages: [{ id: "1", content: "Hello" }] });

      expect(mockScrollIntoView).toHaveBeenCalledWith({ behavior: "smooth" });
    });

    it("should call scrollIntoView when streaming content changes", () => {
      const mockScrollIntoView = vi.fn();
      const mockElement = {
        scrollIntoView: mockScrollIntoView,
      } as unknown as HTMLDivElement;

      const { result, rerender } = renderHook(
        ({ messages, streamingContent }) =>
          useChatAutoScroll(messages, streamingContent),
        { initialProps: { messages: [], streamingContent: "" } }
      );

      // Simulate ref being attached
      Object.defineProperty(result.current.messagesEndRef, "current", {
        value: mockElement,
        writable: true,
      });

      // Trigger re-render with streaming content
      rerender({ messages: [], streamingContent: "Hello world" });

      expect(mockScrollIntoView).toHaveBeenCalledWith({ behavior: "smooth" });
    });

    it("should not throw if scrollIntoView is unavailable (jsdom)", () => {
      const mockElement = {} as HTMLDivElement; // No scrollIntoView

      const { result, rerender } = renderHook(
        ({ messages }) => useChatAutoScroll(messages),
        { initialProps: { messages: [] } }
      );

      // Simulate ref being attached without scrollIntoView
      Object.defineProperty(result.current.messagesEndRef, "current", {
        value: mockElement,
        writable: true,
      });

      // Should not throw
      expect(() => {
        rerender({ messages: [{ id: "1", content: "Hello" }] });
      }).not.toThrow();
    });

    it("should not throw if ref is null", () => {
      const { rerender } = renderHook(
        ({ messages }) => useChatAutoScroll(messages),
        { initialProps: { messages: [] } }
      );

      // Ref is null by default, should not throw
      expect(() => {
        rerender({ messages: [{ id: "1", content: "Hello" }] });
      }).not.toThrow();
    });
  });

  describe("dependency tracking", () => {
    it("should scroll when ref is attached and effect runs", () => {
      // This test verifies that the hook correctly handles
      // the case where the ref gets attached after the effect runs
      const { result, rerender } = renderHook(
        ({ messages }) => useChatAutoScroll(messages),
        { initialProps: { messages: [] } }
      );

      // Ref is null initially
      expect(result.current.messagesEndRef.current).toBeNull();

      // Create mock element with scrollIntoView
      const mockScrollIntoView = vi.fn();
      const mockElement = {
        scrollIntoView: mockScrollIntoView,
      } as unknown as HTMLDivElement;

      // Simulate ref being attached
      Object.defineProperty(result.current.messagesEndRef, "current", {
        value: mockElement,
        writable: true,
      });

      // Trigger effect by changing messages
      rerender({ messages: [{ id: "1" }] });

      // Now scrollIntoView should have been called
      expect(mockScrollIntoView).toHaveBeenCalledWith({ behavior: "smooth" });
    });
  });
});
