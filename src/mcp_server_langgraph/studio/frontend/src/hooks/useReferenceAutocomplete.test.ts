/**
 * Tests for useReferenceAutocomplete hook
 *
 * TDD: Tests written first per project guidelines.
 * WCAG 2.2 AA accessibility requirements included.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useReferenceAutocomplete } from "./useReferenceAutocomplete";

// Use vi.spyOn for fetch mocking (recommended per test/setup.ts)
let fetchSpy: ReturnType<typeof vi.spyOn>;

describe("useReferenceAutocomplete", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Create spy for each test
    fetchSpy = vi.spyOn(global, "fetch");
  });

  afterEach(() => {
    // Restore fetch after each test
    fetchSpy.mockRestore();
  });

  describe("trigger detection", () => {
    it("should detect [[ trigger and activate autocomplete", () => {
      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Hello [[",
          cursorPosition: 8,
          enabled: true,
        }),
      );

      expect(result.current.isActive).toBe(true);
      expect(result.current.triggerStart).toBe(6);
    });

    it("should detect [[ with partial type prefix", () => {
      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Hello [[tool",
          cursorPosition: 12,
          enabled: true,
        }),
      );

      expect(result.current.isActive).toBe(true);
      expect(result.current.query).toBe("tool");
    });

    it("should detect [[ with type prefix and colon", () => {
      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Hello [[tool:read",
          cursorPosition: 17,
          enabled: true,
        }),
      );

      expect(result.current.isActive).toBe(true);
      expect(result.current.query).toBe("tool:read");
    });

    it("should not activate without [[ trigger", () => {
      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Hello world",
          cursorPosition: 11,
          enabled: true,
        }),
      );

      expect(result.current.isActive).toBe(false);
    });

    it("should not activate with single [", () => {
      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Hello [world",
          cursorPosition: 12,
          enabled: true,
        }),
      );

      expect(result.current.isActive).toBe(false);
    });

    it("should deactivate on ]] close", () => {
      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Hello [[tool:read]]",
          cursorPosition: 19,
          enabled: true,
        }),
      );

      expect(result.current.isActive).toBe(false);
    });

    it("should deactivate when cursor moves before trigger", () => {
      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Hello [[tool",
          cursorPosition: 3, // cursor before [[
          enabled: true,
        }),
      );

      expect(result.current.isActive).toBe(false);
    });

    it("should respect enabled flag", () => {
      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Hello [[",
          cursorPosition: 8,
          enabled: false,
        }),
      );

      expect(result.current.isActive).toBe(false);
    });
  });

  describe("query parsing", () => {
    it("should parse type-only query", () => {
      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Use [[tool",
          cursorPosition: 10,
          enabled: true,
        }),
      );

      expect(result.current.parsedQuery).toEqual({
        type: "tool",
        qualifier: undefined,
        id: undefined,
      });
    });

    it("should parse type:qualifier query for tools", () => {
      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Use [[tool:filesystem",
          cursorPosition: 21,
          enabled: true,
        }),
      );

      expect(result.current.parsedQuery).toEqual({
        type: "tool",
        qualifier: "filesystem",
        id: undefined,
      });
    });

    it("should parse type:qualifier:id query for tools", () => {
      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Use [[tool:filesystem:read",
          cursorPosition: 26,
          enabled: true,
        }),
      );

      expect(result.current.parsedQuery).toEqual({
        type: "tool",
        qualifier: "filesystem",
        id: "read",
      });
    });

    it("should parse skill:id query", () => {
      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Use [[skill:code-review",
          cursorPosition: 23,
          enabled: true,
        }),
      );

      expect(result.current.parsedQuery).toEqual({
        type: "skill",
        qualifier: "code-review",
        id: "code-review",
      });
    });

    it("should parse artifact:id query", () => {
      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "See [[artifact:chart-123",
          cursorPosition: 24,
          enabled: true,
        }),
      );

      expect(result.current.parsedQuery).toEqual({
        type: "artifact",
        qualifier: "chart-123",
        id: "chart-123",
      });
    });

    it("should handle empty query", () => {
      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Use [[",
          cursorPosition: 6,
          enabled: true,
        }),
      );

      expect(result.current.parsedQuery).toEqual({
        type: undefined,
        qualifier: undefined,
        id: undefined,
      });
    });
  });

  describe("suggestions", () => {
    it("should show type suggestions when no type is entered", () => {
      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Use [[",
          cursorPosition: 6,
          enabled: true,
        }),
      );

      expect(result.current.suggestions).toContainEqual(
        expect.objectContaining({ value: "tool", type: "type" }),
      );
      expect(result.current.suggestions).toContainEqual(
        expect.objectContaining({ value: "skill", type: "type" }),
      );
      expect(result.current.suggestions).toContainEqual(
        expect.objectContaining({ value: "artifact", type: "type" }),
      );
    });

    it("should filter type suggestions based on input", () => {
      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Use [[to",
          cursorPosition: 8,
          enabled: true,
        }),
      );

      expect(result.current.suggestions).toContainEqual(
        expect.objectContaining({ value: "tool", type: "type" }),
      );
      expect(result.current.suggestions).not.toContainEqual(
        expect.objectContaining({ value: "skill", type: "type" }),
      );
    });

    it("should provide available tools when tool type is complete", async () => {
      fetchSpy.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          tools: [
            {
              server: "filesystem",
              name: "read_file",
              description: "Read a file",
            },
            {
              server: "filesystem",
              name: "write_file",
              description: "Write a file",
            },
          ],
        }),
      } as Response);

      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Use [[tool:",
          cursorPosition: 11,
          enabled: true,
          availableTools: [
            {
              server: "filesystem",
              name: "read_file",
              description: "Read a file",
            },
            {
              server: "filesystem",
              name: "write_file",
              description: "Write a file",
            },
          ],
        }),
      );

      await waitFor(() => {
        expect(result.current.suggestions).toContainEqual(
          expect.objectContaining({
            value: "filesystem:read_file",
            label: "read_file",
            description: "Read a file",
            type: "tool",
          }),
        );
      });
    });

    it("should filter tools based on qualifier input", async () => {
      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Use [[tool:file",
          cursorPosition: 15,
          enabled: true,
          availableTools: [
            {
              server: "filesystem",
              name: "read_file",
              description: "Read a file",
            },
            { server: "database", name: "query", description: "Run SQL query" },
          ],
        }),
      );

      await waitFor(() => {
        expect(result.current.suggestions).toContainEqual(
          expect.objectContaining({ value: "filesystem:read_file" }),
        );
        expect(result.current.suggestions).not.toContainEqual(
          expect.objectContaining({ value: "database:query" }),
        );
      });
    });
  });

  describe("selection", () => {
    it("should call onSelect when suggestion is selected", () => {
      const onSelect = vi.fn();

      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Use [[",
          cursorPosition: 6,
          enabled: true,
          onSelect,
        }),
      );

      act(() => {
        result.current.selectSuggestion({
          value: "tool",
          label: "Tool",
          type: "type",
        });
      });

      expect(onSelect).toHaveBeenCalledWith({
        newText: "Use [[tool:",
        newCursorPosition: 11,
        suggestion: expect.objectContaining({ value: "tool" }),
      });
    });

    it("should complete the reference when final suggestion is selected", () => {
      const onSelect = vi.fn();

      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Use [[tool:filesystem:",
          cursorPosition: 22,
          enabled: true,
          onSelect,
        }),
      );

      act(() => {
        result.current.selectSuggestion({
          value: "read_file",
          label: "Read File",
          type: "tool",
          isComplete: true,
        });
      });

      expect(onSelect).toHaveBeenCalledWith({
        newText: "Use [[tool:filesystem:read_file]]",
        newCursorPosition: 33, // "Use [[tool:filesystem:read_file]]".length = 33
        suggestion: expect.objectContaining({ value: "read_file" }),
      });
    });
  });

  describe("keyboard navigation", () => {
    it("should expose selectedIndex state", () => {
      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Use [[",
          cursorPosition: 6,
          enabled: true,
        }),
      );

      expect(result.current.selectedIndex).toBe(0);
    });

    it("should navigate down with setSelectedIndex", () => {
      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Use [[",
          cursorPosition: 6,
          enabled: true,
        }),
      );

      act(() => {
        result.current.setSelectedIndex(1);
      });

      expect(result.current.selectedIndex).toBe(1);
    });

    it("should not exceed suggestions length", () => {
      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Use [[",
          cursorPosition: 6,
          enabled: true,
        }),
      );

      const maxIndex = result.current.suggestions.length - 1;

      act(() => {
        result.current.setSelectedIndex(100);
      });

      expect(result.current.selectedIndex).toBeLessThanOrEqual(maxIndex);
    });

    it("should reset selectedIndex when suggestions change", async () => {
      const { result, rerender } = renderHook(
        (props) => useReferenceAutocomplete(props),
        {
          initialProps: {
            inputValue: "Use [[",
            cursorPosition: 6,
            enabled: true,
          },
        },
      );

      act(() => {
        result.current.setSelectedIndex(2);
      });

      expect(result.current.selectedIndex).toBe(2);

      rerender({
        inputValue: "Use [[to",
        cursorPosition: 8,
        enabled: true,
      });

      expect(result.current.selectedIndex).toBe(0);
    });
  });

  describe("dismiss", () => {
    it("should expose dismiss function", () => {
      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Use [[",
          cursorPosition: 6,
          enabled: true,
        }),
      );

      expect(result.current.isActive).toBe(true);

      act(() => {
        result.current.dismiss();
      });

      expect(result.current.isActive).toBe(false);
    });

    it("should re-activate when trigger is typed again", () => {
      const { result, rerender } = renderHook(
        (props) => useReferenceAutocomplete(props),
        {
          initialProps: {
            inputValue: "Use [[",
            cursorPosition: 6,
            enabled: true,
          },
        },
      );

      act(() => {
        result.current.dismiss();
      });

      expect(result.current.isActive).toBe(false);

      // Type more
      rerender({
        inputValue: "Use [[ and [[",
        cursorPosition: 13,
        enabled: true,
      });

      expect(result.current.isActive).toBe(true);
    });
  });

  describe("accessibility", () => {
    it("should provide aria attributes for autocomplete", () => {
      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Use [[",
          cursorPosition: 6,
          enabled: true,
        }),
      );

      expect(result.current.ariaProps).toEqual({
        role: "combobox",
        "aria-expanded": true,
        "aria-haspopup": "listbox",
        "aria-controls": "reference-autocomplete-listbox",
        "aria-activedescendant": expect.stringMatching(/^ref-suggestion-/),
      });
    });

    it("should provide aria-expanded false when inactive", () => {
      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Hello world",
          cursorPosition: 11,
          enabled: true,
        }),
      );

      expect(result.current.ariaProps["aria-expanded"]).toBe(false);
    });
  });

  describe("semantic search integration", () => {
    it("should use semantic search API when enableSemanticSearch is true", async () => {
      // Mock semantic search API response
      fetchSpy.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            results: [
              {
                tool_id: "tool-1",
                name: "read_file",
                description: "Read file contents",
                score: 0.95,
              },
            ],
            query: "read file",
            total_results: 1,
          }),
      } as Response);

      const { result: _result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Use [[tool:read file",
          cursorPosition: 20,
          enabled: true,
          enableSemanticSearch: true,
        }),
      );

      // Wait for debounced API call
      await waitFor(
        () => {
          expect(fetchSpy).toHaveBeenCalled();
        },
        { timeout: 500 },
      );

      // Verify API was called with semantic search endpoint
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/tools/semantic-search"),
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining("read file"),
        }),
      );
    });

    it("should fallback to substring matching when enableSemanticSearch is false", () => {
      const mockTools = [
        { server: "filesystem", name: "read_file", description: "Read file" },
        { server: "filesystem", name: "write_file", description: "Write file" },
      ];

      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Use [[tool:filesystem:read",
          cursorPosition: 26,
          enabled: true,
          enableSemanticSearch: false,
          availableTools: mockTools,
        }),
      );

      // Should not call API
      expect(fetchSpy).not.toHaveBeenCalled();

      // Should show filtered suggestion based on substring
      expect(result.current.suggestions.length).toBeGreaterThanOrEqual(1);
      expect(
        result.current.suggestions.some((s) => s.value.includes("read_file")),
      ).toBe(true);
    });

    it("should debounce semantic search API calls", async () => {
      fetchSpy.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            results: [],
            query: "",
            total_results: 0,
          }),
      } as Response);

      const { result: _result, rerender } = renderHook(
        ({ inputValue, cursorPosition }) =>
          useReferenceAutocomplete({
            inputValue,
            cursorPosition,
            enabled: true,
            enableSemanticSearch: true,
          }),
        {
          initialProps: {
            inputValue: "Use [[tool:r",
            cursorPosition: 12,
          },
        },
      );

      // Quickly update input multiple times
      rerender({ inputValue: "Use [[tool:re", cursorPosition: 13 });
      rerender({ inputValue: "Use [[tool:rea", cursorPosition: 14 });
      rerender({ inputValue: "Use [[tool:read", cursorPosition: 15 });

      // Wait for debounce to settle
      await waitFor(
        () => {
          expect(fetchSpy).toHaveBeenCalled();
        },
        { timeout: 500 },
      );

      // Should only call API once due to debouncing
      expect(fetchSpy).toHaveBeenCalledTimes(1);
    });

    it("should handle semantic search API errors gracefully", async () => {
      // Mock API error
      fetchSpy.mockRejectedValueOnce(new Error("Network error"));

      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Use [[tool:read",
          cursorPosition: 15,
          enabled: true,
          enableSemanticSearch: true,
        }),
      );

      // Wait for API call to complete
      await waitFor(
        () => {
          expect(fetchSpy).toHaveBeenCalled();
        },
        { timeout: 500 },
      );

      // Should still be active (error doesn't crash the hook)
      expect(result.current.isActive).toBe(true);
      // Should fallback to type suggestions on error
      expect(result.current.suggestions).toBeDefined();
    });

    it("should include score in suggestions from semantic search", async () => {
      fetchSpy.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            results: [
              {
                tool_id: "tool-1",
                name: "calculator",
                description: "Math operations",
                score: 0.92,
              },
              {
                tool_id: "tool-2",
                name: "add",
                description: "Add numbers",
                score: 0.85,
              },
            ],
            query: "math",
            total_results: 2,
          }),
      } as Response);

      const { result } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Use [[tool:math",
          cursorPosition: 15,
          enabled: true,
          enableSemanticSearch: true,
        }),
      );

      await waitFor(
        () => {
          expect(fetchSpy).toHaveBeenCalled();
        },
        { timeout: 500 },
      );

      // Wait for suggestions to be populated
      await waitFor(() => {
        expect(result.current.suggestions.length).toBeGreaterThan(0);
      });

      // Results should be ordered by score (highest first)
      const scores = result.current.suggestions
        .filter((s) => "score" in s)
        .map((s) => (s as { score: number }).score);
      for (let i = 1; i < scores.length; i++) {
        expect(scores[i - 1]).toBeGreaterThanOrEqual(scores[i]);
      }
    });

    it("should use skill semantic search for skill references", async () => {
      fetchSpy.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            results: [
              {
                skill_id: "skill-1",
                name: "code-review",
                description: "Review code quality",
                score: 0.88,
                tags: ["development"],
              },
            ],
            query: "review code",
            total_results: 1,
          }),
      } as Response);

      const { result: _result2 } = renderHook(() =>
        useReferenceAutocomplete({
          inputValue: "Use [[skill:review code",
          cursorPosition: 23,
          enabled: true,
          enableSemanticSearch: true,
        }),
      );

      await waitFor(
        () => {
          expect(fetchSpy).toHaveBeenCalled();
        },
        { timeout: 500 },
      );

      // Verify API was called with skill semantic search endpoint
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/admin/skills/semantic-search"),
        expect.objectContaining({
          method: "POST",
        }),
      );
    });
  });
});
