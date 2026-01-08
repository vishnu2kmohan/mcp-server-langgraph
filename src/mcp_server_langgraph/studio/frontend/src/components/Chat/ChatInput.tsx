/**
 * ChatInput Component
 *
 * Input field for composing and sending chat messages.
 */

import { useState, KeyboardEvent } from "react";
import { Send } from "lucide-react";

export interface ChatInputProps {
  onSend: (message: string) => void;
  isDisabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSend,
  isDisabled = false,
  placeholder = "Type a message...",
}: ChatInputProps) {
  const [message, setMessage] = useState("");

  const handleSend = () => {
    const trimmedMessage = message.trim();
    if (trimmedMessage && !isDisabled) {
      onSend(trimmedMessage);
      setMessage("");
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex items-end gap-2 p-4 border-t border-gray-200 dark:border-gray-700">
      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isDisabled}
        placeholder={placeholder}
        rows={1}
        className={`flex-1 px-4 py-2 border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 ${
          isDisabled
            ? "bg-gray-100 dark:bg-gray-800 cursor-not-allowed"
            : "bg-white dark:bg-gray-900"
        } border-gray-300 dark:border-gray-600 text-gray-900 dark:text-gray-100`}
      />
      <button
        onClick={handleSend}
        disabled={isDisabled}
        aria-label="Send message"
        className={`p-2 rounded-lg transition-colors ${
          isDisabled
            ? "bg-gray-300 dark:bg-gray-600 dark:bg-gray-700 cursor-not-allowed"
            : "bg-primary-600 hover:bg-primary-700 text-white"
        }`}
      >
        <Send size={20} />
      </button>
    </div>
  );
}
