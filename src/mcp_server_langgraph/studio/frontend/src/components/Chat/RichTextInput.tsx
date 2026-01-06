/**
 * RichTextInput Component
 *
 * Rich text input with formatting support.
 * Features:
 * - Basic formatting (bold, italic, code)
 * - Keyboard shortcuts for formatting
 * - Mention system (@model, @file)
 * - Code block support
 * - Character count
 * - WCAG 2.1 AA accessibility
 */

import {
  useState,
  useRef,
  useCallback,
  useEffect,
  KeyboardEvent,
  ChangeEvent,
} from "react";
import { Bold, Italic, Code, FileCode, Plus, Minus } from "lucide-react";

// ==============================================================================
// Types
// ==============================================================================

export interface MentionOption {
  type: "model" | "file" | "user";
  value: string;
  label?: string;
}

export interface RichTextInputProps {
  /** Callback when text is submitted */
  onSubmit: (text: string) => void;
  /** Callback when text changes */
  onChange?: (text: string) => void;
  /** Controlled value */
  value?: string;
  /** Placeholder text */
  placeholder?: string;
  /** Mention options for autocomplete */
  mentionOptions?: MentionOption[];
  /** Maximum character length */
  maxLength?: number;
  /** Disabled state */
  disabled?: boolean;
  /** Additional CSS classes */
  className?: string;
  /**
   * Keyboard submit behavior (Sprint 5.2)
   * - true: Enter = submit, Shift+Enter = newline (ChatGPT style)
   * - false: Ctrl/Cmd+Enter = submit, Enter = newline (default, legacy)
   */
  submitOnEnter?: boolean;
  /**
   * Whether toolbar is expanded by default (Sprint 2.4)
   * - false: Toolbar collapsed, show + button to expand (default)
   * - true: Toolbar expanded, show formatting buttons
   */
  defaultToolbarExpanded?: boolean;
  // Inline Suggestions props (Sprint 3.3)
  /** Enable inline AI suggestions (ghost text) */
  enableInlineSuggestions?: boolean;
  /** Current suggestion text to display as ghost text */
  inlineSuggestion?: string;
  /** Callback when user accepts suggestion (Tab key) */
  onAcceptSuggestion?: (suggestion: string) => void;
  /** Callback when user dismisses suggestion (Escape key) */
  onDismissSuggestion?: () => void;
  /** Whether suggestion is loading */
  isSuggestionLoading?: boolean;
}

// ==============================================================================
// Helper Functions
// ==============================================================================

function wrapText(
  text: string,
  selectionStart: number,
  selectionEnd: number,
  prefix: string,
  suffix: string,
): { newText: string; newCursorPos: number } {
  const selectedText = text.slice(selectionStart, selectionEnd);
  const before = text.slice(0, selectionStart);
  const after = text.slice(selectionEnd);

  if (selectedText) {
    // Wrap selected text
    const newText = `${before}${prefix}${selectedText}${suffix}${after}`;
    return {
      newText,
      newCursorPos:
        selectionStart + prefix.length + selectedText.length + suffix.length,
    };
  } else {
    // Insert empty wrapper at cursor
    const newText = `${before}${prefix}${suffix}${after}`;
    return {
      newText,
      newCursorPos: selectionStart + prefix.length,
    };
  }
}

function insertCodeBlock(
  text: string,
  selectionStart: number,
  selectionEnd: number,
): { newText: string; newCursorPos: number } {
  const selectedText = text.slice(selectionStart, selectionEnd);
  const before = text.slice(0, selectionStart);
  const after = text.slice(selectionEnd);

  if (selectedText) {
    const newText = `${before}\`\`\`\n${selectedText}\n\`\`\`${after}`;
    return {
      newText,
      newCursorPos: selectionStart + 4 + selectedText.length + 4,
    };
  } else {
    const newText = `${before}\`\`\`\n\n\`\`\`${after}`;
    return {
      newText,
      newCursorPos: selectionStart + 4,
    };
  }
}

// ==============================================================================
// Component
// ==============================================================================

export function RichTextInput({
  onSubmit,
  onChange,
  value: controlledValue,
  placeholder = "",
  mentionOptions = [],
  maxLength,
  disabled = false,
  className = "",
  submitOnEnter = true,
  defaultToolbarExpanded = false,
  // Inline Suggestions props
  enableInlineSuggestions = false,
  inlineSuggestion,
  onAcceptSuggestion,
  onDismissSuggestion,
  isSuggestionLoading = false,
}: RichTextInputProps) {
  const [internalValue, setInternalValue] = useState("");
  const [showMentions, setShowMentions] = useState(false);
  const [mentionFilter, setMentionFilter] = useState("");
  const [mentionStartPos, setMentionStartPos] = useState(0);
  const [toolbarExpanded, setToolbarExpanded] = useState(
    defaultToolbarExpanded,
  );
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Use controlled or internal value
  const value = controlledValue ?? internalValue;
  const setValue = useCallback(
    (newValue: string) => {
      if (controlledValue === undefined) {
        setInternalValue(newValue);
      }
      onChange?.(newValue);
    },
    [controlledValue, onChange],
  );

  // Filter mentions based on current filter
  const filteredMentions = mentionOptions.filter((option) =>
    option.value.toLowerCase().includes(mentionFilter.toLowerCase()),
  );

  // Apply formatting wrapper
  const applyFormatting = useCallback(
    (prefix: string, suffix: string) => {
      const textarea = textareaRef.current;
      if (!textarea || disabled) return;

      const { selectionStart, selectionEnd } = textarea;
      const { newText, newCursorPos } = wrapText(
        value,
        selectionStart,
        selectionEnd,
        prefix,
        suffix,
      );

      setValue(newText);

      // Restore cursor position after React updates
      requestAnimationFrame(() => {
        textarea.focus();
        textarea.setSelectionRange(newCursorPos, newCursorPos);
      });
    },
    [value, setValue, disabled],
  );

  // Apply code block
  const applyCodeBlock = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea || disabled) return;

    const { selectionStart, selectionEnd } = textarea;
    const { newText, newCursorPos } = insertCodeBlock(
      value,
      selectionStart,
      selectionEnd,
    );

    setValue(newText);

    requestAnimationFrame(() => {
      textarea.focus();
      textarea.setSelectionRange(newCursorPos, newCursorPos);
    });
  }, [value, setValue, disabled]);

  // Handle formatting shortcuts
  const handleBold = useCallback(() => {
    applyFormatting("**", "**");
  }, [applyFormatting]);

  const handleItalic = useCallback(() => {
    applyFormatting("*", "*");
  }, [applyFormatting]);

  const handleCode = useCallback(() => {
    applyFormatting("`", "`");
  }, [applyFormatting]);

  // Handle text change
  const handleChange = useCallback(
    (e: ChangeEvent<HTMLTextAreaElement>) => {
      let newValue = e.target.value;

      // Apply maxLength if set
      if (maxLength && newValue.length > maxLength) {
        newValue = newValue.slice(0, maxLength);
      }

      setValue(newValue);

      // Check for mention trigger
      const cursorPos = e.target.selectionStart;
      const textBeforeCursor = newValue.slice(0, cursorPos);
      const lastAtIndex = textBeforeCursor.lastIndexOf("@");

      if (lastAtIndex !== -1) {
        const textAfterAt = textBeforeCursor.slice(lastAtIndex + 1);
        // Check if there's no space after @ (still typing mention)
        if (!textAfterAt.includes(" ") && mentionOptions.length > 0) {
          setShowMentions(true);
          setMentionFilter(textAfterAt);
          setMentionStartPos(lastAtIndex);
        } else {
          setShowMentions(false);
        }
      } else {
        setShowMentions(false);
      }
    },
    [setValue, maxLength, mentionOptions.length],
  );

  // Handle keyboard events
  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      // Submit handling based on user preference (Sprint 5.2)
      if (e.key === "Enter") {
        if (submitOnEnter) {
          // ChatGPT-style: Enter = submit, Shift+Enter = newline
          if (!e.shiftKey && !e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            if (value.trim()) {
              onSubmit(value);
              setValue("");
              setShowMentions(false);
            }
            return;
          }
        } else {
          // Legacy-style: Ctrl/Cmd+Enter = submit
          if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            if (value.trim()) {
              onSubmit(value);
              setValue("");
              setShowMentions(false);
            }
            return;
          }
        }
      }

      // Tab to accept inline suggestion (Sprint 3.3)
      if (
        e.key === "Tab" &&
        enableInlineSuggestions &&
        inlineSuggestion &&
        onAcceptSuggestion
      ) {
        e.preventDefault();
        onAcceptSuggestion(inlineSuggestion);
        return;
      }

      // Escape to close mentions or dismiss inline suggestion
      if (e.key === "Escape") {
        if (showMentions) {
          e.preventDefault();
          setShowMentions(false);
          return;
        }
        if (
          enableInlineSuggestions &&
          inlineSuggestion &&
          onDismissSuggestion
        ) {
          e.preventDefault();
          onDismissSuggestion();
          return;
        }
      }

      // Formatting shortcuts
      if (e.ctrlKey || e.metaKey) {
        // Ctrl+Shift+F to toggle toolbar (Sprint 2.4)
        if (e.shiftKey && e.key.toLowerCase() === "f") {
          e.preventDefault();
          setToolbarExpanded((prev) => !prev);
          return;
        }

        switch (e.key.toLowerCase()) {
          case "b":
            e.preventDefault();
            handleBold();
            break;
          case "i":
            e.preventDefault();
            handleItalic();
            break;
          case "`":
            e.preventDefault();
            handleCode();
            break;
        }
      }
    },
    [
      value,
      onSubmit,
      setValue,
      showMentions,
      handleBold,
      handleItalic,
      handleCode,
      submitOnEnter,
      enableInlineSuggestions,
      inlineSuggestion,
      onAcceptSuggestion,
      onDismissSuggestion,
    ],
  );

  // Handle mention selection
  const handleMentionSelect = useCallback(
    (option: MentionOption) => {
      const before = value.slice(0, mentionStartPos);
      // Calculate the end of the mention query (@ + filter text)
      const mentionEndPos = mentionStartPos + 1 + mentionFilter.length;
      const after = value.slice(mentionEndPos);
      const newValue = `${before}@${option.value} ${after}`;

      setValue(newValue);
      setShowMentions(false);
      setMentionFilter("");

      // Focus textarea after selection
      requestAnimationFrame(() => {
        textareaRef.current?.focus();
      });
    },
    [value, mentionStartPos, mentionFilter, setValue],
  );

  // Close mentions when clicking outside the component
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setShowMentions(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      {/* Formatting toolbar toggle and toolbar (Sprint 2.4 - collapsible) */}
      <div className="flex items-center gap-1 mb-2 p-1 border-b border-gray-200 dark:border-gray-700">
        {/* Toggle button - always visible */}
        <button
          type="button"
          onClick={() => setToolbarExpanded((prev) => !prev)}
          className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
          aria-label="Toggle formatting toolbar"
          aria-expanded={toolbarExpanded}
          title={
            toolbarExpanded
              ? "Hide formatting (Ctrl+Shift+F)"
              : "Show formatting (Ctrl+Shift+F)"
          }
        >
          {toolbarExpanded ? (
            <Minus
              className="w-4 h-4"
              aria-hidden="true"
              data-testid="minus-icon"
            />
          ) : (
            <Plus
              className="w-4 h-4"
              aria-hidden="true"
              data-testid="plus-icon"
            />
          )}
        </button>

        {/* Formatting buttons - only visible when expanded */}
        {toolbarExpanded && (
          <div
            data-testid="formatting-toolbar"
            className="flex items-center gap-1 transition-opacity duration-150"
            role="toolbar"
            aria-label="Text formatting"
          >
            <div className="w-px h-4 bg-gray-300 dark:bg-gray-600 mx-1" />

            <button
              type="button"
              onClick={handleBold}
              disabled={disabled}
              className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Bold"
              title="Bold (Ctrl+B)"
            >
              <Bold className="w-4 h-4" aria-hidden="true" />
            </button>

            <button
              type="button"
              onClick={handleItalic}
              disabled={disabled}
              className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Italic"
              title="Italic (Ctrl+I)"
            >
              <Italic className="w-4 h-4" aria-hidden="true" />
            </button>

            <button
              type="button"
              onClick={handleCode}
              disabled={disabled}
              className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Code"
              title="Inline code (Ctrl+`)"
            >
              <Code className="w-4 h-4" aria-hidden="true" />
            </button>

            <div className="w-px h-4 bg-gray-300 dark:bg-gray-600 mx-1" />

            <button
              type="button"
              onClick={applyCodeBlock}
              disabled={disabled}
              className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Code block"
              title="Code block"
            >
              <FileCode className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        )}
      </div>

      {/* Text input */}
      <div className="relative">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          maxLength={maxLength}
          aria-label="Message input"
          className="
            w-full min-h-[100px] p-3
            border border-gray-300 dark:border-gray-600
            rounded-lg resize-y
            bg-white dark:bg-gray-800
            text-gray-900 dark:text-gray-100
            placeholder-gray-500 dark:placeholder-gray-400
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
            disabled:opacity-50 disabled:cursor-not-allowed
          "
          aria-describedby={maxLength ? "character-count" : undefined}
        />

        {/* Mention suggestions */}
        {showMentions && filteredMentions.length > 0 && (
          <div
            data-testid="mention-suggestions"
            role="listbox"
            aria-label="Mention suggestions"
            className="
              absolute z-10 w-48 mt-1
              bg-white dark:bg-gray-800
              border border-gray-200 dark:border-gray-700
              rounded-lg shadow-lg
              max-h-48 overflow-y-auto
            "
          >
            {filteredMentions.map((option) => (
              <button
                key={`${option.type}-${option.value}`}
                type="button"
                role="option"
                onClick={() => handleMentionSelect(option)}
                className="
                  w-full px-3 py-2 text-left
                  hover:bg-gray-100 dark:hover:bg-gray-700
                  text-sm text-gray-900 dark:text-gray-100
                "
              >
                <span className="text-gray-500 dark:text-gray-400 mr-1">@</span>
                {option.label || option.value}
              </button>
            ))}
          </div>
        )}

        {/* Inline Suggestion Overlay (Sprint 3.3) */}
        {enableInlineSuggestions && value && inlineSuggestion && (
          <div
            data-testid="inline-suggestion-overlay"
            className="absolute left-0 top-0 pointer-events-none p-3 text-gray-400 dark:text-gray-500"
            aria-hidden="true"
          >
            <span className="invisible">{value}</span>
            <span className="text-gray-400 dark:text-gray-500 opacity-60">
              {inlineSuggestion}
            </span>
          </div>
        )}

        {/* Suggestion Loading Indicator (Sprint 3.3) */}
        {enableInlineSuggestions && isSuggestionLoading && (
          <div
            data-testid="suggestion-loading"
            className="absolute right-3 top-3"
          >
            <div className="w-4 h-4 border-2 border-gray-300 dark:border-gray-600 border-t-blue-500 rounded-full animate-spin" />
          </div>
        )}

        {/* Suggestion Hint (Sprint 3.3) */}
        {enableInlineSuggestions && value && inlineSuggestion && (
          <div
            data-testid="suggestion-hint"
            className="absolute right-3 bottom-3 text-xs text-gray-400 dark:text-gray-500 bg-white dark:bg-gray-800 px-1.5 py-0.5 rounded"
          >
            <kbd className="font-mono text-xs">Tab</kbd> to accept
          </div>
        )}
      </div>

      {/* Character count */}
      {maxLength && (
        <div
          id="character-count"
          className="mt-1 text-xs text-gray-500 dark:text-gray-400 text-right"
        >
          {value.length} / {maxLength}
        </div>
      )}

      {/* Live region for screen reader announcements (accessibility) */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {toolbarExpanded
          ? "Formatting toolbar expanded"
          : "Formatting toolbar collapsed"}
      </div>
    </div>
  );
}

export default RichTextInput;
