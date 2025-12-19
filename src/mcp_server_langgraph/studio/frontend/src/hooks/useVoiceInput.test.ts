/**
 * useVoiceInput Hook Tests
 *
 * TDD tests for voice input functionality using Web Speech API.
 * Features:
 * - Start/stop recording
 * - Transcription results
 * - Error handling
 * - Browser support detection
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useVoiceInput } from "./useVoiceInput";

// Mock SpeechRecognition
// Vitest 4 requires class/function syntax for constructor mocks (arrow functions don't work with `new`)
// Use a class that creates fresh instances with the shared reference for assertions
let mockSpeechRecognitionInstance: MockSpeechRecognitionClass | null = null;

class MockSpeechRecognitionClass {
  start = vi.fn();
  stop = vi.fn();
  abort = vi.fn();
  addEventListener = vi.fn();
  removeEventListener = vi.fn();
  continuous = false;
  interimResults = false;
  lang = "en-US";
  onresult: ((event: unknown) => void) | null = null;
  onerror: ((event: unknown) => void) | null = null;
  onend: (() => void) | null = null;
  onstart: (() => void) | null = null;

  constructor() {
    // Store reference for test assertions
    // eslint-disable-next-line @typescript-eslint/no-this-alias
    mockSpeechRecognitionInstance = this;
  }
}

// Getter for current mock instance (for test assertions)
const getMockSpeechRecognition = () => mockSpeechRecognitionInstance!;

// Store original values
const originalSpeechRecognition = (
  window as { SpeechRecognition?: typeof SpeechRecognition }
).SpeechRecognition;
const originalWebkitSpeechRecognition = (
  window as { webkitSpeechRecognition?: typeof SpeechRecognition }
).webkitSpeechRecognition;

describe("useVoiceInput", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSpeechRecognitionInstance = null;
    // Set up SpeechRecognition mock
    (window as { SpeechRecognition?: unknown }).SpeechRecognition =
      MockSpeechRecognitionClass;
    (window as { webkitSpeechRecognition?: unknown }).webkitSpeechRecognition =
      MockSpeechRecognitionClass;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    // Restore original values
    (window as { SpeechRecognition?: unknown }).SpeechRecognition =
      originalSpeechRecognition;
    (window as { webkitSpeechRecognition?: unknown }).webkitSpeechRecognition =
      originalWebkitSpeechRecognition;
  });

  describe("Initial State", () => {
    it("should start with isListening false", () => {
      const { result } = renderHook(() => useVoiceInput());
      expect(result.current.isListening).toBe(false);
    });

    it("should start with empty transcript", () => {
      const { result } = renderHook(() => useVoiceInput());
      expect(result.current.transcript).toBe("");
    });

    it("should start with no error", () => {
      const { result } = renderHook(() => useVoiceInput());
      expect(result.current.error).toBeNull();
    });

    it("should detect browser support", () => {
      const { result } = renderHook(() => useVoiceInput());
      expect(result.current.isSupported).toBe(true);
    });

    it("should return isSupported false when not supported", () => {
      (window as { SpeechRecognition?: unknown }).SpeechRecognition = undefined;
      (
        window as { webkitSpeechRecognition?: unknown }
      ).webkitSpeechRecognition = undefined;

      const { result } = renderHook(() => useVoiceInput());
      expect(result.current.isSupported).toBe(false);
    });
  });

  describe("Start/Stop Recording", () => {
    it("should set isListening to true when startListening is called", () => {
      const { result } = renderHook(() => useVoiceInput());

      act(() => {
        result.current.startListening();
      });

      // Simulate start event
      act(() => {
        getMockSpeechRecognition().onstart?.();
      });

      expect(result.current.isListening).toBe(true);
    });

    it("should call recognition.start when startListening is called", () => {
      const { result } = renderHook(() => useVoiceInput());

      act(() => {
        result.current.startListening();
      });

      expect(getMockSpeechRecognition().start).toHaveBeenCalled();
    });

    it("should set isListening to false when stopListening is called", () => {
      const { result } = renderHook(() => useVoiceInput());

      act(() => {
        result.current.startListening();
      });

      act(() => {
        getMockSpeechRecognition().onstart?.();
      });

      act(() => {
        result.current.stopListening();
      });

      act(() => {
        getMockSpeechRecognition().onend?.();
      });

      expect(result.current.isListening).toBe(false);
    });

    it("should call recognition.stop when stopListening is called", () => {
      const { result } = renderHook(() => useVoiceInput());

      act(() => {
        result.current.startListening();
      });

      act(() => {
        result.current.stopListening();
      });

      expect(getMockSpeechRecognition().stop).toHaveBeenCalled();
    });
  });

  describe("Transcription", () => {
    it("should update transcript when results are received", () => {
      const { result } = renderHook(() => useVoiceInput());

      act(() => {
        result.current.startListening();
      });

      // Simulate speech result
      act(() => {
        const event = {
          results: [[{ transcript: "Hello world", confidence: 0.9 }]],
          resultIndex: 0,
        };
        getMockSpeechRecognition().onresult?.(event);
      });

      expect(result.current.transcript).toBe("Hello world");
    });

    it("should append to transcript with continuous mode", () => {
      const { result } = renderHook(() => useVoiceInput({ continuous: true }));

      act(() => {
        result.current.startListening();
      });

      // First result
      act(() => {
        const event = {
          results: [[{ transcript: "Hello", confidence: 0.9 }]],
          resultIndex: 0,
        };
        getMockSpeechRecognition().onresult?.(event);
      });

      // Second result
      act(() => {
        const event = {
          results: [
            [{ transcript: "Hello", confidence: 0.9, isFinal: true }],
            [{ transcript: " world", confidence: 0.9 }],
          ],
          resultIndex: 1,
        };
        getMockSpeechRecognition().onresult?.(event);
      });

      expect(result.current.transcript).toContain("world");
    });

    it("should call onTranscript callback with result", () => {
      const onTranscript = vi.fn();
      const { result } = renderHook(() => useVoiceInput({ onTranscript }));

      act(() => {
        result.current.startListening();
      });

      act(() => {
        const event = {
          results: [[{ transcript: "Test speech", confidence: 0.95 }]],
          resultIndex: 0,
        };
        getMockSpeechRecognition().onresult?.(event);
      });

      expect(onTranscript).toHaveBeenCalledWith("Test speech");
    });
  });

  describe("Error Handling", () => {
    it("should set error when recognition fails", () => {
      const { result } = renderHook(() => useVoiceInput());

      act(() => {
        result.current.startListening();
      });

      act(() => {
        const event = { error: "no-speech" };
        getMockSpeechRecognition().onerror?.(event);
      });

      expect(result.current.error).toBe("no-speech");
    });

    it("should call onError callback when error occurs", () => {
      const onError = vi.fn();
      const { result } = renderHook(() => useVoiceInput({ onError }));

      act(() => {
        result.current.startListening();
      });

      act(() => {
        const event = { error: "network" };
        getMockSpeechRecognition().onerror?.(event);
      });

      expect(onError).toHaveBeenCalledWith("network");
    });

    it("should set error when browser does not support speech recognition", () => {
      (window as { SpeechRecognition?: unknown }).SpeechRecognition = undefined;
      (
        window as { webkitSpeechRecognition?: unknown }
      ).webkitSpeechRecognition = undefined;

      const { result } = renderHook(() => useVoiceInput());

      act(() => {
        result.current.startListening();
      });

      expect(result.current.error).toBe(
        "Speech recognition is not supported in this browser",
      );
    });
  });

  describe("Clear Transcript", () => {
    it("should clear transcript when clearTranscript is called", () => {
      const { result } = renderHook(() => useVoiceInput());

      act(() => {
        result.current.startListening();
      });

      act(() => {
        const event = {
          results: [[{ transcript: "Some text", confidence: 0.9 }]],
          resultIndex: 0,
        };
        getMockSpeechRecognition().onresult?.(event);
      });

      act(() => {
        result.current.clearTranscript();
      });

      expect(result.current.transcript).toBe("");
    });
  });

  describe("Options", () => {
    it("should use specified language", () => {
      renderHook(() => useVoiceInput({ language: "es-ES" }));

      expect(getMockSpeechRecognition().lang).toBe("es-ES");
    });

    it("should set continuous mode", () => {
      renderHook(() => useVoiceInput({ continuous: true }));

      expect(getMockSpeechRecognition().continuous).toBe(true);
    });

    it("should enable interim results", () => {
      renderHook(() => useVoiceInput({ interimResults: true }));

      expect(getMockSpeechRecognition().interimResults).toBe(true);
    });
  });

  describe("Lifecycle", () => {
    it("should stop recognition on unmount", () => {
      const { unmount } = renderHook(() => useVoiceInput());

      unmount();

      expect(getMockSpeechRecognition().abort).toHaveBeenCalled();
    });
  });
});
