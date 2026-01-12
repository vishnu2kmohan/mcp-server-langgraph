/**
 * ToolInvocationDialog Component
 *
 * A dialog for invoking MCP tools with dynamic form generation based on
 * the tool's input schema.
 *
 * Features:
 * - Tool selection from available tools
 * - Dynamic form generation from JSON Schema
 * - Real-time validation
 * - Result display with error handling
 */

import React, { useState, useCallback, useEffect, useMemo } from "react";
import { useListMcpToolsQuery, useInvokeMcpToolMutation } from "../../api";

import { Button, Input, Select } from "@/components/UI";

export interface ToolInvocationDialogProps {
  open: boolean;
  onClose: () => void;
  /** Optional tool name to pre-select when dialog opens */
  preselectedToolName?: string;
}

interface ToolArgument {
  name: string;
  type: string;
  description?: string;
  required: boolean;
}

interface ToolResult {
  content: Array<{
    type: string;
    text?: string;
    data?: string;
    mimeType?: string;
  }>;
  isError: boolean;
}

export function ToolInvocationDialog({
  open,
  onClose,
  preselectedToolName,
}: ToolInvocationDialogProps) {
  const {
    data: toolsData,
    isLoading: isLoadingTools,
    error: toolsError,
  } = useListMcpToolsQuery();
  const [invokeTool, { isLoading: isInvoking }] = useInvokeMcpToolMutation();

  const [selectedToolName, setSelectedToolName] = useState<string>("");
  const [argumentValues, setArgumentValues] = useState<Record<string, string>>(
    {},
  );
  const [result, setResult] = useState<ToolResult | null>(null);

  // Reset form when dialog closes
  useEffect(() => {
    if (!open) {
      setSelectedToolName("");
      setArgumentValues({});
      setResult(null);
    }
  }, [open]);

  // Pre-select tool when preselectedToolName is provided
  useEffect(() => {
    if (open && preselectedToolName && toolsData?.tools) {
      // Validate the tool exists
      const toolExists = toolsData.tools.some(
        (t) => t.name === preselectedToolName,
      );
      if (toolExists) {
        setSelectedToolName(preselectedToolName);
      }
    }
  }, [open, preselectedToolName, toolsData?.tools]);

  // Get selected tool details
  const selectedTool = useMemo(() => {
    if (!selectedToolName || !toolsData?.tools) return null;
    return toolsData.tools.find((t) => t.name === selectedToolName) || null;
  }, [selectedToolName, toolsData?.tools]);

  // Parse input schema to get arguments
  const toolArguments = useMemo((): ToolArgument[] => {
    if (!selectedTool?.inputSchema) return [];

    const schema = selectedTool.inputSchema as {
      properties?: Record<string, { type?: string; description?: string }>;
      required?: string[];
    };

    if (!schema.properties) return [];

    const required = schema.required || [];

    return Object.entries(schema.properties).map(([name, prop]) => ({
      name,
      type: prop.type || "string",
      description: prop.description,
      required: required.includes(name),
    }));
  }, [selectedTool]);

  // Check if form is valid
  const isFormValid = useMemo(() => {
    if (!selectedTool) return false;

    const requiredArgs = toolArguments.filter((arg) => arg.required);
    return requiredArgs.every(
      (arg) =>
        argumentValues[arg.name] && argumentValues[arg.name].trim() !== "",
    );
  }, [selectedTool, toolArguments, argumentValues]);

  // Handle tool selection
  const handleToolSelect = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      setSelectedToolName(e.target.value);
      setArgumentValues({});
      setResult(null);
    },
    [],
  );

  // Handle argument value change
  const handleArgumentChange = useCallback((name: string, value: string) => {
    setArgumentValues((prev) => ({ ...prev, [name]: value }));
  }, []);

  // Handle tool invocation
  const handleInvoke = useCallback(async () => {
    if (!selectedTool || !isFormValid) return;

    try {
      const response = await invokeTool({
        name: selectedTool.name,
        arguments: argumentValues,
      }).unwrap();
      setResult(response);
    } catch (error) {
      setResult({
        content: [{ type: "text", text: String(error) }],
        isError: true,
      });
    }
  }, [selectedTool, argumentValues, isFormValid, invokeTool]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-labelledby="tool-invocation-title"
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
          id="tool-invocation-title"
          className="mb-4 text-xl font-semibold text-neutral-900 dark:text-white"
        >
          Invoke Tool
        </h2>

        {/* Loading state */}
        {isLoadingTools && (
          <div className="flex items-center justify-center py-8">
            <span className="text-neutral-500 dark:text-neutral-400">
              Loading tools...
            </span>
          </div>
        )}

        {/* Error state */}
        {toolsError && (
          <div className="rounded-md bg-error-50 p-4 text-error-700 dark:bg-error-900/20 dark:text-error-400">
            Error loading tools. Please try again.
          </div>
        )}

        {/* Tools loaded */}
        {!isLoadingTools && !toolsError && (
          <div className="space-y-4">
            {/* Tool selection */}
            <div>
              <label
                htmlFor="tool-select"
                className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300"
              >
                Select Tool
              </label>
              <Select
                className="px-3 py-2 text-neutral-900 -500 focus:ring-primary-500 dark:border-neutral-600 dark:text-white"
                id="tool-select"
                value={selectedToolName}
                onChange={handleToolSelect}
              >
                <option value="">-- Select a tool --</option>
                {toolsData?.tools.map((tool) => (
                  <option key={tool.name} value={tool.name}>
                    {tool.name}
                  </option>
                ))}
              </Select>
            </div>

            {/* Tool description */}
            {selectedTool && (
              <div className="rounded-md bg-neutral-50 p-3 text-sm text-neutral-600 dark:text-neutral-300 dark:bg-neutral-700/50 dark:text-neutral-400">
                {selectedTool.description}
              </div>
            )}

            {/* Tool arguments */}
            {selectedTool && toolArguments.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
                  Arguments
                </h3>
                {toolArguments.map((arg) => (
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
                    <Input
                      className="px-3 py-2 text-neutral-900 -500 focus:ring-primary-500 dark:border-neutral-600 dark:text-white"
                      id={`arg-${arg.name}`}
                      value={argumentValues[arg.name] || ""}
                      onChange={(e) =>
                        handleArgumentChange(arg.name, e.target.value)
                      }
                      placeholder={arg.type}
                    />
                  </div>
                ))}
              </div>
            )}

            {/* Result display */}
            {result && (
              <div
                className={`rounded-md p-4 ${
                  result.isError
                    ? "bg-error-50 text-error-700 dark:bg-error-900/20 dark:text-error-400"
                    : "bg-success-50 text-success-700 dark:bg-success-900/20 dark:text-success-400"
                }`}
              >
                <h3 className="mb-2 font-medium">
                  {result.isError ? "Error" : "Result"}
                </h3>
                <pre className="whitespace-pre-wrap text-sm">
                  {result.content.map((c, i) => (
                    <span key={i}>{c.text}</span>
                  ))}
                </pre>
              </div>
            )}
          </div>
        )}

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
            onClick={handleInvoke}
            disabled={!isFormValid || isInvoking}
          >
            {isInvoking ? "Invoking..." : "Invoke"}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default ToolInvocationDialog;
