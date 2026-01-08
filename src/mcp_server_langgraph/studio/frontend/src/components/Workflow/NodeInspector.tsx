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
    <div className="absolute top-4 right-4 w-80 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-10">
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <h3 className="font-semibold text-gray-900 dark:text-gray-100">
          Node Inspector
        </h3>
        <button
          onClick={() => dispatch(clearSelection())}
          className="p-1 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 rounded"
          aria-label="Close node inspector"
        >
          <X size={18} className="text-gray-500 dark:text-gray-400" />
        </button>
      </div>

      <div className="p-4 space-y-4">
        {/* Node Type */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Type
          </label>
          <div className="text-sm text-gray-900 dark:text-gray-100 capitalize px-3 py-2 bg-gray-50 dark:bg-gray-700 rounded">
            {data.nodeType}
          </div>
        </div>

        {/* Label */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Label
          </label>
          <input
            type="text"
            value={data.label}
            onChange={(e) => handleLabelChange(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
              bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
              focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>

        {/* Type-specific configuration */}
        {data.nodeType === "llm" && (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Model
            </label>
            <select
              value={(data.config.model as string) || "gemini-2.5-flash"}
              onChange={(e) => handleConfigChange("model", e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
                focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
              <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
              <option value="gpt-4o">GPT-4o</option>
              <option value="claude-opus-4.5">Claude Opus 4.5</option>
            </select>
          </div>
        )}

        {data.nodeType === "tool" && (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Tool Name
            </label>
            <input
              type="text"
              value={(data.config.toolName as string) || ""}
              onChange={(e) => handleConfigChange("toolName", e.target.value)}
              placeholder="e.g., search_web, read_file"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
                focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
        )}

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Description (optional)
          </label>
          <textarea
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
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
              bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
              focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>

        {/* Ask AI Button */}
        <button
          data-testid="ask-ai-button"
          onClick={() => setShowAiChat(!showAiChat)}
          className={`
            w-full flex items-center justify-center gap-2 px-4 py-2 rounded-md
            text-sm font-medium transition-colors
            ${
              showAiChat
                ? "bg-insight-100 text-insight-700 dark:bg-insight-900/30 dark:text-insight-400"
                : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600"
            }
          `}
        >
          <Sparkles size={16} />
          Ask AI
        </button>

        {/* AI Chat Panel */}
        {showAiChat && (
          <div
            data-testid="ai-chat-panel"
            className="mt-4 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-md border border-gray-200 dark:border-gray-700 dark:border-gray-600"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                AI Config Assistant
              </span>
              <button
                data-testid="close-ai-panel"
                onClick={() => setShowAiChat(false)}
                className="p-1 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded"
                aria-label="Close AI assistant panel"
              >
                <X size={14} className="text-gray-500 dark:text-gray-400" />
              </button>
            </div>

            {/* Question Input */}
            <div className="flex gap-2">
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && question.trim()) {
                    handleAskAi();
                  }
                }}
                placeholder="Ask about this node config..."
                className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md
                  bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
                  focus:ring-2 focus:ring-insight-500 focus:border-transparent"
              />
              <button
                data-testid="send-ai-question"
                onClick={handleAskAi}
                disabled={!question.trim() || isLoadingAi}
                className="p-2 bg-insight-600 text-white rounded-md hover:bg-insight-700
                  disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Send question to AI assistant"
              >
                {isLoadingAi ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Send size={16} />
                )}
              </button>
            </div>

            {/* Loading State */}
            {isLoadingAi && (
              <div
                data-testid="ai-loading"
                className="mt-3 flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400"
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
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  {aiResponse.answer}
                </p>

                {/* Examples */}
                {aiResponse.examples && aiResponse.examples.length > 0 && (
                  <div className="mt-2">
                    <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                      Examples:
                    </span>
                    <ul className="mt-1 text-xs text-gray-600 dark:text-gray-400 space-y-1">
                      {aiResponse.examples.map((example, i) => (
                        <li
                          key={i}
                          className="pl-2 border-l-2 border-gray-300 dark:border-gray-600"
                        >
                          {example}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Apply Suggested Config Button */}
                {aiResponse.suggested_config && (
                  <button
                    data-testid="apply-suggested-config"
                    onClick={handleApplySuggestedConfig}
                    className="flex items-center gap-2 px-3 py-1.5 bg-success-100 text-success-700
                      dark:bg-success-900/30 dark:text-success-400 text-sm rounded-md
                      hover:bg-success-200 dark:hover:bg-success-900/50 transition-colors"
                  >
                    <Check size={14} />
                    Apply Suggested Config
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
