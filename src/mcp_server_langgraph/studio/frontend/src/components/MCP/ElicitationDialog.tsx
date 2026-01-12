/**
 * ElicitationDialog Component
 *
 * A dialog for requesting user input through MCP elicitation.
 *
 * Features:
 * - Message input for elicitation prompt
 * - Optional JSON schema for structured input
 * - Schema validation
 * - Response display (accept/decline)
 */

import React, { useState, useCallback, useEffect, useMemo } from "react";
import { useRequestMcpElicitationMutation } from "../../api";

import { Button, Textarea } from "@/components/UI";

export interface ElicitationDialogProps {
  open: boolean;
  onClose: () => void;
}

interface ElicitationResponse {
  action: "accept" | "decline" | "cancel";
  content?: Record<string, unknown> | null;
}

export function ElicitationDialog({ open, onClose }: ElicitationDialogProps) {
  const [requestElicitation, { isLoading }] =
    useRequestMcpElicitationMutation();

  const [message, setMessage] = useState("");
  const [schemaText, setSchemaText] = useState("");
  const [schemaError, setSchemaError] = useState<string | null>(null);
  const [response, setResponse] = useState<ElicitationResponse | null>(null);
  const [requestError, setRequestError] = useState<string | null>(null);

  // Reset form when dialog closes
  useEffect(() => {
    if (!open) {
      setMessage("");
      setSchemaText("");
      setSchemaError(null);
      setResponse(null);
      setRequestError(null);
    }
  }, [open]);

  // Parse and validate schema
  const parsedSchema = useMemo(() => {
    if (!schemaText.trim()) return { parsed: null, error: null };

    try {
      const parsed = JSON.parse(schemaText);
      return { parsed, error: null };
    } catch {
      return { parsed: undefined, error: "Invalid JSON schema" }; // undefined means invalid, null means empty
    }
  }, [schemaText]);

  // Update schema error when parsing result changes
  useEffect(() => {
    setSchemaError(parsedSchema.error);
  }, [parsedSchema.error]);

  // Check if form is valid
  const isFormValid = useMemo(() => {
    if (!message.trim()) return false;
    if (schemaText.trim() && parsedSchema.parsed === undefined) return false;
    return true;
  }, [message, schemaText, parsedSchema.parsed]);

  // Handle message change
  const handleMessageChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setMessage(e.target.value);
    },
    [],
  );

  // Handle schema change
  const handleSchemaChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setSchemaText(e.target.value);
    },
    [],
  );

  // Handle send request
  const handleSend = useCallback(async () => {
    if (!isFormValid) return;

    setRequestError(null);
    setResponse(null);

    try {
      const result = await requestElicitation({
        message: message.trim(),
        schema: parsedSchema.parsed ?? null,
      }).unwrap();
      setResponse(result);
    } catch {
      setRequestError("Failed to send elicitation request");
    }
  }, [isFormValid, message, parsedSchema.parsed, requestElicitation]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-labelledby="elicitation-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Dialog content */}
      <div className="relative z-10 w-full max-w-2xl rounded-lg bg-white p-6 shadow-xl dark:bg-neutral-800">
        <h2
          id="elicitation-dialog-title"
          className="mb-4 text-xl font-semibold text-neutral-900 dark:text-white"
        >
          Request User Input
        </h2>

        <div className="space-y-4">
          {/* Message input */}
          <div>
            <label
              htmlFor="elicitation-message"
              className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300"
            >
              Message
            </label>
            <Textarea
              className="px-3 py-2 text-neutral-900 -500 focus:ring-primary-500 dark:border-neutral-600 dark:text-white"
              id="elicitation-message"
              value={message}
              onChange={handleMessageChange}
              rows={3}
              placeholder="Enter the message to display to the user"
            />
          </div>

          {/* Schema input */}
          <div>
            <label
              htmlFor="elicitation-schema"
              className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300"
            >
              Schema (Optional JSON)
            </label>
            <Textarea
              id="elicitation-schema"
              value={schemaText}
              onChange={handleSchemaChange}
              className={`w-full rounded-md border px-3 py-2 text-neutral-900 focus:outline-none focus:ring-1 dark:bg-neutral-700 dark:text-white ${
                schemaError
                  ? "border-error-500 focus:border-error-500 focus:ring-error-500"
                  : "border-neutral-300 dark:border-neutral-600 focus:border-primary-500 focus:ring-primary-500 dark:border-neutral-600"
              }`}
              rows={4}
              placeholder='{"type": "object", "properties": {"name": {"type": "string"}}}'
            />
            {schemaError && (
              <p className="mt-1 text-sm text-error-600 dark:text-error-400">
                {schemaError}
              </p>
            )}
          </div>

          {/* Request error */}
          {requestError && (
            <div className="rounded-md bg-error-50 p-4 text-error-700 dark:bg-error-900/20 dark:text-error-400">
              {requestError}
            </div>
          )}

          {/* Response display */}
          {response && (
            <div
              className={`rounded-md p-4 ${
                response.action === "accept"
                  ? "bg-success-50 text-success-700 dark:bg-success-900/20 dark:text-success-400"
                  : "bg-warning-50 text-warning-700 dark:bg-warning-900/20 dark:text-warning-400"
              }`}
            >
              <h3 className="mb-2 font-medium">
                {response.action === "accept"
                  ? "User Accepted"
                  : "User Declined"}
              </h3>
              {response.content && (
                <pre className="whitespace-pre-wrap text-sm">
                  {JSON.stringify(response.content, null, 2)}
                </pre>
              )}
            </div>
          )}
        </div>

        {/* Dialog actions */}
        <div className="mt-6 flex justify-end gap-3">
          <Button
            variant="secondary"
            className="rounded-md border border-neutral-300 dark:border-neutral-600 bg-white px-4 py-2 text-sm text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 focus:ring-primary-500 focus:ring-offset-2 dark:border-neutral-600 dark:bg-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-600"
            type="button"
            onClick={onClose}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            className="rounded-md bg-primary-600 px-4 py-2 text-sm text-white hover:bg-primary-700 focus:ring-primary-500 focus:ring-offset-2"
            type="button"
            onClick={handleSend}
            disabled={!isFormValid || isLoading}
          >
            {isLoading ? "Sending..." : "Send"}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default ElicitationDialog;
