/**
 * ChatInputForm Component
 *
 * Rich chat input form with voice input, file uploads, and drag-drop support.
 */

import { Send, Mic, MicOff, Paperclip, X, Loader2, Square } from "lucide-react";
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

  const canSend = input.trim().length > 0 && !isProcessing;

  return (
    <div className="relative" {...dragHandlers}>
      {isDragging && (
        <div
          data-testid="drop-zone-overlay"
          className="absolute inset-0 bg-blue-500/20 border-2 border-dashed border-blue-500 rounded-lg flex items-center justify-center z-10"
        >
          <p className="text-blue-600 font-medium">Drop files here</p>
        </div>
      )}

      {uploadFiles.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-2">
          {uploadFiles.map((file) => (
            <div
              key={file.id}
              className="flex items-center gap-2 bg-gray-100 dark:bg-gray-800 px-3 py-1 rounded-full text-sm"
            >
              <span>{file.file.name}</span>
              {file.status === "uploading" && (
                <span className="text-blue-500">{file.progress}%</span>
              )}
              {file.status === "error" && (
                <span className="text-red-500">{file.error}</span>
              )}
              <button
                type="button"
                onClick={() => onRemoveFile(file.id)}
                aria-label="Remove file"
                className="text-gray-500 hover:text-red-500"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {voiceError && <p className="text-red-500 text-sm mb-2">{voiceError}</p>}

      {fileError && <p className="text-red-500 text-sm mb-2">{fileError}</p>}

      {isListening && (
        <div
          data-testid="recording-indicator"
          className="flex items-center gap-2 mb-2 text-red-500"
        >
          <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
          <span>Listening...</span>
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        data-testid="chat-input-form"
        className="flex items-center gap-2"
      >
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
          className="p-2 text-gray-500 hover:text-gray-700 disabled:opacity-50"
          onClick={() => document.getElementById("chat-file-input")?.click()}
        >
          <Paperclip className="w-5 h-5" />
        </button>

        <input
          type="text"
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          placeholder="Type your message..."
          disabled={isProcessing}
          className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border-gray-300 dark:border-gray-600 placeholder-gray-500 dark:placeholder-gray-400"
        />

        {isVoiceSupported && (
          <button
            type="button"
            onClick={isListening ? onStopListening : onStartListening}
            disabled={isProcessing}
            aria-label={isListening ? "Stop voice input" : "Start voice input"}
            className={
              isListening
                ? "p-2 text-red-500 disabled:opacity-50"
                : "p-2 text-gray-500 hover:text-gray-700 disabled:opacity-50"
            }
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
            className="p-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
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
      </form>
    </div>
  );
}
