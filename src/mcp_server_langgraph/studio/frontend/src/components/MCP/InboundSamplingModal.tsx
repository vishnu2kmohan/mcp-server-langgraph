/**
 * InboundSamplingModal Component
 *
 * A modal for handling server-initiated sampling/createMessage JSON-RPC requests.
 * When an MCP server sends a sampling request, this modal displays the
 * conversation and allows the user to provide a manual response or reject.
 *
 * Features:
 * - Display conversation history (user/assistant messages)
 * - Manual text input for response content
 * - System prompt display
 * - Model preferences display
 * - Accessible dialog with focus management
 * - Support for both numeric and string JSON-RPC IDs
 *
 * @see ADR-0069 MCP 2025-11-25 Upgrade
 */

import { useState, useCallback, useEffect, useRef } from "react";
import { X, Server, Bot, User, Cpu, AlertCircle } from "lucide-react";
import { cn } from "@/utils/cn";
import { Button, Textarea } from "@/components/UI";
import type {
  PendingSamplingRequest,
  SamplingResponse,
  SamplingMessage,
} from "@/types/mcp";

// ============================================================================
// Types
// ============================================================================

export interface InboundSamplingModalProps {
  /** The pending sampling request */
  request: PendingSamplingRequest;
  /** Called when user approves with a response */
  onApprove: (response: SamplingResponse) => void;
  /** Called when user rejects the request */
  onReject: () => void;
}

// ============================================================================
// Sub-Components
// ============================================================================

interface MessageBubbleProps {
  message: SamplingMessage;
}

function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const content =
    message.content.type === "text"
      ? message.content.text
      : `[${message.content.type} content]`;

  return (
    <div
      data-role={message.role}
      className={cn(
        "flex gap-2 rounded-lg p-3",
        isUser ? "bg-primary-3" : "bg-neutral-3",
      )}
    >
      <div
        className={cn(
          "flex h-6 w-6 shrink-0 items-center justify-center rounded-full",
          isUser
            ? "bg-primary-9 text-neutral-1"
            : "bg-neutral-9 text-neutral-1",
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div className="flex-1">
        <p className="text-xs font-medium text-neutral-10 mb-1">
          {isUser ? "User" : "Assistant"}
        </p>
        <p className="text-sm text-neutral-12 whitespace-pre-wrap">{content}</p>
      </div>
    </div>
  );
}

// ============================================================================
// Component
// ============================================================================

export function InboundSamplingModal({
  request,
  onApprove,
  onReject,
}: InboundSamplingModalProps) {
  // Response text state
  const [responseText, setResponseText] = useState("");

  // Focus management
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Focus textarea on mount
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  }, []);

  // Check if response is valid
  const isResponseValid = responseText.trim().length > 0;

  // Handle text change
  const handleTextChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setResponseText(e.target.value);
    },
    [],
  );

  // Handle approval
  const handleApprove = useCallback(() => {
    if (!isResponseValid) return;

    const response: SamplingResponse = {
      role: "assistant",
      content: { type: "text", text: responseText.trim() },
      model: "user-input",
      stopReason: "endTurn",
    };

    onApprove(response);
  }, [responseText, isResponseValid, onApprove]);

  // Handle form submission
  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      handleApprove();
    },
    [handleApprove],
  );

  // Get model hints display
  const modelHints = request.modelPreferences?.hints
    ?.map((h) => h.name)
    .filter(Boolean)
    .join(", ");

  return (
    <div
      role="dialog"
      aria-labelledby="sampling-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      {/* Backdrop */}
      <div
        data-testid="modal-backdrop"
        className="absolute inset-0 bg-neutral-a6"
        onClick={onReject}
        aria-hidden="true"
      />

      {/* Modal content */}
      <div className="relative z-10 w-full max-w-2xl max-h-[90vh] flex flex-col rounded-lg bg-neutral-1 shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-neutral-5 p-4">
          <h2
            id="sampling-modal-title"
            className="text-lg font-semibold text-neutral-12"
          >
            Sampling Request
          </h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={onReject}
            className="p-1"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Server info */}
          <div className="flex items-center gap-2 text-sm text-neutral-10">
            <Server className="h-4 w-4" />
            <span>From: {request.serverId}</span>
          </div>

          {/* Request details */}
          <div className="flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-1.5 text-neutral-10">
              <Cpu className="h-4 w-4" />
              <span>Max tokens: {request.maxTokens}</span>
            </div>
            {modelHints && (
              <div className="flex items-center gap-1.5 text-neutral-10">
                <Bot className="h-4 w-4" />
                <span>Preferred: {modelHints}</span>
              </div>
            )}
          </div>

          {/* System prompt */}
          {request.systemPrompt && (
            <div className="rounded-lg border border-neutral-5 bg-neutral-2 p-3">
              <p className="text-xs font-medium text-neutral-10 mb-1">
                System Prompt
              </p>
              <p className="text-sm text-neutral-11 whitespace-pre-wrap">
                {request.systemPrompt}
              </p>
            </div>
          )}

          {/* Message history */}
          <div className="space-y-2">
            <p className="text-xs font-medium text-neutral-10">
              Conversation ({request.messages.length} message
              {request.messages.length !== 1 ? "s" : ""})
            </p>
            <div className="space-y-2">
              {request.messages.map((message, index) => (
                <MessageBubble key={index} message={message} />
              ))}
            </div>
          </div>

          {/* Response input */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <label
                htmlFor="sampling-response"
                className="block text-sm font-medium text-neutral-12"
              >
                Your Response
              </label>
              <Textarea
                ref={textareaRef}
                id="sampling-response"
                aria-label="Response"
                value={responseText}
                onChange={handleTextChange}
                placeholder="Enter your response to this sampling request..."
                rows={4}
                className="w-full"
              />
              <p className="text-xs text-neutral-10">
                This response will be sent back to the MCP server as the
                assistant's reply.
              </p>
            </div>

            {/* Warning about manual response */}
            <div className="flex items-start gap-2 rounded-lg border border-warning-6 bg-warning-2 p-3">
              <AlertCircle className="h-4 w-4 text-warning-9 shrink-0 mt-0.5" />
              <p className="text-xs text-warning-11">
                You are manually providing a response instead of using an LLM.
                The MCP server will receive this as an AI-generated response.
              </p>
            </div>
          </form>
        </div>

        {/* Footer actions */}
        <div className="flex justify-end gap-3 border-t border-neutral-5 p-4">
          <Button type="button" variant="secondary" onClick={onReject}>
            Reject
          </Button>
          <Button
            type="button"
            variant="primary"
            onClick={handleApprove}
            disabled={!isResponseValid}
          >
            Approve
          </Button>
        </div>
      </div>
    </div>
  );
}

export default InboundSamplingModal;
