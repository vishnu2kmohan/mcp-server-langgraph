/**
 * ChatProperties Component
 *
 * Property panel for chat sessions, showing session info,
 * model configuration, token usage, and available tools.
 */

import { useState, useMemo, useCallback } from "react";
import { Pencil, Check, X } from "lucide-react";
import type { TabState } from "../../../store/slices/workspaceSlice";
import type { ClientSession } from "../../../types/session";
import type { MCPTool } from "../../../types/mcp";
import { PropertySection } from "./PropertySection";
import { PropertyRow } from "./PropertyRow";
import { useUpdateSessionConfigMutation } from "../../../api";

// =============================================================================
// Types
// =============================================================================

export interface ChatPropertiesProps {
  tab: TabState;
  session: ClientSession | null;
  tools: MCPTool[];
  isSectionExpanded: (id: string) => boolean;
  onToggleSection: (id: string) => void;
}

// =============================================================================
// Constants
// =============================================================================

// Cost per 1K tokens by provider (simplified estimates)
const COST_PER_1K_TOKENS: Record<string, { input: number; output: number }> = {
  openai: { input: 0.01, output: 0.03 },
  anthropic: { input: 0.015, output: 0.075 },
  google: { input: 0.00025, output: 0.0005 },
  azure: { input: 0.01, output: 0.03 },
};

// =============================================================================
// Component
// =============================================================================

export function ChatProperties({
  tab,
  session,
  tools,
  isSectionExpanded,
  onToggleSection,
}: ChatPropertiesProps) {
  // Model editing state
  const [isEditingModel, setIsEditingModel] = useState(false);
  const [editModelValue, setEditModelValue] = useState("");

  // Temperature editing state
  const [isEditingTemperature, setIsEditingTemperature] = useState(false);
  const [editTemperatureValue, setEditTemperatureValue] = useState("");

  // Max tokens editing state
  const [isEditingMaxTokens, setIsEditingMaxTokens] = useState(false);
  const [editMaxTokensValue, setEditMaxTokensValue] = useState("");

  const [updateSessionConfig] = useUpdateSessionConfigMutation();

  // Handle model edit
  const handleEditModel = useCallback(() => {
    setEditModelValue(session?.config?.modelName ?? "");
    setIsEditingModel(true);
  }, [session?.config?.modelName]);

  const handleSaveModel = useCallback(async () => {
    if (session?.id && editModelValue.trim()) {
      await updateSessionConfig({
        session_id: session.id,
        model: editModelValue.trim(),
      });
    }
    setIsEditingModel(false);
  }, [session?.id, editModelValue, updateSessionConfig]);

  const handleCancelModel = useCallback(() => {
    setIsEditingModel(false);
    setEditModelValue("");
  }, []);

  // Handle temperature edit
  const handleEditTemperature = useCallback(() => {
    setEditTemperatureValue(String(session?.config?.temperature ?? 0.7));
    setIsEditingTemperature(true);
  }, [session?.config?.temperature]);

  const handleSaveTemperature = useCallback(async () => {
    const value = parseFloat(editTemperatureValue);
    if (session?.id && !isNaN(value) && value >= 0 && value <= 2) {
      await updateSessionConfig({
        session_id: session.id,
        temperature: value,
      });
    }
    setIsEditingTemperature(false);
  }, [session?.id, editTemperatureValue, updateSessionConfig]);

  const handleCancelTemperature = useCallback(() => {
    setIsEditingTemperature(false);
    setEditTemperatureValue("");
  }, []);

  // Handle max tokens edit
  const handleEditMaxTokens = useCallback(() => {
    setEditMaxTokensValue(String(session?.config?.maxTokens ?? 1000));
    setIsEditingMaxTokens(true);
  }, [session?.config?.maxTokens]);

  const handleSaveMaxTokens = useCallback(async () => {
    const value = parseInt(editMaxTokensValue, 10);
    if (session?.id && !isNaN(value) && value >= 1) {
      await updateSessionConfig({
        session_id: session.id,
        max_tokens: value,
      });
    }
    setIsEditingMaxTokens(false);
  }, [session?.id, editMaxTokensValue, updateSessionConfig]);

  const handleCancelMaxTokens = useCallback(() => {
    setIsEditingMaxTokens(false);
    setEditMaxTokensValue("");
  }, []);

  // Calculate total tokens from messages
  const tokenStats = useMemo(() => {
    if (!session?.messages) {
      return { prompt: 0, completion: 0, total: 0 };
    }
    return session.messages.reduce(
      (acc, msg) => {
        if (msg.usage) {
          acc.prompt += msg.usage.promptTokens;
          acc.completion += msg.usage.completionTokens;
          acc.total += msg.usage.totalTokens;
        }
        return acc;
      },
      { prompt: 0, completion: 0, total: 0 },
    );
  }, [session?.messages]);

  // Estimate cost
  const estimatedCost = useMemo(() => {
    if (!session?.config) return 0;
    const rates =
      COST_PER_1K_TOKENS[session.config.modelProvider] ??
      COST_PER_1K_TOKENS.openai;
    const inputCost = (tokenStats.prompt / 1000) * rates.input;
    const outputCost = (tokenStats.completion / 1000) * rates.output;
    return inputCost + outputCost;
  }, [session?.config, tokenStats]);

  const modelProvider = session?.config?.modelProvider ?? "Not configured";
  const modelName = session?.config?.modelName ?? "Default";
  const messageCount = session?.messages?.length ?? 0;

  return (
    <div data-testid="chat-properties">
      <PropertySection
        id="session-info"
        title="Session Info"
        isExpanded={isSectionExpanded("session-info")}
        onToggle={() => onToggleSection("session-info")}
      >
        <PropertyRow label="ID" value={tab.entityId || "N/A"} mono />
        <PropertyRow label="Title" value={tab.title} />
        <PropertyRow label="Messages" value={messageCount} />
      </PropertySection>

      <PropertySection
        id="model-info"
        title="Model"
        isExpanded={isSectionExpanded("model-info")}
        onToggle={() => onToggleSection("model-info")}
      >
        <PropertyRow label="Provider" value={modelProvider} />
        {isEditingModel ? (
          <div className="flex items-center gap-1 text-xs">
            <span className="text-gray-500 dark:text-gray-400 flex-shrink-0">
              Model
            </span>
            <div className="flex items-center gap-1 ml-auto">
              <input
                data-testid="model-input"
                type="text"
                value={editModelValue}
                onChange={(e) => setEditModelValue(e.target.value)}
                className="w-24 px-1 py-0.5 text-xs border rounded bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-1 focus:ring-primary-500"
                autoFocus
              />
              <button
                data-testid="save-model-button"
                type="button"
                onClick={handleSaveModel}
                className="p-0.5 text-green-600 hover:text-green-700 dark:text-green-400"
                title="Save"
              >
                <Check size={12} />
              </button>
              <button
                data-testid="cancel-model-button"
                type="button"
                onClick={handleCancelModel}
                className="p-0.5 text-gray-500 hover:text-gray-700 dark:text-gray-400"
                title="Cancel"
              >
                <X size={12} />
              </button>
            </div>
          </div>
        ) : (
          <PropertyRow
            label="Model"
            value={modelName}
            action={
              session && (
                <button
                  data-testid="edit-model-button"
                  type="button"
                  onClick={handleEditModel}
                  className="p-0.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  title="Edit model"
                >
                  <Pencil size={10} />
                </button>
              )
            }
          />
        )}
        {session?.config && (
          <>
            {isEditingTemperature ? (
              <div className="flex items-center gap-1 text-xs">
                <span className="text-gray-500 dark:text-gray-400 flex-shrink-0">
                  Temperature
                </span>
                <div className="flex items-center gap-1 ml-auto">
                  <input
                    data-testid="temperature-input"
                    type="number"
                    step="0.1"
                    min="0"
                    max="2"
                    value={editTemperatureValue}
                    onChange={(e) => setEditTemperatureValue(e.target.value)}
                    className="w-16 px-1 py-0.5 text-xs border rounded bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    autoFocus
                  />
                  <button
                    data-testid="save-temperature-button"
                    type="button"
                    onClick={handleSaveTemperature}
                    className="p-0.5 text-green-600 hover:text-green-700 dark:text-green-400"
                    title="Save"
                  >
                    <Check size={12} />
                  </button>
                  <button
                    data-testid="cancel-temperature-button"
                    type="button"
                    onClick={handleCancelTemperature}
                    className="p-0.5 text-gray-500 hover:text-gray-700 dark:text-gray-400"
                    title="Cancel"
                  >
                    <X size={12} />
                  </button>
                </div>
              </div>
            ) : (
              <PropertyRow
                label="Temperature"
                value={session.config.temperature.toFixed(1)}
                action={
                  <button
                    data-testid="edit-temperature-button"
                    type="button"
                    onClick={handleEditTemperature}
                    className="p-0.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                    title="Edit temperature"
                  >
                    <Pencil size={10} />
                  </button>
                }
              />
            )}
            {isEditingMaxTokens ? (
              <div className="flex items-center gap-1 text-xs">
                <span className="text-gray-500 dark:text-gray-400 flex-shrink-0">
                  Max Tokens
                </span>
                <div className="flex items-center gap-1 ml-auto">
                  <input
                    data-testid="max-tokens-input"
                    type="number"
                    min="1"
                    max="128000"
                    value={editMaxTokensValue}
                    onChange={(e) => setEditMaxTokensValue(e.target.value)}
                    className="w-20 px-1 py-0.5 text-xs border rounded bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    autoFocus
                  />
                  <button
                    data-testid="save-max-tokens-button"
                    type="button"
                    onClick={handleSaveMaxTokens}
                    className="p-0.5 text-green-600 hover:text-green-700 dark:text-green-400"
                    title="Save"
                  >
                    <Check size={12} />
                  </button>
                  <button
                    data-testid="cancel-max-tokens-button"
                    type="button"
                    onClick={handleCancelMaxTokens}
                    className="p-0.5 text-gray-500 hover:text-gray-700 dark:text-gray-400"
                    title="Cancel"
                  >
                    <X size={12} />
                  </button>
                </div>
              </div>
            ) : (
              <PropertyRow
                label="Max Tokens"
                value={session.config.maxTokens.toLocaleString()}
                action={
                  <button
                    data-testid="edit-max-tokens-button"
                    type="button"
                    onClick={handleEditMaxTokens}
                    className="p-0.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                    title="Edit max tokens"
                  >
                    <Pencil size={10} />
                  </button>
                }
              />
            )}
          </>
        )}
      </PropertySection>

      <PropertySection
        id="usage-info"
        title="Usage"
        isExpanded={isSectionExpanded("usage-info")}
        onToggle={() => onToggleSection("usage-info")}
        badge={
          <span className="text-[10px] text-gray-400">
            {tokenStats.total.toLocaleString()} tokens
          </span>
        }
      >
        <PropertyRow
          label="Prompt Tokens"
          value={tokenStats.prompt.toLocaleString()}
        />
        <PropertyRow
          label="Completion Tokens"
          value={tokenStats.completion.toLocaleString()}
        />
        <PropertyRow
          label="Total Tokens"
          value={tokenStats.total.toLocaleString()}
        />
        <PropertyRow label="Est. Cost" value={`$${estimatedCost.toFixed(4)}`} />
      </PropertySection>

      <PropertySection
        id="tools-info"
        title="Available Tools"
        isExpanded={isSectionExpanded("tools-info")}
        onToggle={() => onToggleSection("tools-info")}
        badge={
          <span className="text-[10px] px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded">
            {tools.length}
          </span>
        }
      >
        {tools.length === 0 ? (
          <p className="text-xs text-gray-500 dark:text-gray-400">
            No tools available
          </p>
        ) : (
          <div className="space-y-1">
            {tools.map((tool) => (
              <div
                key={tool.name}
                className="flex items-center gap-2 text-xs py-1"
              >
                <span className="w-2 h-2 rounded-full bg-green-500 flex-shrink-0" />
                <span className="text-gray-700 dark:text-gray-200 font-medium truncate">
                  {tool.name}
                </span>
              </div>
            ))}
          </div>
        )}
      </PropertySection>
    </div>
  );
}

export default ChatProperties;
