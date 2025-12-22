/**
 * useVoiceInput Hook
 *
 * Custom hook for voice input using Web Speech API.
 * Features:
 * - Start/stop recording
 * - Transcription results
 * - Error handling
 * - Browser support detection
 * - Continuous mode support
 */

import { useState, useCallback, useRef, useEffect, useMemo } from "react";

/**
 * Web Speech API type declarations
 * These types are not included in TypeScript's lib.dom by default
 */
interface SpeechRecognition extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onstart: ((this: SpeechRecognition, ev: Event) => void) | null;
  onresult: ((this: SpeechRecognition, ev: Event) => void) | null;
  onerror: ((this: SpeechRecognition, ev: Event) => void) | null;
  onend: ((this: SpeechRecognition, ev: Event) => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

interface SpeechRecognitionConstructor {
  new (): SpeechRecognition;
  prototype: SpeechRecognition;
}

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

/**
 * Speech recognition result type
 */
interface SpeechResult {
  transcript: string;
  confidence: number;
  isFinal?: boolean;
}

/**
 * Speech recognition event types
 */
interface SpeechRecognitionEvent {
  results: SpeechResult[][];
  resultIndex: number;
}

interface SpeechRecognitionErrorEvent {
  error: string;
}

/**
 * Options for useVoiceInput hook
 */
export interface UseVoiceInputOptions {
  /** Language for speech recognition (e.g., 'en-US', 'es-ES') */
  language?: string;
  /** Enable continuous recognition */
  continuous?: boolean;
  /** Return interim (partial) results */
  interimResults?: boolean;
  /** Callback when transcript is updated */
  onTranscript?: (transcript: string) => void;
  /** Callback when error occurs */
  onError?: (error: string) => void;
  /** Callback when recording ends */
  onEnd?: () => void;
}

/**
 * Return type for useVoiceInput hook
 */
export interface UseVoiceInputReturn {
  /** Whether currently listening */
  isListening: boolean;
  /** Whether browser supports speech recognition */
  isSupported: boolean;
  /** Current transcript text */
  transcript: string;
  /** Current error message */
  error: string | null;
  /** Start listening for speech */
  startListening: () => void;
  /** Stop listening */
  stopListening: () => void;
  /** Clear the transcript */
  clearTranscript: () => void;
}

/**
 * Get SpeechRecognition constructor (handles vendor prefixes)
 */
function getSpeechRecognition(): SpeechRecognitionConstructor | null {
  if (typeof window === "undefined") return null;

  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

/**
 * Voice input hook using Web Speech API
 */
export function useVoiceInput(
  options: UseVoiceInputOptions = {},
): UseVoiceInputReturn {
  const {
    language = "en-US",
    continuous = false,
    interimResults = false,
    onTranscript,
    onError,
    onEnd,
  } = options;

  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Get SpeechRecognition constructor
  const SpeechRecognitionAPI = useMemo(() => getSpeechRecognition(), []);

  // Whether browser supports speech recognition
  const isSupported = SpeechRecognitionAPI !== null;

  // Reference to recognition instance
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  // Initialize recognition instance
  useEffect(() => {
    if (!SpeechRecognitionAPI) return;

    const recognition = new SpeechRecognitionAPI();
    recognition.lang = language;
    recognition.continuous = continuous;
    recognition.interimResults = interimResults;

    recognitionRef.current = recognition;

    // Cleanup on unmount
    return () => {
      recognition.abort();
    };
  }, [SpeechRecognitionAPI, language, continuous, interimResults]);

  // Set up event handlers
  useEffect(() => {
    const recognition = recognitionRef.current;
    if (!recognition) return;

    // Handle start
    recognition.onstart = () => {
      setIsListening(true);
      setError(null);
    };

    // Handle results
    recognition.onresult = (event: unknown) => {
      const speechEvent = event as SpeechRecognitionEvent;
      const results = speechEvent.results;

      // Get the latest transcript
      let finalTranscript = "";
      let interimTranscript = "";

      for (let i = speechEvent.resultIndex; i < results.length; i++) {
        const resultRow = results[i];
        if (!resultRow) continue;
        const result = resultRow[0];
        if (!result) continue;

        if (result.isFinal) {
          finalTranscript += result.transcript;
        } else {
          interimTranscript += result.transcript;
        }
      }

      const newTranscript = finalTranscript || interimTranscript;

      if (continuous) {
        setTranscript((prev) => prev + newTranscript);
        onTranscript?.(newTranscript);
      } else {
        setTranscript(newTranscript);
        onTranscript?.(newTranscript);
      }
    };

    // Handle error
    recognition.onerror = (event: unknown) => {
      const errorEvent = event as SpeechRecognitionErrorEvent;
      setError(errorEvent.error);
      onError?.(errorEvent.error);
    };

    // Handle end
    recognition.onend = () => {
      setIsListening(false);
      onEnd?.();
    };
  }, [continuous, onTranscript, onError, onEnd]);

  /**
   * Start listening for speech
   */
  const startListening = useCallback(() => {
    setError(null);

    if (!isSupported) {
      const errorMsg = "Speech recognition is not supported in this browser";
      setError(errorMsg);
      onError?.(errorMsg);
      return;
    }

    const recognition = recognitionRef.current;
    if (recognition) {
      try {
        recognition.start();
      } catch (err) {
        // May throw if already started
        console.warn("Speech recognition start error:", err);
      }
    }
  }, [isSupported, onError]);

  /**
   * Stop listening
   */
  const stopListening = useCallback(() => {
    const recognition = recognitionRef.current;
    if (recognition) {
      recognition.stop();
    }
  }, []);

  /**
   * Clear the transcript
   */
  const clearTranscript = useCallback(() => {
    setTranscript("");
  }, []);

  return {
    isListening,
    isSupported,
    transcript,
    error,
    startListening,
    stopListening,
    clearTranscript,
  };
}
