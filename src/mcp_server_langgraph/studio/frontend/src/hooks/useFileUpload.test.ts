/**
 * useFileUpload Hook Tests
 *
 * TDD tests for file upload functionality.
 * Features:
 * - File selection (click or drag & drop)
 * - Upload progress tracking
 * - Multiple file support
 * - File type validation
 * - Size limit enforcement
 * - Upload cancellation
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useFileUpload } from "./useFileUpload";

// Mock fetch for upload
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock XMLHttpRequest for progress tracking
// Vitest 4 requires class/function syntax for constructor mocks (arrow functions don't work with `new`)
// Using a class to create fresh mocks for each instance
interface MockXHRInstance {
  open: ReturnType<typeof vi.fn>;
  send: ReturnType<typeof vi.fn>;
  setRequestHeader: ReturnType<typeof vi.fn>;
  upload: { addEventListener: ReturnType<typeof vi.fn> };
  addEventListener: ReturnType<typeof vi.fn>;
  abort: ReturnType<typeof vi.fn>;
  readyState: number;
  status: number;
  response: string;
}

let lastMockXHR: MockXHRInstance | null = null;

class MockXMLHttpRequest {
  open = vi.fn();
  send = vi.fn();
  setRequestHeader = vi.fn();
  upload = { addEventListener: vi.fn() };
  addEventListener = vi.fn();
  abort = vi.fn();
  readyState = 4;
  status = 200;
  response = JSON.stringify({ id: "file-123", url: "/files/file-123" });

  constructor() {
    // eslint-disable-next-line @typescript-eslint/no-this-alias
    lastMockXHR = this;
  }
}

// Getter for accessing the last created instance in tests
const getMockXHR = () => lastMockXHR!;

// Helper to create mock File
function createMockFile(name: string, type: string, size: number): File {
  const content = new Array(size).fill("a").join("");
  return new File([content], name, { type });
}

describe("useFileUpload", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    lastMockXHR = null;
    // Use vi.stubGlobal to properly mock XMLHttpRequest in jsdom environment
    // This ensures our mock takes precedence over jsdom's XMLHttpRequest
    vi.stubGlobal("XMLHttpRequest", MockXMLHttpRequest);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  describe("Initial State", () => {
    it("should start with empty files array", () => {
      const { result } = renderHook(() => useFileUpload());
      expect(result.current.files).toEqual([]);
    });

    it("should start with isUploading false", () => {
      const { result } = renderHook(() => useFileUpload());
      expect(result.current.isUploading).toBe(false);
    });

    it("should start with progress 0", () => {
      const { result } = renderHook(() => useFileUpload());
      expect(result.current.progress).toBe(0);
    });

    it("should start with no error", () => {
      const { result } = renderHook(() => useFileUpload());
      expect(result.current.error).toBeNull();
    });
  });

  describe("File Selection", () => {
    it("should add files when selectFiles is called", () => {
      const { result } = renderHook(() => useFileUpload());

      const file = createMockFile("test.txt", "text/plain", 100);

      act(() => {
        result.current.selectFiles([file]);
      });

      expect(result.current.files).toHaveLength(1);
      expect(result.current.files[0].file.name).toBe("test.txt");
    });

    it("should support multiple file selection", () => {
      const { result } = renderHook(() => useFileUpload());

      const files = [
        createMockFile("test1.txt", "text/plain", 100),
        createMockFile("test2.pdf", "application/pdf", 200),
      ];

      act(() => {
        result.current.selectFiles(files);
      });

      expect(result.current.files).toHaveLength(2);
    });

    it("should generate unique id for each file", () => {
      const { result } = renderHook(() => useFileUpload());

      const files = [
        createMockFile("test1.txt", "text/plain", 100),
        createMockFile("test2.txt", "text/plain", 100),
      ];

      act(() => {
        result.current.selectFiles(files);
      });

      expect(result.current.files[0].id).not.toBe(result.current.files[1].id);
    });

    it("should set initial status to pending", () => {
      const { result } = renderHook(() => useFileUpload());

      const file = createMockFile("test.txt", "text/plain", 100);

      act(() => {
        result.current.selectFiles([file]);
      });

      expect(result.current.files[0].status).toBe("pending");
    });
  });

  describe("File Validation", () => {
    it("should reject files exceeding max size", () => {
      const { result } = renderHook(() => useFileUpload({ maxSizeMB: 1 }));

      // 2MB file (exceeds 1MB limit)
      const file = createMockFile("large.txt", "text/plain", 2 * 1024 * 1024);

      act(() => {
        result.current.selectFiles([file]);
      });

      expect(result.current.files).toHaveLength(1);
      expect(result.current.files[0].status).toBe("error");
      expect(result.current.files[0].error).toContain("size");
    });

    it("should reject files with invalid types", () => {
      const { result } = renderHook(() =>
        useFileUpload({ acceptedTypes: ["image/png", "image/jpeg"] }),
      );

      const file = createMockFile("doc.pdf", "application/pdf", 100);

      act(() => {
        result.current.selectFiles([file]);
      });

      expect(result.current.files).toHaveLength(1);
      expect(result.current.files[0].status).toBe("error");
      expect(result.current.files[0].error).toContain("type");
    });

    it("should accept files within size limit", () => {
      const { result } = renderHook(() => useFileUpload({ maxSizeMB: 5 }));

      // 1MB file (within 5MB limit)
      const file = createMockFile("ok.txt", "text/plain", 1 * 1024 * 1024);

      act(() => {
        result.current.selectFiles([file]);
      });

      expect(result.current.files[0].status).toBe("pending");
    });

    it("should accept files with valid types", () => {
      const { result } = renderHook(() =>
        useFileUpload({ acceptedTypes: ["image/png", "image/jpeg"] }),
      );

      const file = createMockFile("image.png", "image/png", 100);

      act(() => {
        result.current.selectFiles([file]);
      });

      expect(result.current.files[0].status).toBe("pending");
    });
  });

  describe("File Removal", () => {
    it("should remove file by id", () => {
      const { result } = renderHook(() => useFileUpload());

      const files = [
        createMockFile("test1.txt", "text/plain", 100),
        createMockFile("test2.txt", "text/plain", 100),
      ];

      act(() => {
        result.current.selectFiles(files);
      });

      const fileIdToRemove = result.current.files[0].id;

      act(() => {
        result.current.removeFile(fileIdToRemove);
      });

      expect(result.current.files).toHaveLength(1);
      expect(result.current.files[0].file.name).toBe("test2.txt");
    });

    it("should clear all files", () => {
      const { result } = renderHook(() => useFileUpload());

      const files = [
        createMockFile("test1.txt", "text/plain", 100),
        createMockFile("test2.txt", "text/plain", 100),
      ];

      act(() => {
        result.current.selectFiles(files);
      });

      act(() => {
        result.current.clearFiles();
      });

      expect(result.current.files).toHaveLength(0);
    });
  });

  describe("Upload", () => {
    it("should set isUploading to true during upload", async () => {
      const { result } = renderHook(() =>
        useFileUpload({ uploadUrl: "/api/upload" }),
      );

      const file = createMockFile("test.txt", "text/plain", 100);

      act(() => {
        result.current.selectFiles([file]);
      });

      // Start upload
      act(() => {
        result.current.uploadFiles();
      });

      expect(result.current.isUploading).toBe(true);
    });

    it("should register XHR event handlers when uploading", async () => {
      const { result } = renderHook(() =>
        useFileUpload({
          uploadUrl: "/api/upload",
        }),
      );

      const file = createMockFile("test.txt", "text/plain", 100);

      act(() => {
        result.current.selectFiles([file]);
      });

      await act(async () => {
        result.current.uploadFiles();
      });

      // XHR should have registered load and error handlers
      expect(getMockXHR().addEventListener).toHaveBeenCalled();
      const loadCall = getMockXHR().addEventListener.mock.calls.find(
        (call) => call[0] === "load",
      );
      expect(loadCall).toBeDefined();
    });

    it("should send FormData when uploading", async () => {
      const { result } = renderHook(() =>
        useFileUpload({
          uploadUrl: "/api/upload",
        }),
      );

      const file = createMockFile("test.txt", "text/plain", 100);

      act(() => {
        result.current.selectFiles([file]);
      });

      // Verify files were added
      expect(result.current.files.length).toBe(1);
      expect(result.current.files[0].status).toBe("pending");

      // Use synchronous act since XHR calls are synchronous
      act(() => {
        result.current.uploadFiles();
      });

      // Wait for XHR to be created
      await vi.waitFor(() => {
        expect(getMockXHR()).not.toBeNull();
      });

      // XHR.send should have been called with FormData
      const xhr = getMockXHR();
      expect(xhr).not.toBeNull();
      expect(xhr.open).toHaveBeenCalled();
      expect(xhr.send).toHaveBeenCalled();
      const sendCall = xhr.send.mock.calls[0];
      expect(sendCall[0]).toBeInstanceOf(FormData);
    });
  });

  describe("Upload Cancellation", () => {
    it("should cancel upload when cancelUpload is called", () => {
      const { result } = renderHook(() =>
        useFileUpload({ uploadUrl: "/api/upload" }),
      );

      const file = createMockFile("test.txt", "text/plain", 100);

      act(() => {
        result.current.selectFiles([file]);
      });

      act(() => {
        result.current.uploadFiles();
      });

      act(() => {
        result.current.cancelUpload();
      });

      expect(getMockXHR().abort).toHaveBeenCalled();
      expect(result.current.isUploading).toBe(false);
    });
  });

  describe("Drag and Drop", () => {
    it("should provide drag handlers", () => {
      const { result } = renderHook(() => useFileUpload());

      expect(result.current.dragHandlers).toBeDefined();
      expect(result.current.dragHandlers.onDragEnter).toBeDefined();
      expect(result.current.dragHandlers.onDragLeave).toBeDefined();
      expect(result.current.dragHandlers.onDragOver).toBeDefined();
      expect(result.current.dragHandlers.onDrop).toBeDefined();
    });

    it("should set isDragging when drag enters", () => {
      const { result } = renderHook(() => useFileUpload());

      const event = {
        preventDefault: vi.fn(),
        stopPropagation: vi.fn(),
      } as unknown as React.DragEvent;

      act(() => {
        result.current.dragHandlers.onDragEnter(event);
      });

      expect(result.current.isDragging).toBe(true);
    });

    it("should unset isDragging when drag leaves", () => {
      const { result } = renderHook(() => useFileUpload());

      const event = {
        preventDefault: vi.fn(),
        stopPropagation: vi.fn(),
      } as unknown as React.DragEvent;

      act(() => {
        result.current.dragHandlers.onDragEnter(event);
      });

      act(() => {
        result.current.dragHandlers.onDragLeave(event);
      });

      expect(result.current.isDragging).toBe(false);
    });
  });

  describe("Options", () => {
    it("should respect maxFiles limit", () => {
      const { result } = renderHook(() => useFileUpload({ maxFiles: 2 }));

      const files = [
        createMockFile("test1.txt", "text/plain", 100),
        createMockFile("test2.txt", "text/plain", 100),
        createMockFile("test3.txt", "text/plain", 100),
      ];

      act(() => {
        result.current.selectFiles(files);
      });

      expect(result.current.files).toHaveLength(2);
    });

    it("should use custom upload URL", () => {
      const { result } = renderHook(() =>
        useFileUpload({ uploadUrl: "/custom/upload" }),
      );

      const file = createMockFile("test.txt", "text/plain", 100);

      act(() => {
        result.current.selectFiles([file]);
      });

      act(() => {
        result.current.uploadFiles();
      });

      expect(getMockXHR().open).toHaveBeenCalledWith(
        "POST",
        "/custom/upload",
        true,
      );
    });
  });
});
