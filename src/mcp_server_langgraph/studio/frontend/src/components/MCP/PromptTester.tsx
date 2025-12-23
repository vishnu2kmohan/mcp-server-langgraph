/**
 * PromptTester Component
 *
 * A dialog for testing MCP prompts with dynamic argument handling.
 *
 * Features:
 * - List available prompts
 * - Dynamic form generation from prompt arguments
 * - Real-time validation
 * - Display generated messages
 */

import React, { useState, useCallback, useEffect, useMemo } from "react";
import {
  useListMcpPromptsQuery,
  useGetMcpPromptMutation,
} from "../../api";

export interface PromptTesterProps {
  open: boolean;
  onClose: () => void;
}

interface PromptArgument {
  name: string;
  description?: string;
  required: boolean;
}

interface PromptMessage {
  role: string;
  content: { type: string; text?: string };
}

interface PromptResult {
  messages: PromptMessage[];
}

export function PromptTester({ open, onClose }: PromptTesterProps) {
  const {
    data: promptsData,
    isLoading: isLoadingPrompts,
    error: promptsError,
  } = useListMcpPromptsQuery();
  const [getPrompt, { isLoading: isExecuting }] = useGetMcpPromptMutation();

  const [selectedPromptName, setSelectedPromptName] = useState<string>("");
  const [argumentValues, setArgumentValues] = useState<Record<string, string>>(
    {}
  );
  const [result, setResult] = useState<PromptResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Reset form when dialog closes
  useEffect(() => {
    if (!open) {
      setSelectedPromptName("");
      setArgumentValues({});
      setResult(null);
      setError(null);
    }
  }, [open]);

  // Get selected prompt details
  const selectedPrompt = useMemo(() => {
    if (!selectedPromptName || !promptsData?.prompts) return null;
    return (
      promptsData.prompts.find((p) => p.name === selectedPromptName) || null
    );
  }, [selectedPromptName, promptsData?.prompts]);

  // Get prompt arguments
  const promptArguments = useMemo((): PromptArgument[] => {
    if (!selectedPrompt?.arguments) return [];
    return selectedPrompt.arguments.map((arg) => ({
      name: arg.name,
      description: arg.description,
      required: arg.required ?? false,
    }));
  }, [selectedPrompt]);

  // Check if form is valid
  const isFormValid = useMemo(() => {
    if (!selectedPrompt) return false;

    const requiredArgs = promptArguments.filter((arg) => arg.required);
    return requiredArgs.every(
      (arg) =>
        argumentValues[arg.name] && argumentValues[arg.name].trim() !== ""
    );
  }, [selectedPrompt, promptArguments, argumentValues]);

  // Handle prompt selection
  const handlePromptSelect = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      setSelectedPromptName(e.target.value);
      setArgumentValues({});
      setResult(null);
      setError(null);
    },
    []
  );

  // Handle argument value change
  const handleArgumentChange = useCallback(
    (name: string, value: string) => {
      setArgumentValues((prev) => ({ ...prev, [name]: value }));
    },
    []
  );

  // Handle prompt execution
  const handleExecute = useCallback(async () => {
    if (!selectedPrompt || !isFormValid) return;

    setError(null);
    try {
      // Filter out empty optional arguments
      const args: Record<string, string> = {};
      for (const [key, value] of Object.entries(argumentValues)) {
        if (value.trim() !== "") {
          args[key] = value;
        }
      }

      const response = await getPrompt({
        name: selectedPrompt.name,
        arguments: args,
      }).unwrap();
      setResult(response);
    } catch (_err) {
      setError("Failed to execute prompt");
    }
  }, [selectedPrompt, argumentValues, isFormValid, getPrompt]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-labelledby="prompt-tester-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Dialog content */}
      <div className="relative z-10 flex h-[80vh] w-full max-w-3xl flex-col rounded-lg bg-white shadow-xl dark:bg-gray-800">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 p-4 dark:border-gray-700">
          <h2
            id="prompt-tester-title"
            className="text-xl font-semibold text-gray-900 dark:text-white"
          >
            Prompt Tester
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-gray-200"
            aria-label="Close"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Loading state */}
        {isLoadingPrompts && (
          <div className="flex flex-1 items-center justify-center">
            <span className="text-gray-500">Loading prompts...</span>
          </div>
        )}

        {/* Error state */}
        {promptsError && (
          <div className="flex flex-1 items-center justify-center">
            <div className="rounded-md bg-red-50 p-4 text-red-700 dark:bg-red-900/20 dark:text-red-400">
              Error loading prompts. Please try again.
            </div>
          </div>
        )}

        {/* Main content */}
        {!isLoadingPrompts && !promptsError && (
          <div className="flex flex-1 flex-col overflow-hidden p-4">
            {promptsData?.prompts.length === 0 ? (
              <div className="flex flex-1 items-center justify-center text-gray-500">
                No prompts available
              </div>
            ) : (
              <div className="flex flex-1 flex-col gap-4 overflow-hidden">
                {/* Prompt selection */}
                <div>
                  <label
                    htmlFor="prompt-select"
                    className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
                  >
                    Select Prompt
                  </label>
                  <select
                    id="prompt-select"
                    value={selectedPromptName}
                    onChange={handlePromptSelect}
                    className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                  >
                    <option value="">-- Select a prompt --</option>
                    {promptsData?.prompts.map((prompt) => (
                      <option key={prompt.name} value={prompt.name}>
                        {prompt.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Prompt description */}
                {selectedPrompt && (
                  <div className="rounded-md bg-gray-50 p-3 text-sm text-gray-600 dark:bg-gray-700/50 dark:text-gray-400">
                    {selectedPrompt.description}
                  </div>
                )}

                {/* Prompt arguments */}
                {selectedPrompt && promptArguments.length > 0 && (
                  <div className="space-y-3">
                    <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Arguments
                    </h3>
                    {promptArguments.map((arg) => (
                      <div key={arg.name}>
                        <label
                          htmlFor={`arg-${arg.name}`}
                          className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
                        >
                          {arg.name}
                          {arg.required && (
                            <span className="text-red-500">*</span>
                          )}
                        </label>
                        {arg.description && (
                          <p className="mb-1 text-xs text-gray-500 dark:text-gray-400">
                            {arg.description}
                          </p>
                        )}
                        <textarea
                          id={`arg-${arg.name}`}
                          value={argumentValues[arg.name] || ""}
                          onChange={(e) =>
                            handleArgumentChange(arg.name, e.target.value)
                          }
                          className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                          rows={3}
                          placeholder={arg.description}
                        />
                      </div>
                    ))}
                  </div>
                )}

                {/* Execute button */}
                {selectedPrompt && (
                  <div>
                    <button
                      type="button"
                      onClick={handleExecute}
                      disabled={!isFormValid || isExecuting}
                      className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {isExecuting ? "Executing..." : "Execute"}
                    </button>
                  </div>
                )}

                {/* Error display */}
                {error && (
                  <div className="rounded-md bg-red-50 p-4 text-red-700 dark:bg-red-900/20 dark:text-red-400">
                    {error}
                  </div>
                )}

                {/* Result display */}
                {result && (
                  <div className="flex-1 overflow-auto rounded-md bg-gray-50 p-4 dark:bg-gray-900">
                    <h3 className="mb-2 font-medium text-gray-900 dark:text-white">
                      Generated Messages
                    </h3>
                    <div className="space-y-3">
                      {result.messages.map((message, index) => (
                        <div
                          key={index}
                          className="rounded-md border border-gray-200 p-3 dark:border-gray-700"
                        >
                          <div className="mb-1 text-xs font-medium uppercase text-gray-500 dark:text-gray-400">
                            {message.role}
                          </div>
                          <div className="text-sm text-gray-800 dark:text-gray-200">
                            {message.content.text}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default PromptTester;
