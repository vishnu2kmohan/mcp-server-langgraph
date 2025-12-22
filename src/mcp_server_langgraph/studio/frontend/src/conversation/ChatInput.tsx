/**
 * ChatInput - Phase 2
 *
 * Rich chat input component with slash command support,
 * auto-resize, loading states, and keyboard handling.
 */
import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Loader2 } from "lucide-react";
import { cn } from "../utils/cn";

// =============================================================================
// Types
// =============================================================================

export interface ChatInputProps {
  onSend: (message: string) => void;
  onSlashCommand?: (command: string) => void;
  /** Called on every input change (for AI intent detection) */
  onInputChange?: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  isLoading?: boolean;
  autoFocus?: boolean;
  ariaLabel?: string;
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function ChatInput({
  onSend,
  onSlashCommand,
  onInputChange,
  placeholder = "Type a message...",
  disabled = false,
  isLoading = false,
  autoFocus = false,
  ariaLabel,
  className,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const [showSlashIndicator, setShowSlashIndicator] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Focus on mount if autoFocus
  useEffect(() => {
    if (autoFocus && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [autoFocus]);

  // Auto-resize textarea based on content
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [value]);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const newValue = e.target.value;
      setValue(newValue);

      // Notify parent of all input changes (for AI intent detection)
      onInputChange?.(newValue);

      // Detect slash command
      if (newValue.startsWith("/")) {
        setShowSlashIndicator(true);
        onSlashCommand?.(newValue);
      } else {
        setShowSlashIndicator(false);
      }
    },
    [onSlashCommand, onInputChange],
  );

  const handleSend = useCallback(() => {
    const trimmedValue = value.trim();
    if (!trimmedValue || disabled || isLoading) return;

    onSend(trimmedValue);
    setValue("");
    setShowSlashIndicator(false);

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [value, disabled, isLoading, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      // Enter without Shift sends the message
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const isDisabled = disabled || isLoading;
  const canSend = value.trim().length > 0 && !isDisabled;

  return (
    <div
      data-testid="chat-input-container"
      className={cn(
        "relative flex items-end gap-2 p-4",
        "bg-white dark:bg-gray-900",
        "border-t border-gray-200 dark:border-gray-700",
        className,
      )}
    >
      {/* Slash command indicator */}
      {showSlashIndicator && (
        <div
          data-testid="slash-command-indicator"
          className="absolute left-4 bottom-full mb-2 px-2 py-1 bg-gray-800 dark:bg-gray-700 text-white text-xs rounded"
        >
          Type a command...
        </div>
      )}

      {/* Textarea */}
      <div className="relative flex-1">
        <textarea
          ref={textareaRef}
          data-testid="chat-input"
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isDisabled}
          aria-label={ariaLabel}
          rows={1}
          className={cn(
            "w-full px-4 py-2 resize-none",
            "bg-gray-100 dark:bg-gray-800",
            "border border-gray-200 dark:border-gray-700",
            "rounded-2xl",
            "text-gray-900 dark:text-gray-100",
            "placeholder-gray-500 dark:placeholder-gray-400",
            "focus:outline-none focus:ring-2 focus:ring-primary-500",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            "transition-all",
          )}
        />
      </div>

      {/* Send button */}
      <button
        data-testid="send-button"
        type="button"
        onClick={handleSend}
        disabled={!canSend}
        className={cn(
          "flex items-center justify-center",
          "w-10 h-10 rounded-full",
          "bg-primary-500 text-white",
          "hover:bg-primary-600",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          "transition-colors",
        )}
        aria-label="Send message"
      >
        {isLoading ? (
          <Loader2
            data-testid="loading-spinner"
            size={18}
            className="animate-spin"
          />
        ) : (
          <Send size={18} />
        )}
      </button>
    </div>
  );
}
