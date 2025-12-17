/**
 * ChatProperties Component
 *
 * Property panel for chat sessions, showing session info,
 * model configuration, token usage, and available tools.
 */

import { useMemo } from "react";
import type { TabState } from "../../../store/slices/workspaceSlice";
import type { ClientSession } from "../../../types/session";
import type { MCPTool } from "../../../types/mcp";
import { PropertySection } from "./PropertySection";
import { PropertyRow } from "./PropertyRow";

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
        <PropertyRow label="Model" value={modelName} />
        {session?.config && (
          <>
            <PropertyRow
              label="Temperature"
              value={session.config.temperature.toFixed(1)}
            />
            <PropertyRow
              label="Max Tokens"
              value={session.config.maxTokens.toLocaleString()}
            />
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
