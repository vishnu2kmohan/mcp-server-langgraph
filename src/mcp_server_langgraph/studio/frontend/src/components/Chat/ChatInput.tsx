/**
 * ChatInput Component
 *
 * Input field for composing and sending chat messages.
 */

import { useState, KeyboardEvent } from "react";
import { Send } from "lucide-react";

import { Button, Textarea } from "@/components/UI";

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
    <div className="flex items-end gap-2 p-4 border-t border-neutral-200 dark:border-neutral-700">
      <Textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isDisabled}
        placeholder={placeholder}
        rows={1}
        className={`flex-1 px-4 py-2 border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 ${
          isDisabled
            ? "bg-neutral-100 dark:bg-neutral-800 cursor-not-allowed"
            : "bg-white dark:bg-neutral-900"
        } border-neutral-300 dark:border-neutral-600 text-neutral-900 dark:text-neutral-100`}
      />
      <Button
        className="p-2 rounded-lg"
        onClick={handleSend}
        disabled={isDisabled}
        aria-label="Send message"
      >
        <Send size={20} />
      </Button>
    </div>
  );
}
