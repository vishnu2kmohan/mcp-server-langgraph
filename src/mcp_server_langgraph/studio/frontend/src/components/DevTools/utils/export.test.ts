/**
 * Export Utilities Tests
 *
 * TDD tests for exporting console/network logs to JSON/CSV.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import {
  exportToJSON,
  exportToCSV,
  downloadFile,
  formatConsoleEntriesForExport,
  formatNetworkEntriesForExport,
} from "./export";
import type { ConsoleEntry, NetworkEntry } from "../types";

// =============================================================================
// Test Data
// =============================================================================

const mockConsoleEntries: ConsoleEntry[] = [
  {
    id: "console-1",
    level: "info",
    source: "system",
    message: "Application started",
    timestamp: 1703275200000,
  },
  {
    id: "console-2",
    level: "error",
    source: "api",
    message: "Request failed",
    timestamp: 1703275260000,
    data: { code: 500, url: "/api/test" },
    stackTrace: "Error: Request failed\n  at fetch (/src/api.ts:42)",
  },
];

const mockNetworkEntries: NetworkEntry[] = [
  {
    id: "net-1",
    method: "GET",
    url: "/api/v1/sessions",
    status: "completed",
    statusCode: 200,
    statusText: "OK",
    startTime: 1703275200000,
    endTime: 1703275200150,
    duration: 150,
    requestSize: 0,
    responseSize: 1024,
  },
  {
    id: "net-2",
    method: "POST",
    url: "/api/v1/messages",
    status: "completed",
    statusCode: 201,
    statusText: "Created",
    startTime: 1703275260000,
    endTime: 1703275260300,
    duration: 300,
    requestSize: 512,
    responseSize: 256,
    requestBody: { text: "Hello" },
    responseBody: { id: "msg-1", text: "Hello" },
  },
];

// =============================================================================
// Tests
// =============================================================================

describe("Export Utilities", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("exportToJSON", () => {
    it("should export data to JSON string", () => {
      const data = { key: "value" };
      const result = exportToJSON(data);
      expect(result).toBe(JSON.stringify(data, null, 2));
    });

    it("should handle empty arrays", () => {
      const result = exportToJSON([]);
      expect(result).toBe("[]");
    });
  });

  describe("exportToCSV", () => {
    it("should export array of objects to CSV", () => {
      const data = [
        { name: "Alice", age: 30 },
        { name: "Bob", age: 25 },
      ];
      const result = exportToCSV(data);
      expect(result).toContain("name,age");
      expect(result).toContain("Alice,30");
    });

    it("should escape values with commas", () => {
      const data = [{ message: "Hello, world" }];
      const result = exportToCSV(data);
      expect(result).toContain('"Hello, world"');
    });
  });

  describe("formatConsoleEntriesForExport", () => {
    it("should format console entries for export", () => {
      const result = formatConsoleEntriesForExport(mockConsoleEntries);
      expect(result).toHaveLength(2);
      expect(result[0]).toHaveProperty("timestamp");
      expect(result[0]).toHaveProperty("level");
    });

    it("should include data when present", () => {
      const result = formatConsoleEntriesForExport(mockConsoleEntries);
      expect(result[1].data).toBeDefined();
    });
  });

  describe("formatNetworkEntriesForExport", () => {
    it("should format network entries for export", () => {
      const result = formatNetworkEntriesForExport(mockNetworkEntries);
      expect(result).toHaveLength(2);
      expect(result[0]).toHaveProperty("method");
      expect(result[0]).toHaveProperty("url");
    });

    it("should format request/response body as JSON strings", () => {
      const result = formatNetworkEntriesForExport(mockNetworkEntries);
      expect(result[1].requestBody).toContain("Hello");
    });
  });

  describe("downloadFile", () => {
    it("should create and trigger download link", () => {
      const createElementSpy = vi.spyOn(document, "createElement");
      const mockLink = {
        href: "",
        download: "",
        click: vi.fn(),
        style: {},
      };
      createElementSpy.mockReturnValue(mockLink as unknown as HTMLElement);
      vi.spyOn(document.body, "appendChild").mockImplementation(
        () => mockLink as unknown as Node,
      );
      vi.spyOn(document.body, "removeChild").mockImplementation(
        () => mockLink as unknown as Node,
      );
      vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:test");
      vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});

      downloadFile("test", "test.json", "application/json");

      expect(mockLink.download).toBe("test.json");
      expect(mockLink.click).toHaveBeenCalled();
    });
  });
});
