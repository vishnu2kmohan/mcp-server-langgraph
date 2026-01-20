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
        className="absolute inset-0 bg-neutral-a6"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Dialog content */}
      <div className="relative z-10 w-full max-w-2xl rounded-lg bg-neutral-1 p-6 shadow-xl">
        <h2
          id="elicitation-dialog-title"
          className="mb-4 text-xl font-semibold text-neutral-12"
        >
          Request User Input
        </h2>

        <div className="space-y-4">
          {/* Message input */}
          <div>
            <label
              htmlFor="elicitation-message"
              className="mb-1 block text-sm font-medium text-neutral-11"
            >
              Message
            </label>
            <Textarea
              className="px-3 py-2 text-neutral-12 -500 focus:ring-primary-7"
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
              className="mb-1 block text-sm font-medium text-neutral-11"
            >
              Schema (Optional JSON)
            </label>
            <Textarea
              id="elicitation-schema"
              value={schemaText}
              onChange={handleSchemaChange}
              className={`w-full rounded-md border px-3 py-2 text-neutral-12 focus:outline-none focus:ring-1 ${
                schemaError
                  ? "border-error-9 focus:border-error-9 focus:ring-error-7"
                  : "border-neutral-5 focus:border-primary-9 focus:ring-primary-7"
              }`}
              rows={4}
              placeholder='{"type": "object", "properties": {"name": {"type": "string"}}}'
            />
            {schemaError && (
              <p className="mt-1 text-sm text-error-10 dark:text-error-7">
                {schemaError}
              </p>
            )}
          </div>

          {/* Request error */}
          {requestError && (
            <div className="rounded-md bg-error-1 p-4 text-error-11 dark:bg-error-a3 dark:text-error-7">
              {requestError}
            </div>
          )}

          {/* Response display */}
          {response && (
            <div
              className={`rounded-md p-4 ${
                response.action === "accept"
                  ? "bg-success-1 text-success-11 dark:bg-success-a3 dark:text-success-7"
                  : "bg-warning-3 text-warning-10 bg-warning-3 dark:text-warning-9"
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
            className="rounded-md border border-neutral-5 bg-neutral-1 px-4 py-2 text-sm text-neutral-11 hover:bg-neutral-1 focus:ring-primary-7 focus:ring-offset-2"
            type="button"
            onClick={onClose}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            className="rounded-md bg-primary-10 px-4 py-2 text-sm text-neutral-12 hover:bg-primary-11 focus:ring-primary-7 focus:ring-offset-2"
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
