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
import {
  useListMcpToolsQuery,
  useInvokeMcpToolMutation,
} from "../../api";

export interface ToolInvocationDialogProps {
  open: boolean;
  onClose: () => void;
}

interface ToolArgument {
  name: string;
  type: string;
  description?: string;
  required: boolean;
}

interface ToolResult {
  content: Array<{ type: string; text?: string; data?: string; mimeType?: string }>;
  isError: boolean;
}

export function ToolInvocationDialog({
  open,
  onClose,
}: ToolInvocationDialogProps) {
  const { data: toolsData, isLoading: isLoadingTools, error: toolsError } = useListMcpToolsQuery();
  const [invokeTool, { isLoading: isInvoking }] = useInvokeMcpToolMutation();

  const [selectedToolName, setSelectedToolName] = useState<string>("");
  const [argumentValues, setArgumentValues] = useState<Record<string, string>>({});
  const [result, setResult] = useState<ToolResult | null>(null);

  // Reset form when dialog closes
  useEffect(() => {
    if (!open) {
      setSelectedToolName("");
      setArgumentValues({});
      setResult(null);
    }
  }, [open]);

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
      (arg) => argumentValues[arg.name] && argumentValues[arg.name].trim() !== ""
    );
  }, [selectedTool, toolArguments, argumentValues]);

  // Handle tool selection
  const handleToolSelect = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      setSelectedToolName(e.target.value);
      setArgumentValues({});
      setResult(null);
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
      <div className="relative z-10 w-full max-w-2xl rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
        <h2
          id="tool-invocation-title"
          className="mb-4 text-xl font-semibold text-gray-900 dark:text-white"
        >
          Invoke Tool
        </h2>

        {/* Loading state */}
        {isLoadingTools && (
          <div className="flex items-center justify-center py-8">
            <span className="text-gray-500">Loading tools...</span>
          </div>
        )}

        {/* Error state */}
        {toolsError && (
          <div className="rounded-md bg-red-50 p-4 text-red-700 dark:bg-red-900/20 dark:text-red-400">
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
                className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                Select Tool
              </label>
              <select
                id="tool-select"
                value={selectedToolName}
                onChange={handleToolSelect}
                className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                <option value="">-- Select a tool --</option>
                {toolsData?.tools.map((tool) => (
                  <option key={tool.name} value={tool.name}>
                    {tool.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Tool description */}
            {selectedTool && (
              <div className="rounded-md bg-gray-50 p-3 text-sm text-gray-600 dark:bg-gray-700/50 dark:text-gray-400">
                {selectedTool.description}
              </div>
            )}

            {/* Tool arguments */}
            {selectedTool && toolArguments.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Arguments
                </h3>
                {toolArguments.map((arg) => (
                  <div key={arg.name}>
                    <label
                      htmlFor={`arg-${arg.name}`}
                      className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
                    >
                      {arg.name}
                      {arg.required && <span className="text-red-500">*</span>}
                    </label>
                    {arg.description && (
                      <p className="mb-1 text-xs text-gray-500 dark:text-gray-400">
                        {arg.description}
                      </p>
                    )}
                    <input
                      id={`arg-${arg.name}`}
                      type="text"
                      value={argumentValues[arg.name] || ""}
                      onChange={(e) =>
                        handleArgumentChange(arg.name, e.target.value)
                      }
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
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
                    ? "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400"
                    : "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400"
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
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleInvoke}
            disabled={!isFormValid || isInvoking}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isInvoking ? "Invoking..." : "Invoke"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ToolInvocationDialog;
