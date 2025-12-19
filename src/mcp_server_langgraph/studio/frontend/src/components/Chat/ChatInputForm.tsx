/**
 * ChatInputForm Component
 *
 * Rich chat input form with voice input, file uploads, and drag-drop support.
 *
 * Layout Design (inspired by ChatGPT, Claude, OpenWebUI):
 * ┌─────────────────────────────────────────────────────────────┐
 * │                     (Bottom padding zone)                    │
 * │  ┌───────────────────────────────────────────────────────┐  │
 * │  │  [📎]  Textarea (expandable)              [🎤] [Send] │  │
 * │  └───────────────────────────────────────────────────────┘  │
 * │                     (Bottom padding zone)                    │
 * └─────────────────────────────────────────────────────────────┘
 *
 * Features:
 * - Centered max-width container for readability on wide screens
 * - Bottom padding for comfortable spacing from page edge
 * - Multi-line textarea with auto-expand
 * - Consolidated controls grouped around input
 */

import { useRef, useEffect, useCallback } from "react";
import { Send, Mic, MicOff, Paperclip, X, Loader2, Square, Plus } from "lucide-react";
import type { UploadFile, DragHandlers } from "../../hooks/useFileUpload";

// Re-export for test compatibility
export type { UploadFile };

export interface ChatInputFormProps {
  input: string;
  onInputChange: (value: string) => void;
  onSubmit: () => void;
  isProcessing: boolean;
  /** Whether response is currently streaming (for stop button) */
  isStreaming?: boolean;
  /** Callback to stop streaming response */
  onStopStreaming?: () => void;
  isListening: boolean;
  isVoiceSupported: boolean;
  voiceError: string | null;
  onStartListening: () => void;
  onStopListening: () => void;
  uploadFiles: UploadFile[];
  isUploading: boolean;
  isDragging: boolean;
  fileError: string | null;
  onSelectFiles: (files: File[]) => void;
  onRemoveFile: (id: string) => void;
  dragHandlers: DragHandlers;
}

export function ChatInputForm({
  input,
  onInputChange,
  onSubmit,
  isProcessing,
  isStreaming = false,
  onStopStreaming,
  isListening,
  isVoiceSupported,
  voiceError,
  onStartListening,
  onStopListening,
  uploadFiles,
  isUploading,
  isDragging,
  fileError,
  onSelectFiles,
  onRemoveFile,
  dragHandlers,
}: ChatInputFormProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onSelectFiles(Array.from(e.target.files));
    }
    // Reset value to allow same file selection again
    e.target.value = "";
  };

  // Handle keyboard shortcuts (Enter to send, Shift+Enter for newline)
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (input.trim().length > 0 && !isProcessing) {
          onSubmit();
        }
      }
    },
    [input, isProcessing, onSubmit],
  );

  // Auto-resize textarea based on content
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      const newHeight = Math.min(textarea.scrollHeight, 200); // Max 200px height
      textarea.style.height = `${newHeight}px`;
    }
  }, [input]);

  const canSend = input.trim().length > 0 && !isProcessing;

  return (
    <div
      data-testid="chat-input-container"
      className="w-full px-4 pb-6 pt-4 max-w-4xl mx-auto"
      {...dragHandlers}
    >
      {/* Drop zone overlay */}
      {isDragging && (
        <div
          data-testid="drop-zone-overlay"
          className="absolute inset-0 bg-blue-500/20 border-2 border-dashed border-blue-500 rounded-lg flex items-center justify-center z-10"
        >
          <p className="text-blue-600 font-medium">Drop files here</p>
        </div>
      )}

      {/* Attached files preview */}
      {uploadFiles.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-2">
          {uploadFiles.map((file) => (
            <div
              key={file.id}
              className="flex items-center gap-2 bg-gray-100 dark:bg-gray-800 px-3 py-1.5 rounded-full text-sm border border-gray-200 dark:border-gray-700"
            >
              <span className="truncate max-w-[150px]">{file.file.name}</span>
              {file.status === "uploading" && (
                <span className="text-blue-500 text-xs">{file.progress}%</span>
              )}
              {file.status === "error" && (
                <span className="text-red-500 text-xs">{file.error}</span>
              )}
              <button
                type="button"
                onClick={() => onRemoveFile(file.id)}
                aria-label="Remove file"
                className="text-gray-400 hover:text-red-500 transition-colors"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Error messages */}
      {voiceError && (
        <p className="text-red-500 text-sm mb-2 px-1">{voiceError}</p>
      )}
      {fileError && (
        <p className="text-red-500 text-sm mb-2 px-1">{fileError}</p>
      )}

      {/* Recording indicator */}
      {isListening && (
        <div
          data-testid="recording-indicator"
          className="flex items-center gap-2 mb-3 text-red-500 px-1"
        >
          <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
          <span className="text-sm">Listening...</span>
        </div>
      )}

      {/* Main input form */}
      <form
        onSubmit={handleSubmit}
        data-testid="chat-input-form"
        className="relative"
      >
        {/* Input wrapper - ChatGPT/Claude style rounded container */}
        <div
          data-testid="input-wrapper"
          className="flex items-end gap-2 p-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-2xl shadow-sm focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent transition-all"
        >
          {/* Left controls - Attachment button */}
          <div className="flex items-center gap-1 pb-1">
            {/* Hidden file input */}
            <input
              type="file"
              multiple
              onChange={handleFileChange}
              className="sr-only"
              aria-hidden="true"
              id="chat-file-input"
            />
            <button
              type="button"
              disabled={isProcessing || isUploading}
              aria-label="Attach file"
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              onClick={() => document.getElementById("chat-file-input")?.click()}
            >
              <Plus className="w-5 h-5" />
            </button>
          </div>

          {/* Textarea - expandable multi-line input */}
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message..."
            disabled={isProcessing}
            rows={1}
            className="flex-1 px-2 py-2 bg-transparent text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 resize-none focus:outline-none disabled:opacity-50 min-h-[40px] max-h-[200px]"
          />

          {/* Right controls - Voice & Send */}
          <div className="flex items-center gap-1 pb-1">
            {isVoiceSupported && (
              <button
                type="button"
                onClick={isListening ? onStopListening : onStartListening}
                disabled={isProcessing}
                aria-label={isListening ? "Stop voice input" : "Start voice input"}
                className={`p-2 rounded-lg transition-colors ${
                  isListening
                    ? "text-red-500 bg-red-50 dark:bg-red-900/20"
                    : "text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                } disabled:opacity-50`}
              >
                {isListening ? (
                  <MicOff className="w-5 h-5" />
                ) : (
                  <Mic className="w-5 h-5" />
                )}
              </button>
            )}

            {/* Stop button when streaming, otherwise Send button */}
            {isStreaming && onStopStreaming ? (
              <button
                type="button"
                onClick={onStopStreaming}
                aria-label="Stop generating"
                className="p-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
                data-testid="stop-streaming-button"
              >
                <Square className="w-5 h-5" />
              </button>
            ) : (
              <button
                type="submit"
                disabled={!canSend}
                aria-label="Send"
                className="p-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isProcessing ? (
                  <Loader2
                    className="w-5 h-5 animate-spin"
                    data-testid="send-button-loading"
                  />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            )}
          </div>
        </div>
      </form>

      {/* Hint text */}
      <p className="text-xs text-gray-400 dark:text-gray-500 text-center mt-2">
        Press Enter to send, Shift+Enter for new line
      </p>
    </div>
  );
}
