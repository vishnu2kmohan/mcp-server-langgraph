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
import { useListMcpPromptsQuery, useGetMcpPromptMutation } from "../../api";

import { Button, Select, Textarea } from "@/components/UI";

export interface PromptTesterProps {
  open: boolean;
  onClose: () => void;
  /** Optional prompt name to pre-select when dialog opens */
  preselectedPromptName?: string;
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

export function PromptTester({
  open,
  onClose,
  preselectedPromptName,
}: PromptTesterProps) {
  const {
    data: promptsData,
    isLoading: isLoadingPrompts,
    error: promptsError,
  } = useListMcpPromptsQuery();
  const [getPrompt, { isLoading: isExecuting }] = useGetMcpPromptMutation();

  const [selectedPromptName, setSelectedPromptName] = useState<string>("");
  const [argumentValues, setArgumentValues] = useState<Record<string, string>>(
    {},
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

  // Pre-select prompt when preselectedPromptName is provided
  useEffect(() => {
    if (open && preselectedPromptName && promptsData?.prompts) {
      // Validate the prompt exists
      const promptExists = promptsData.prompts.some(
        (p) => p.name === preselectedPromptName,
      );
      if (promptExists) {
        setSelectedPromptName(preselectedPromptName);
      }
    }
  }, [open, preselectedPromptName, promptsData?.prompts]);

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
        argumentValues[arg.name] && argumentValues[arg.name].trim() !== "",
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
    [],
  );

  // Handle argument value change
  const handleArgumentChange = useCallback((name: string, value: string) => {
    setArgumentValues((prev) => ({ ...prev, [name]: value }));
  }, []);

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
    } catch {
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
      <div className="relative z-10 flex h-[80vh] w-full max-w-3xl flex-col rounded-lg bg-white shadow-xl dark:bg-neutral-800">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-neutral-200 dark:border-neutral-700 p-4 dark:border-neutral-700">
          <h2
            id="prompt-tester-title"
            className="text-xl font-semibold text-neutral-900 dark:text-white"
          >
            Prompt Tester
          </h2>
          <Button
            variant="secondary"
            className="rounded-md p-2 text-neutral-500 dark:text-neutral-400 hover:bg-neutral-100 dark:bg-neutral-800 hover:text-neutral-700 dark:text-neutral-200 dark:text-neutral-400 dark:hover:bg-neutral-700 dark:hover:text-neutral-200"
            type="button"
            onClick={onClose}
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
          </Button>
        </div>

        {/* Loading state */}
        {isLoadingPrompts && (
          <div className="flex flex-1 items-center justify-center">
            <span className="text-neutral-500 dark:text-neutral-400">
              Loading prompts...
            </span>
          </div>
        )}

        {/* Error state */}
        {promptsError && (
          <div className="flex flex-1 items-center justify-center">
            <div className="rounded-md bg-error-50 p-4 text-error-700 dark:bg-error-900/20 dark:text-error-400">
              Error loading prompts. Please try again.
            </div>
          </div>
        )}

        {/* Main content */}
        {!isLoadingPrompts && !promptsError && (
          <div className="flex flex-1 flex-col overflow-hidden p-4">
            {promptsData?.prompts.length === 0 ? (
              <div className="flex flex-1 items-center justify-center text-neutral-500 dark:text-neutral-400">
                No prompts available
              </div>
            ) : (
              <div className="flex flex-1 flex-col gap-4 overflow-hidden">
                {/* Prompt selection */}
                <div>
                  <label
                    htmlFor="prompt-select"
                    className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300"
                  >
                    Select Prompt
                  </label>
                  <Select
                    className="px-3 py-2 text-neutral-900 -500 focus:ring-primary-500 dark:border-neutral-600 dark:text-white"
                    id="prompt-select"
                    value={selectedPromptName}
                    onChange={handlePromptSelect}
                  >
                    <option value="">-- Select a prompt --</option>
                    {promptsData?.prompts.map((prompt) => (
                      <option key={prompt.name} value={prompt.name}>
                        {prompt.name}
                      </option>
                    ))}
                  </Select>
                </div>

                {/* Prompt description */}
                {selectedPrompt && (
                  <div className="rounded-md bg-neutral-50 p-3 text-sm text-neutral-600 dark:text-neutral-300 dark:bg-neutral-700/50 dark:text-neutral-400">
                    {selectedPrompt.description}
                  </div>
                )}

                {/* Prompt arguments */}
                {selectedPrompt && promptArguments.length > 0 && (
                  <div className="space-y-3">
                    <h3 className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
                      Arguments
                    </h3>
                    {promptArguments.map((arg) => (
                      <div key={arg.name}>
                        <label
                          htmlFor={`arg-${arg.name}`}
                          className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300"
                        >
                          {arg.name}
                          {arg.required && (
                            <span className="text-error-500">*</span>
                          )}
                        </label>
                        {arg.description && (
                          <p className="mb-1 text-xs text-neutral-500 dark:text-neutral-400">
                            {arg.description}
                          </p>
                        )}
                        <Textarea
                          className="px-3 py-2 text-neutral-900 -500 focus:ring-primary-500 dark:border-neutral-600 dark:text-white"
                          id={`arg-${arg.name}`}
                          value={argumentValues[arg.name] || ""}
                          onChange={(e) =>
                            handleArgumentChange(arg.name, e.target.value)
                          }
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
                    <Button
                      variant="primary"
                      className="rounded-md bg-primary-600 px-4 py-2 text-sm text-white hover:bg-primary-700 focus:ring-primary-500 focus:ring-offset-2"
                      type="button"
                      onClick={handleExecute}
                      disabled={!isFormValid || isExecuting}
                    >
                      {isExecuting ? "Executing..." : "Execute"}
                    </Button>
                  </div>
                )}

                {/* Error display */}
                {error && (
                  <div className="rounded-md bg-error-50 p-4 text-error-700 dark:bg-error-900/20 dark:text-error-400">
                    {error}
                  </div>
                )}

                {/* Result display */}
                {result && (
                  <div className="flex-1 overflow-auto rounded-md bg-neutral-50 p-4 dark:bg-neutral-900">
                    <h3 className="mb-2 font-medium text-neutral-900 dark:text-white">
                      Generated Messages
                    </h3>
                    <div className="space-y-3">
                      {result.messages.map((message, index) => (
                        <div
                          key={index}
                          className="rounded-md border border-neutral-200 dark:border-neutral-700 p-3 dark:border-neutral-700"
                        >
                          <div className="mb-1 text-xs font-medium uppercase text-neutral-500 dark:text-neutral-400">
                            {message.role}
                          </div>
                          <div className="text-sm text-neutral-800 dark:text-neutral-200">
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
