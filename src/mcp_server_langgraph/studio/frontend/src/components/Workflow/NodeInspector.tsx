/**
 * NodeInspector Component
 *
 * Configuration panel for selected nodes.
 * Shows node properties and allows editing.
 * Includes AI-powered configuration assistance.
 */

import { useState, useCallback } from "react";
import { X, Sparkles, Send, Loader2, Check } from "lucide-react";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import {
  updateNode,
  clearSelection,
  selectWorkflowNodes,
  selectSelectedNodeIds,
} from "../../store/slices/workflowSlice";
import { useGetNodeConfigHelpMutation } from "../../api";
import type { NodeConfigHelpResponse } from "../../types/api";

import { Button, Input, Select, Textarea } from "@/components/UI";

export function NodeInspector() {
  const dispatch = useAppDispatch();
  const nodes = useAppSelector(selectWorkflowNodes);
  const selectedNodeIds = useAppSelector(selectSelectedNodeIds);

  // AI Config Assistant state
  const [showAiChat, setShowAiChat] = useState(false);
  const [question, setQuestion] = useState("");
  const [aiResponse, setAiResponse] = useState<NodeConfigHelpResponse | null>(
    null,
  );
  const [aiError, setAiError] = useState<string | null>(null);

  const [getNodeConfigHelp, { isLoading: isLoadingAi }] =
    useGetNodeConfigHelpMutation();

  const selectedNode =
    selectedNodeIds?.length === 1
      ? nodes?.find((n) => n.id === selectedNodeIds[0])
      : null;

  const handleLabelChange = useCallback(
    (label: string) => {
      if (!selectedNode) return;
      dispatch(updateNode({ nodeId: selectedNode.id, data: { label } }));
    },
    [dispatch, selectedNode],
  );

  const handleConfigChange = useCallback(
    (key: string, value: unknown) => {
      if (!selectedNode) return;
      dispatch(
        updateNode({
          nodeId: selectedNode.id,
          data: {
            config: { ...selectedNode.data.config, [key]: value },
          },
        }),
      );
    },
    [dispatch, selectedNode],
  );

  const handleAskAi = useCallback(async () => {
    if (!selectedNode || !question.trim()) return;

    setAiError(null);
    try {
      const response = await getNodeConfigHelp({
        node_type: selectedNode.data.nodeType,
        node_config: selectedNode.data.config,
        question: question.trim(),
      }).unwrap();
      setAiResponse(response);
    } catch (error) {
      setAiError("Failed to get AI help. Please try again.");
      console.error("AI Config Help error:", error);
    }
  }, [selectedNode, question, getNodeConfigHelp]);

  const handleApplySuggestedConfig = useCallback(() => {
    if (!selectedNode || !aiResponse?.suggested_config) return;

    // Merge suggested config with existing config
    dispatch(
      updateNode({
        nodeId: selectedNode.id,
        data: {
          config: {
            ...selectedNode.data.config,
            ...aiResponse.suggested_config,
          },
        },
      }),
    );
  }, [dispatch, selectedNode, aiResponse]);

  if (!selectedNode) {
    return null;
  }

  const { data } = selectedNode;

  return (
    <div className="absolute top-4 right-4 w-80 bg-white dark:bg-neutral-800 rounded-lg shadow-lg border border-neutral-200 dark:border-neutral-700 z-10">
      <div className="flex items-center justify-between p-4 border-b border-neutral-200 dark:border-neutral-700">
        <h3 className="font-semibold text-neutral-900 dark:text-neutral-100">
          Node Inspector
        </h3>
        <Button
          variant="secondary"
          className="p-1 hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700 rounded"
          onClick={() => dispatch(clearSelection())}
          aria-label="Close node inspector"
        >
          <X size={18} className="text-neutral-500 dark:text-neutral-400" />
        </Button>
      </div>
      <div className="p-4 space-y-4">
        {/* Node Type */}
        <div>
          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
            Type
          </label>
          <div className="text-sm text-neutral-900 dark:text-neutral-100 capitalize px-3 py-2 bg-neutral-50 dark:bg-neutral-700 rounded">
            {data.nodeType}
          </div>
        </div>

        {/* Label */}
        <div>
          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
            Label
          </label>
          <Input
            className="px-3 py-2 text-neutral-900 dark:text-neutral-100 focus:ring-primary-500"
            value={data.label}
            onChange={(e) => handleLabelChange(e.target.value)}
          />
        </div>

        {/* Type-specific configuration */}
        {data.nodeType === "llm" && (
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
              Model
            </label>
            <Select
              className="px-3 py-2 text-neutral-900 dark:text-neutral-100 focus:ring-primary-500"
              value={(data.config.model as string) || "gemini-2.5-flash"}
              onChange={(e) => handleConfigChange("model", e.target.value)}
            >
              <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
              <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
              <option value="gpt-4o">GPT-4o</option>
              <option value="claude-opus-4.5">Claude Opus 4.5</option>
            </Select>
          </div>
        )}

        {data.nodeType === "tool" && (
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
              Tool Name
            </label>
            <Input
              className="px-3 py-2 text-neutral-900 dark:text-neutral-100 focus:ring-primary-500"
              value={(data.config.toolName as string) || ""}
              onChange={(e) => handleConfigChange("toolName", e.target.value)}
              placeholder="e.g., search_web, read_file"
            />
          </div>
        )}

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
            Description (optional)
          </label>
          <Textarea
            className="px-3 py-2 text-neutral-900 dark:text-neutral-100 focus:ring-primary-500"
            value={data.description || ""}
            onChange={(e) =>
              dispatch(
                updateNode({
                  nodeId: selectedNode.id,
                  data: { description: e.target.value },
                }),
              )
            }
            rows={3}
          />
        </div>

        {/* Ask AI Button */}
        <Button
          className="w-full flex px-4 py-2 rounded-md text-sm"
          data-testid="ask-ai-button"
          onClick={() => setShowAiChat(!showAiChat)}
        >
          <Sparkles size={16} />
          Ask AI
        </Button>

        {/* AI Chat Panel */}
        {showAiChat && (
          <div
            data-testid="ai-chat-panel"
            className="mt-4 p-3 bg-neutral-50 dark:bg-neutral-700/50 rounded-md border border-neutral-200 dark:border-neutral-700 dark:border-neutral-600"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
                AI Config Assistant
              </span>
              <Button
                variant="secondary"
                className="p-1 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600 rounded"
                data-testid="close-ai-panel"
                onClick={() => setShowAiChat(false)}
                aria-label="Close AI assistant panel"
              >
                <X
                  size={14}
                  className="text-neutral-500 dark:text-neutral-400"
                />
              </Button>
            </div>

            {/* Question Input */}
            <div className="flex gap-2">
              <Input
                className="flex-1 px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 focus:ring-insight-500"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && question.trim()) {
                    handleAskAi();
                  }
                }}
                placeholder="Ask about this node config..."
              />
              <Button
                className="p-2 bg-insight-600 text-white rounded-md hover:bg-insight-700"
                data-testid="send-ai-question"
                onClick={handleAskAi}
                disabled={!question.trim() || isLoadingAi}
                aria-label="Send question to AI assistant"
              >
                {isLoadingAi ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Send size={16} />
                )}
              </Button>
            </div>

            {/* Loading State */}
            {isLoadingAi && (
              <div
                data-testid="ai-loading"
                className="mt-3 flex items-center gap-2 text-sm text-neutral-500 dark:text-neutral-400"
              >
                <Loader2 size={14} className="animate-spin" />
                Thinking...
              </div>
            )}

            {/* Error State */}
            {aiError && (
              <div
                data-testid="ai-error"
                className="mt-3 p-2 bg-error-100 dark:bg-error-900/30 text-error-700 dark:text-error-400 text-sm rounded"
              >
                {aiError}
              </div>
            )}

            {/* AI Response */}
            {aiResponse && !isLoadingAi && (
              <div className="mt-3 space-y-2">
                <p className="text-sm text-neutral-700 dark:text-neutral-300">
                  {aiResponse.answer}
                </p>

                {/* Examples */}
                {aiResponse.examples && aiResponse.examples.length > 0 && (
                  <div className="mt-2">
                    <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400">
                      Examples:
                    </span>
                    <ul className="mt-1 text-xs text-neutral-600 dark:text-neutral-400 space-y-1">
                      {aiResponse.examples.map((example, i) => (
                        <li
                          key={i}
                          className="pl-2 border-l-2 border-neutral-300 dark:border-neutral-600"
                        >
                          {example}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Apply Suggested Config Button */}
                {aiResponse.suggested_config && (
                  <Button
                    variant="success"
                    className="flex px-3 py-1.5 bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400 text-sm rounded-md hover:bg-success-200 dark:hover:bg-success-900/50"
                    data-testid="apply-suggested-config"
                    onClick={handleApplySuggestedConfig}
                  >
                    <Check size={14} />
                    Apply Suggested Config
                  </Button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
