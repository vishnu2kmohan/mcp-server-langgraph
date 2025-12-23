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
      <div className="relative z-10 w-full max-w-2xl rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
        <h2
          id="elicitation-dialog-title"
          className="mb-4 text-xl font-semibold text-gray-900 dark:text-white"
        >
          Request User Input
        </h2>

        <div className="space-y-4">
          {/* Message input */}
          <div>
            <label
              htmlFor="elicitation-message"
              className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Message
            </label>
            <textarea
              id="elicitation-message"
              value={message}
              onChange={handleMessageChange}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              rows={3}
              placeholder="Enter the message to display to the user"
            />
          </div>

          {/* Schema input */}
          <div>
            <label
              htmlFor="elicitation-schema"
              className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Schema (Optional JSON)
            </label>
            <textarea
              id="elicitation-schema"
              value={schemaText}
              onChange={handleSchemaChange}
              className={`w-full rounded-md border px-3 py-2 text-gray-900 focus:outline-none focus:ring-1 dark:bg-gray-700 dark:text-white ${
                schemaError
                  ? "border-red-500 focus:border-red-500 focus:ring-red-500"
                  : "border-gray-300 focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600"
              }`}
              rows={4}
              placeholder='{"type": "object", "properties": {"name": {"type": "string"}}}'
            />
            {schemaError && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                {schemaError}
              </p>
            )}
          </div>

          {/* Request error */}
          {requestError && (
            <div className="rounded-md bg-red-50 p-4 text-red-700 dark:bg-red-900/20 dark:text-red-400">
              {requestError}
            </div>
          )}

          {/* Response display */}
          {response && (
            <div
              className={`rounded-md p-4 ${
                response.action === "accept"
                  ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400"
                  : "bg-yellow-50 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400"
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
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSend}
            disabled={!isFormValid || isLoading}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isLoading ? "Sending..." : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ElicitationDialog;
