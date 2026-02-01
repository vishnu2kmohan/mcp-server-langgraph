/**
 * SmartValue Component Tests
 *
 * TDD: Tests written FIRST, then implementation.
 * Tests human-friendly data formatting for various value types.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { SmartValue } from "./SmartValue";

// =============================================================================
// Mock Date for consistent timestamp testing
// =============================================================================

const MOCK_NOW = new Date("2026-01-15T14:30:00Z").getTime();

describe("SmartValue", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(MOCK_NOW);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  // ===========================================================================
  // Timestamp Formatting Tests
  // ===========================================================================

  describe("timestamp formatting", () => {
    it("should format ISO timestamp as relative time", () => {
      render(<SmartValue value="2026-01-15T14:25:00Z" type="timestamp" />);
      expect(screen.getByText("5m ago")).toBeInTheDocument();
    });

    it("should format timestamp from 1 hour ago", () => {
      render(<SmartValue value="2026-01-15T13:30:00Z" type="timestamp" />);
      expect(screen.getByText("1h ago")).toBeInTheDocument();
    });

    it("should format timestamp from 2 days ago", () => {
      render(<SmartValue value="2026-01-13T14:30:00Z" type="timestamp" />);
      expect(screen.getByText("2d ago")).toBeInTheDocument();
    });

    it("should show absolute timestamp in tooltip", () => {
      render(<SmartValue value="2026-01-15T14:25:00Z" type="timestamp" />);
      const element = screen.getByText("5m ago");
      expect(element).toHaveAttribute("title");
      expect(element.getAttribute("title")).toContain("2026");
    });

    it("should handle epoch milliseconds", () => {
      const fiveMinutesAgo = MOCK_NOW - 5 * 60 * 1000;
      render(<SmartValue value={fiveMinutesAgo} type="timestamp" />);
      expect(screen.getByText("5m ago")).toBeInTheDocument();
    });

    it("should auto-detect ISO string as timestamp", () => {
      render(<SmartValue value="2026-01-15T14:25:00Z" />);
      expect(screen.getByText("5m ago")).toBeInTheDocument();
    });

    it("should show 'just now' for very recent timestamps", () => {
      render(<SmartValue value="2026-01-15T14:29:50Z" type="timestamp" />);
      expect(screen.getByText("just now")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Duration Formatting Tests
  // ===========================================================================

  describe("duration formatting", () => {
    it("should format milliseconds under 1 second", () => {
      render(<SmartValue value={234} type="duration" />);
      expect(screen.getByText("234ms")).toBeInTheDocument();
    });

    it("should format milliseconds as seconds when >= 1000", () => {
      render(<SmartValue value={1234} type="duration" />);
      expect(screen.getByText("1.2s")).toBeInTheDocument();
    });

    it("should format very small durations", () => {
      render(<SmartValue value={0.5} type="duration" />);
      expect(screen.getByText("<1ms")).toBeInTheDocument();
    });

    it("should format minutes for long durations", () => {
      render(<SmartValue value={90000} type="duration" />);
      expect(screen.getByText("1.5m")).toBeInTheDocument();
    });

    it("should show exact milliseconds in tooltip", () => {
      render(<SmartValue value={1234.567} type="duration" />);
      const element = screen.getByText("1.2s");
      expect(element).toHaveAttribute("title");
      expect(element.getAttribute("title")).toContain("1,234.567");
    });
  });

  // ===========================================================================
  // Byte Size Formatting Tests
  // ===========================================================================

  describe("bytes formatting", () => {
    it("should format bytes under 1KB", () => {
      render(<SmartValue value={456} type="bytes" />);
      expect(screen.getByText("456 B")).toBeInTheDocument();
    });

    it("should format kilobytes", () => {
      render(<SmartValue value={1536} type="bytes" />);
      expect(screen.getByText("1.5 KB")).toBeInTheDocument();
    });

    it("should format megabytes", () => {
      render(<SmartValue value={2411724} type="bytes" />);
      expect(screen.getByText("2.3 MB")).toBeInTheDocument();
    });

    it("should format gigabytes", () => {
      render(<SmartValue value={1610612736} type="bytes" />);
      expect(screen.getByText("1.5 GB")).toBeInTheDocument();
    });

    it("should show exact bytes in tooltip", () => {
      render(<SmartValue value={1536} type="bytes" />);
      const element = screen.getByText("1.5 KB");
      expect(element).toHaveAttribute("title");
      expect(element.getAttribute("title")).toContain("1,536 bytes");
    });
  });

  // ===========================================================================
  // Number Formatting Tests
  // ===========================================================================

  describe("number formatting", () => {
    it("should format numbers with locale separators", () => {
      render(<SmartValue value={1234} type="number" />);
      expect(screen.getByText("1,234")).toBeInTheDocument();
    });

    it("should format large numbers with K suffix", () => {
      render(<SmartValue value={5200} type="number" />);
      // Should still show full number by default
      expect(screen.getByText("5,200")).toBeInTheDocument();
    });

    it("should format very large numbers", () => {
      render(<SmartValue value={1234567} type="number" />);
      expect(screen.getByText("1,234,567")).toBeInTheDocument();
    });

    it("should handle decimal numbers", () => {
      render(<SmartValue value={123.456} type="number" />);
      expect(screen.getByText("123.46")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // ID/String Truncation Tests
  // ===========================================================================

  describe("id formatting", () => {
    it("should truncate long IDs with ellipsis", () => {
      const longId = "abc123def456ghi789jkl012mno345";
      render(<SmartValue value={longId} type="id" />);
      // Default truncateAt is 16, so we get 8 start + ... + 8 end
      // longId is 30 chars, first 8 = "abc123de", last 8 = "12mno345"
      expect(screen.getByText(/abc123de\.\.\.12mno345/)).toBeInTheDocument();
    });

    it("should show full ID in tooltip", () => {
      const longId = "abc123def456ghi789jkl012mno345";
      render(<SmartValue value={longId} type="id" />);
      const element = screen.getByText(/abc123de\.\.\.12mno345/);
      expect(element).toHaveAttribute("title", longId);
    });

    it("should respect custom truncateAt", () => {
      const longId = "abc123def456ghi789jkl012mno345";
      render(<SmartValue value={longId} type="id" truncateAt={8} />);
      // truncateAt=8 means 4 start + ... + 4 end
      expect(screen.getByText(/abc1\.\.\.o345/)).toBeInTheDocument();
    });

    it("should not truncate short IDs", () => {
      render(<SmartValue value="abc123" type="id" />);
      expect(screen.getByText("abc123")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // JSON/Object Formatting Tests
  // ===========================================================================

  describe("json formatting", () => {
    it("should show object summary", () => {
      const obj = { name: "test", count: 5 };
      render(<SmartValue value={obj} type="json" />);
      expect(screen.getByText(/{.*}/)).toBeInTheDocument();
    });

    it("should show key count for large objects", () => {
      const obj = { a: 1, b: 2, c: 3, d: 4, e: 5 };
      render(<SmartValue value={obj} type="json" />);
      expect(screen.getByText(/5 keys/)).toBeInTheDocument();
    });

    it("should show array length", () => {
      const arr = [1, 2, 3, 4, 5];
      render(<SmartValue value={arr} type="json" />);
      expect(screen.getByText(/5 items/)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Auto-Detection Tests
  // ===========================================================================

  describe("auto type detection", () => {
    it("should auto-detect ISO timestamp strings", () => {
      render(<SmartValue value="2026-01-15T14:25:00Z" />);
      expect(screen.getByText("5m ago")).toBeInTheDocument();
    });

    it("should auto-detect objects as json", () => {
      render(<SmartValue value={{ key: "value" }} />);
      expect(screen.getByText(/{.*}/)).toBeInTheDocument();
    });

    it("should auto-detect arrays as json", () => {
      render(<SmartValue value={[1, 2, 3]} />);
      expect(screen.getByText(/3 items/)).toBeInTheDocument();
    });

    it("should render plain strings as-is", () => {
      render(<SmartValue value="hello world" />);
      expect(screen.getByText("hello world")).toBeInTheDocument();
    });

    it("should render plain numbers as formatted numbers", () => {
      render(<SmartValue value={1234} />);
      expect(screen.getByText("1,234")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Copyable Tests
  // ===========================================================================

  describe("copyable functionality", () => {
    it("should show copy indicator when copyable", () => {
      render(<SmartValue value="test-value" copyable />);
      const element = screen.getByText("test-value");
      // Should have cursor-pointer for copyable
      expect(element.parentElement).toHaveClass("cursor-pointer");
    });

    it("should copy to clipboard on click when copyable", async () => {
      // Use real timers for async clipboard operations
      vi.useRealTimers();

      const mockWriteText = vi.fn().mockResolvedValue(undefined);

      // Mock the clipboard API
      const originalClipboard = navigator.clipboard;
      Object.defineProperty(navigator, "clipboard", {
        value: { writeText: mockWriteText },
        writable: true,
        configurable: true,
      });

      render(<SmartValue value="copy-me" copyable />);

      // Click the wrapper element which has the onClick handler
      const textElement = screen.getByText("copy-me");
      const wrapper = textElement.parentElement;
      expect(wrapper).not.toBeNull();

      // Use fireEvent for direct event triggering
      fireEvent.click(wrapper!);

      // Wait for the async clipboard operation
      await vi.waitFor(() => {
        expect(mockWriteText).toHaveBeenCalledWith("copy-me");
      });

      // Restore clipboard
      Object.defineProperty(navigator, "clipboard", {
        value: originalClipboard,
        writable: true,
        configurable: true,
      });

      // Restore fake timers for other tests
      vi.useFakeTimers();
      vi.setSystemTime(MOCK_NOW);
    });
  });

  // ===========================================================================
  // Edge Cases
  // ===========================================================================

  describe("edge cases", () => {
    it("should handle null value", () => {
      render(<SmartValue value={null} />);
      expect(screen.getByText("null")).toBeInTheDocument();
    });

    it("should handle undefined value", () => {
      render(<SmartValue value={undefined} />);
      expect(screen.getByText("undefined")).toBeInTheDocument();
    });

    it("should handle boolean true", () => {
      render(<SmartValue value={true} />);
      expect(screen.getByText("true")).toBeInTheDocument();
    });

    it("should handle boolean false", () => {
      render(<SmartValue value={false} />);
      expect(screen.getByText("false")).toBeInTheDocument();
    });

    it("should handle empty string", () => {
      render(<SmartValue value="" />);
      expect(screen.getByText('""')).toBeInTheDocument();
    });

    it("should handle zero", () => {
      render(<SmartValue value={0} />);
      expect(screen.getByText("0")).toBeInTheDocument();
    });

    it("should handle empty object", () => {
      render(<SmartValue value={{}} type="json" />);
      expect(screen.getByText("{}")).toBeInTheDocument();
    });

    it("should handle empty array", () => {
      render(<SmartValue value={[]} type="json" />);
      expect(screen.getByText("[]")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Custom className Tests
  // ===========================================================================

  describe("className prop", () => {
    it("should merge custom className", () => {
      render(<SmartValue value="test" className="custom-class" />);
      const element = screen.getByText("test");
      expect(element.parentElement).toHaveClass("custom-class");
    });
  });
});
